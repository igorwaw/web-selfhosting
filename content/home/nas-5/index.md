---
title: "Storage server, part 5: migrating from unencrypted mdadm to encrypted btrfs"
date: 2026-07-10T14:00:00
draft: true
tags: ["storage"]
---

In [part 3](/home/nas-3/) and [part 4](/home/nas-4/) I explained how I configured my NAS with btrfs in RAID1 mode and encryption. Strictly speaking, it wasn't true. When I originally built this server few years ago, I used mdadm RAID1 and no encryption. Later, I decided to improve the setup. This post is the actual migration, done live on my NAS ("firefly") without buying any new hardware.

## The starting point

Before the change, `sdb` and `sde` (2x3TB) were an mdadm RAID1 array (`md0`), with LVM (`datavg`) on top providing two mounted logical volumes:

- `othervol` at `/data/other`
- `noshare` at `/data/noshare`

The rest of the disks (`sdc`, `sdd`, `sdf`, `sdg`, `sdh`) were plain ext4, managed by SnapRAID, unencrypted. System drive `sda` is left untouched.

Target state:

- `sdb` + `sde`: LUKS on each disk individually, btrfs RAID1 on top, so bitrot gets corrected automatically
- every SnapRAID disk: LUKS individually too, same shared key
- one password unlocks everything, via a script run manually over SSH after boot, never at boot itself

## Step 1: making space to work with

Reformatting `sdb`/`sde` destroys everything on them, so I needed a temporary local copy (I have an offsite backup on iDrive, but restoring would be slow, plus 2 copies are safer than 1). I decided to use one of the SnapRAID video volumes which had enough free space:

```bash
cp -a /data/other /data/filmy/backup/
cp -a /data/noshare /data/filmy/backup/
```

This is where I learned more than I wanted to about my own hardware. The first attempt (on /data/seriale) started at 250MB/s, but in a few seconds dropped to 30MB/s. `iostat -x` pointed at the destination disk, not the source RAID1 pair - high `%util`, huge `w_await`. Turned out the disk I'd picked as scratch space was an SMR model. And that's exactly what's expected from SMR drives - once their write cache fills up, write speed drops to unaccaptable values. I checked my HDDs, luckily one of CMR drives (WD Red Plus) also had enough free space. Copying speed was more sensible 100MB/s (and the bottleneck was the source drive).

Later in the same copy job, speed dropped to just a few MB/s for a different reason entirely: a scheduled mdadm RAID consistency check had kicked in and was competing for reads on the same array. `cat /proc/mdstat` confirmed it's active and would take 10 hours to complete; `echo idle > /sys/block/md0/md/sync_action` paused it. I don't need the check, in a moment I'd be wiping the array anyway.

But before that, I verified the copy rather than trusting `cp -a`. There went another few hours.

```bash
rsync -ac --dry-run --stats /data/noshare/ /data/filmy/backup/noshare/
rsync -ac --dry-run --stats /data/other/ /data/filmy/backup/orhwe/
```

## Step 2: tearing down the old mdadm/LVM stack

With the data safely elsewhere, `sdb`/`sde` could be wiped. I prepared a script, supported by Claude. Nobody reviews my home scripts and there's no test environment, which is why I don't trust the AI agent alone, but I don't trust myself either (I don't hallucinate, but I make typos). Here's the relevant part.

```bash
for mp in "${OLD_LV_MOUNTPOINTS[@]}"; do
  umount "$mp" 2>/dev/null || true
done
if vgs "$OLD_LVM_VG" &>/dev/null; then
  vgchange -an "$OLD_LVM_VG"
  vgremove -f "$OLD_LVM_VG"
fi
if [ -e "$OLD_MD_DEVICE" ]; then
  mdadm --stop "$OLD_MD_DEVICE"
fi
for dev in "${BTRFS_RAID1_DEVICES[@]}"; do
  mdadm --zero-superblock "$dev" 2>/dev/null || true
  wipefs -a "$dev"
done
sed -i '/ARRAY \/dev\/md0/d' /etc/mdadm/mdadm.conf 2>/dev/null || true
```

The few `|| true` parts and the `if` check give a bit of idempotency: if the script fails, it can be rerun. Not as safe as an Ansible playbook would be, but easier to create for a one-off task.

Unmount the LVs, deactivate and remove the volume group, stop the array, zero the mdadm superblock on each member disk, `wipefs` to clear any remaining LVM/mdadm signatures, and drop the array from `mdadm.conf` so it doesn't try (and fail) to reassemble a dead array on the next boot.

## Step 3: LUKS on each disk, btrfs RAID1 on top

The order of layers is important: physical disks, LUKS, then btrfs. For the "one password for everything" requirement, I generated a single random keyfile once and use it directly as the LUKS key material on every disk in the whole setup (this one and the SnapRAID ones later):

```bash
if [ ! -f "$KEYFILE" ]; then
  dd if=/dev/urandom of="$KEYFILE" bs=512 count=4
  chmod 600 "$KEYFILE"
fi
```

LUKS can have multiple keys unlocking the same device. I also added a second key slot on each disk with a passphrase I saved in my password manager, in case the keyfile is ever lost or corrupted.

```bash
read -r -s -p "Recovery passphrase: " RECOVERY_PASSPHRASE
echo
read -r -s -p "Confirm recovery passphrase: " RECOVERY_PASSPHRASE_CONFIRM
echo
if [ "$RECOVERY_PASSPHRASE" != "$RECOVERY_PASSPHRASE_CONFIRM" ]; then
  echo "Passphrases don't match." >&2
  exit 1
fi
unset RECOVERY_PASSPHRASE_CONFIRM
```

Then format and open both disks, adding the recovery passphrase as a second slot:

```bash
mapper_devices=()
i=1
for dev in "${BTRFS_RAID1_DEVICES[@]}"; do
  name="${BTRFS_MAPPER_PREFIX}${i}"
  cryptsetup luksFormat --type luks2 "$dev" --key-file "$KEYFILE"
  printf '%s' "$RECOVERY_PASSPHRASE" | cryptsetup luksAddKey "$dev" --key-file "$KEYFILE" -
  cryptsetup luksOpen "$dev" "$name" --key-file "$KEYFILE"
  mapper_devices+=("/dev/mapper/$name")
  i=$((i + 1))
done
unset RECOVERY_PASSPHRASE
```

With both disks open as `/dev/mapper/luks-btrfs1` and `luks-btrfs2`, creating the actual RAID1 pool is a single command:

```bash
mkfs.btrfs -m raid1 -d raid1 -L "$BTRFS_LABEL" "${mapper_devices[@]}"
```

Btrfs replaces the LVM layer I used to have, so instead of logical volumes I created subvolumes for the two things I actually mount:

```bash
mkdir -p /mnt/btrfs-root
mount "${mapper_devices[0]}" /mnt/btrfs-root
for entry in "${BTRFS_SUBVOLUMES[@]}"; do
  subvol="${entry%%:*}"
  btrfs subvolume create "/mnt/btrfs-root/${subvol}"
done
umount /mnt/btrfs-root

for entry in "${BTRFS_SUBVOLUMES[@]}"; do
  subvol="${entry%%:*}"
  mountpoint="${entry#*:}"
  [ -z "$mountpoint" ] && continue
  mkdir -p "$mountpoint"
  mount -o "subvol=${subvol}" "${mapper_devices[0]}" "$mountpoint"
done
```

Notice both subvolumes mount through `mapper_devices[0]` (the first disk) - with a multi-device btrfs filesystem you only ever mount one member, and btrfs itself finds the rest.

Finally, I added `/etc/fstab` entries for both mountpoints, but with `noauto` - the whole point of this setup is that nothing mounts by itself at boot:

```bash
for entry in "${BTRFS_SUBVOLUMES[@]}"; do
  subvol="${entry%%:*}"
  mountpoint="${entry#*:}"
  [ -z "$mountpoint" ] && continue
  echo "/dev/mapper/${BTRFS_MAPPER_PREFIX}1 $mountpoint btrfs subvol=${subvol},noauto,nofail,nodev,noexec,noatime 0 0" >> /etc/fstab
done
```

## Step 4: locking down dependent services, moving the data back

A few things on this NAS (Grafana, Jellyfin, Syncthing, Samba) read or write to `/data/other` or `/data/noshare`. Since those paths are empty until the unlock script runs, I stopped them and disabled autostart:

```bash
for container in "${DOCKER_CONTAINERS[@]}"; do
  docker stop "$container" || true
  docker update --restart no "$container"
done

for service in "${SYSTEMD_SERVICES[@]}"; do
  systemctl stop "$service" || true
  systemctl disable "$service"
done
```

With the new pool mounted and empty, I copied the data back from its temporary home. This time I used a `tar` pipe instead of `cp -a`, since both directories have a lot of small files and `tar` avoids the per-file overhead - run under `screen` so it survives if SSH disconnects:

```bash
screen -S restore

tar -cf - -C /data/filmy/backup/other . | tar -xf - -C /data/other
tar -cf - -C /data/filmy/backup/noshare . | tar -xf - -C /data/noshare
```

Once both finished, I verified with `rsync` in checksum dry-run mode - it reads every byte on both sides and reports any mismatch without touching anything:

```bash
rsync -ac --dry-run --stats /data/filmy/backup/other/ /data/other/
rsync -ac --dry-run --stats /data/filmy/backup/noshare/ /data/noshare/
```

No files listed means a byte-for-byte match. Since source and destination are on completely separate physical disks, this verification pass ran close to full disk speed on each side rather than fighting itself for I/O. Only after both came back clean did I delete the temporary copy on `/data/filmy`.

## Step 5: verifying the RAID1 pool

Btrfs hides some of its internal structure from standard Linux tools (though not as much as ZFS). The `lsblk` command that's very useful on a machine with many hard drives only shows mount points on one of underlying devices:

```
sdb    └─luks-btrfs1  /data/noshare
                      /data/other
sde    └─luks-btrfs2
```

That is expected. The real check is:

```bash
btrfs filesystem show /data/other
btrfs filesystem usage /data/other
```

They confirm the RAID1 setup. Another command you might be used to: `df -h`, is not accurate on btrfs, the command you need is `btrfs filesystem df /data/other`. For a simple setup like this - just a bunch of files copied all in one batch, no snapshots - the numbers were very close, but it's not always the case.

## Step 6: the deferred, single-password unlock script

The LUKS keyfile gets GPG-encrypted with a human passphrase, and the plaintext copy shredded once every disk (this pair, and eventually the SnapRAID disks) is formatted with it.

The unlock script, run manually over SSH after boot, asks for the password once:

```bash
read -r -s -p "Password: " PASSPHRASE
echo
echo -n "$PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 --decrypt "$KEYFILE_ENC" > "$KEYFILE_TMP"
unset PASSPHRASE
chmod 600 "$KEYFILE_TMP"
```

The decrypted keyfile only ever touches `/dev/shm` (tmpfs, never written to disk), and gets shredded on exit via a trap, whether the script succeeds or fails. From there, it's the mirror image of the setup script - open both LUKS containers by UUID, scan for the btrfs devices, mount the subvolumes:

```bash
for uuid in "${BTRFS_RAID1_UUIDS[@]}"; do
  name="${BTRFS_MAPPER_PREFIX}${i}"
  cryptsetup luksOpen "/dev/disk/by-uuid/$uuid" "$name" --key-file "$KEYFILE_TMP"
  btrfs_mapper_devices+=("/dev/mapper/$name")
  i=$((i + 1))
done

btrfs device scan
```

One gotcha worth flagging: the UUIDs this script needs are the LUKS container UUIDs of the raw disks (`blkid /dev/sdb /dev/sde`, `TYPE="crypto_LUKS"`), not the btrfs filesystem UUID you'd get from running `blkid` on the already-decrypted `/dev/mapper/luks-btrfs*` devices. I mixed these up once - easy to do, since both are perfectly valid UUIDs, just for different layers.

I'm testing this in stages: the SnapRAID disks aren't encrypted yet, so their section of the unlock script is commented out for now, and only the btrfs part runs. Once that's proven reliable, the script also starts the dependent services again at the end:

```bash
for container in "${DOCKER_CONTAINERS[@]}"; do
  docker start "$container"
done

for service in "${SYSTEMD_SERVICES[@]}"; do
  systemctl start "$service"
done
```

## What's left

- Encrypting the five SnapRAID disks the same way, with the same keyfile and recovery passphrase, so one password really does unlock everything.
- Uncommenting the SnapRAID section of the unlock script once those disks are done.
- Running a full `snapraid scrub` before wiping any SnapRAID disk, just in case, and keeping the offsite backup up to date throughout.
- Retiring the plaintext keyfile entirely once I'm confident everything works, keeping only the GPG-encrypted copy around.
