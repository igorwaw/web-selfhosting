---
title: "Storage server, part 5: migrating from mdadm to btrfs and unencrypted to encrypted"
date: 2026-07-10T14:00:00
draft: false
tags: ["storage"]
---

In [part 3](/home/nas-3/) and [part 4](/home/nas-4/) I explained how I configured my NAS with encrypted drives and btrfs in RAID1 mode. Strictly speaking, it wasn't true. When I originally built this server a few years ago, I used mdadm RAID1 and no encryption. I soon regretted the decision.

Some time later, when I replaced some old hard drives with higher-capacity ones, I decided now it's a good time. Changing the setup requires moving the data around. Having some drives less than 50% full simplifies it. This post is the actual migration, done live on my NAS ("firefly") without buying any new hardware.

## The starting point

Before the change, `sdb` and `sde` (2x3TB) were an mdadm RAID1 array (`md0`), with LVM (`datavg`) on top providing two mounted logical volumes:

- `othervol` at `/data/other`
- `noshare` at `/data/noshare`

Four HDDs (`sdc`, `sdd`, `sdf`, `sdg`) were ext4, managed by SnapRAID, unencrypted. System drive `sda` is left untouched.

Target state:

- `sdb` + `sde`: LUKS on each disk individually, btrfs RAID1 on top, so bitrot gets corrected automatically
- every SnapRAID disk: LUKS on each disk individually too, ext4 on top of it
- one password unlocks everything, via a script run manually over SSH after boot, never at boot itself

## The process

### Step 1: make sure nothing writes to the drives

A few things on this NAS (Grafana, Jellyfin, Syncthing, Samba) read or write to `/data/other` or `/data/noshare`. I didn't want files to change mid-process. And later, those paths will be empty until the unlock script runs. I stopped them and disabled autostart:

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

I also disabled IDrive scheduler, so it wouldn't back up my local copies.

### Step 2: local copy

Reformatting `sdb`/`sde` destroys everything on them, so I needed a temporary local copy (I have an offsite backup on IDrive, but restoring would be slow, plus 2 copies are safer than 1). I decided to use one of the SnapRAID video volumes which had enough free space:

```bash
cp -a /data/other /data/filmy/backup/
cp -a /data/noshare /data/filmy/backup/
```
Before wiping the old array, I verified the copy was bit-for-bit correct. There went another few hours.

```bash
rsync -ac --dry-run --stats /data/noshare/ /data/filmy/backup/noshare/
rsync -ac --dry-run --stats /data/other/ /data/filmy/backup/other/
```

No files listed means both copies are identical. You might wonder why I used rsync for verification only, but not for doing the actual copy. Rsync has many features - it can resume, transfer over a network, copy only changed parts etc. But it also means for a simple task of copying files to an empty directory on the same machine, it's noticeably slower. And, when you're moving back and forth hundreds of gigabytes, a slower tool could mean an extra few hours.

### Step 3: tearing down the old mdadm/LVM

Now that I had a local copy, `sdb`/`sde` could be wiped. I prepared a script, supported by Claude Code. Nobody reviews my home scripts and there's no test environment. Which is why I don't trust the AI agent, but I don't trust myself either (I don't hallucinate, but I make typos and can mix up device names). Here's the relevant part.

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

What it does is: unmount the filesystems, deactivate and remove the volume group, stop the array, zero the mdadm superblock on each member disk, `wipefs` to clear any remaining LVM/mdadm signatures, and remove the array from `mdadm.conf` so it doesn't try (and fail) to reassemble it on the next boot.

### Step 4: LUKS on each disk

The order of layers is important: physical disks, LUKS, then btrfs. For the "one password for everything" requirement, I generated a single random keyfile once and used it directly as the LUKS key material on every disk in the whole setup (this pair and the SnapRAID ones later):

```bash
if [ ! -f "$KEYFILE" ]; then
  dd if=/dev/urandom of="$KEYFILE" bs=512 count=4
  chmod 600 "$KEYFILE"
fi
```

LUKS can have multiple keys unlocking the same device. I added a second key slot on each disk with a passphrase that I saved in my password manager, in case the keyfile is ever lost or corrupted.

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

Then created the encrypted devices and added the recovery passphrase as a second slot:

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

### Step 5: btrfs RAID1 on top of LUKS devices

With both disks open as `/dev/mapper/luks-btrfs1` and `luks-btrfs2`, creating the actual RAID1 pool is a single command:

```bash
mkfs.btrfs -m raid1 -d raid1 -L "$BTRFS_LABEL" "${mapper_devices[@]}"
```

Btrfs replaces the LVM layer I used to have, so instead of logical volumes I created subvolumes:

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

Notice both subvolumes mount through `mapper_devices[0]` (the first disk). With a multi-device btrfs filesystem you only mount one member - any of them - and btrfs deals with finding the other one and keeping them in sync.

Finally, the script added `/etc/fstab` entries for both mountpoints, but with `noauto` so they're not mounted at boot. I removed the old entries from fstab manually.

```bash
for entry in "${BTRFS_SUBVOLUMES[@]}"; do
  subvol="${entry%%:*}"
  mountpoint="${entry#*:}"
  [ -z "$mountpoint" ] && continue
  echo "/dev/mapper/${BTRFS_MAPPER_PREFIX}1 $mountpoint btrfs subvol=${subvol},noauto,nofail,nodev,noexec,noatime 0 0" >> /etc/fstab
done
```

### Step 6: moving the data back

With the new pool mounted and empty, I copied the data back from its temporary home. This time I used a `tar` pipe instead of `cp -a`. Since both directories have a lot of small files and `tar` avoids the per-file overhead, I was hoping it would be faster. It was, actually, a bit slower. Oh well.

```bash
tar -cf - -C /data/filmy/backup/other . | tar -xf - -C /data/other
tar -cf - -C /data/filmy/backup/noshare . | tar -xf - -C /data/noshare
```

Once both finished, I verified with `rsync` again:

```bash
rsync -ac --dry-run --stats /data/filmy/backup/other/ /data/other/
rsync -ac --dry-run --stats /data/filmy/backup/noshare/ /data/noshare/
```

Only after both came back clean did I delete the temporary copy on `/data/filmy`.

### Step 7: verifying the RAID1 pool

Btrfs hides some of its internal structure from standard Linux tools (though not as much as ZFS). The `lsblk` command that's very useful on a machine with many hard drives only shows mount points on one of the underlying devices:

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

They confirm the RAID1 setup. Another command you might be used to: `df -h`, is not accurate on btrfs, the command you need is `btrfs filesystem df /data/other`. For a simple setup like this - just a bunch of files copied all in one batch, no snapshots, no compression - the numbers were very close, but it's not always the case.

Also worth noting, the btrfs commands above on /data/noshare and /data/other give exactly the same results. That's because these are subvolumes of the same filesystem.

### Step 8: the deferred, single-password unlock script

The LUKS keyfile gets GPG-encrypted with a human passphrase, and the plaintext copy gets shredded once every disk (this pair, and eventually the SnapRAID disks) is formatted with it.

The unlock script, run manually over SSH after boot, asks for the password once:

```bash
read -r -s -p "Password: " PASSPHRASE
echo
echo -n "$PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 --decrypt "$KEYFILE_ENC" > "$KEYFILE_TMP"
unset PASSPHRASE
chmod 600 "$KEYFILE_TMP"
```

The decrypted keyfile is saved to `/dev/shm` (tmpfs, never written to disk), and gets shredded on exit via a trap, whether the script succeeds or fails. From there, it's the mirror image of the setup script - open both LUKS containers by UUID, scan for the btrfs devices, mount the subvolumes:

```bash
for uuid in "${BTRFS_RAID1_UUIDS[@]}"; do
  name="${BTRFS_MAPPER_PREFIX}${i}"
  cryptsetup luksOpen "/dev/disk/by-uuid/$uuid" "$name" --key-file "$KEYFILE_TMP"
  btrfs_mapper_devices+=("/dev/mapper/$name")
  i=$((i + 1))
done

btrfs device scan
```

I was testing this in stages: the SnapRAID disks weren't encrypted yet, so their section of the unlock script was commented out for now. After mounting the filesystem, the script also starts the dependent services again:

```bash
for container in "${DOCKER_CONTAINERS[@]}"; do
  docker start "$container"
done

for service in "${SYSTEMD_SERVICES[@]}"; do
  systemctl start "$service"
done
```

### Step 9: encrypting the first SnapRAID disk

Similarly to the mdadm device, I had to make local copies using free space on the other drives. This means working one disk at a time.

First up: `/data/seriale` on `/dev/sdg1`. Once its contents were safely copied to `/data/filmy/backup`, the disk itself could be wiped and re-encrypted. I turned the relevant part of the setup script into something reusable, since I'll be running it four times (the remaining video disks, plus the parity disk):

```bash
umount "$MOUNTPOINT" 2>/dev/null || true
awk -v mp="$MOUNTPOINT" '$2 != mp' /etc/fstab > /etc/fstab.tmp && mv /etc/fstab.tmp /etc/fstab
wipefs -a "$PARTITION"
```

I switched the fstab cleanup from a `sed` pattern match to an `awk` filter on the exact mountpoint field - a substring match could accidentally catch something like `/data/seriale1`. In the past, I used more, but smaller drives; old paths were still present here and there.

Same key setup as the btrfs pair: the same `master.key`, and the same recovery passphrase added as a second key slot.

```bash
cryptsetup luksFormat --type luks2 "$PARTITION" --key-file "$KEYFILE"
printf '%s' "$RECOVERY_PASSPHRASE" | cryptsetup luksAddKey "$PARTITION" --key-file "$KEYFILE" -
cryptsetup luksOpen "$PARTITION" "$MAPPER_NAME" --key-file "$KEYFILE"
```

I then recreated ext4 with the same options that I used before:

```bash
mkfs.ext4 -m 0 -T largefile4 -L "$LABEL" "/dev/mapper/$MAPPER_NAME"
mkdir -p "$MOUNTPOINT"
mount "/dev/mapper/$MAPPER_NAME" "$MOUNTPOINT"
echo "/dev/mapper/$MAPPER_NAME $MOUNTPOINT ext4 noauto,nofail,nodev,noatime 0 0" >> /etc/fstab
```

Next, the data goes back onto `/data/seriale`, verified the same way as step 6, and its LUKS UUID gets added to the (still commented-out) `SNAPRAID_DISKS` block in the unlock script. 

### Step 10: encrypting the rest of the SnapRAID disks

Then it's the same routine again for `filmy`, `video2` and `parity1`. Only once it was done, I uncommented the SnapRAID block from the `unlock-mount.sh` script. I ran `snapraid --force-uuid check | tee snapraid.log 2>&1` to confirm the array's fine. SnapRAID refuses to run when more than one disk changes, so the force parameter is needed. Then I shredded the unencrypted `master.key`. Finally, a reboot, to confirm everything was working as planned. It was!

## Summary

The whole process took three days. Most of that was waiting for the file copy or verification (or idle time when it was done but I was away). Actual time spent at the terminal - maybe 2 or 3 hours.

As a result, I got bitrot protection on my main array, plus all the nice features of btrfs. I'm not enabling compression (most space is used by already compressed files, such as JPEG photos, MP3 audio or archives). I'm surely going to use snapshots.

Encryption was the most important goal. Most files on the NAS aren't confidential - I wouldn't care if my music collection leaks. But some are personal. My laptops have been encrypted for years, by encrypting the NAS I closed a major hole. Even if it was unlikely to be exploited, it didn't feel proper.

## Tips

I doubt anyone would be doing exactly the same thing, but maybe something similar?

### Drive letters can change

After a reboot, /dev/sda can become /dev/sde. There are several ways to deal with it:

- **UUIDs** are the best permanent solution to use in /etc/fstab or scripts. They don't change, unless you reformat the filesystem.
- **lsblk** is your friend. For the commands you type manually, short drive paths are convenient, `lsblk` is the quickest way to check all drives. Or, a less handy `lsblk -o NAME,TRAN,UUID,FSTYPE,MOUNTPOINT` gives you UUIDs and transport type (usb, sata, nvme and others).
- **Filesystem labels** can be used in fstab or mount commands, but on an encrypted machine, they're only visible once the drives are unlocked.
- **LVM**, if used, can scan all devices for PVs, with the same caveat about encrypted drives.

### Use screen or tmux

All the copying or verification commands take hours to run. If your server is running headless and you log in with ssh from another machine, you need to make sure the commands won't be stopped if your connection is interrupted.

### Have more than one copy

I only worked on local copies during the migration. But it's easy to make a slip and type "wipefs /dev/sdf1/" when you actually meant "sdg1". It didn't happen to me, but I was prepared for it. Off-site backup gives peace of mind, local backup is faster, have both.

### Monitor hard drive throughput

Two useful commands: `iotop` shows which process reads/writes most data. If the throughput is lower than expected, `iostat -x 1` will show whether source or target is to blame - look for high *%util* and *w_await*.

In my case, the first attempt to make a local copy started at 250MB/s, but in a few seconds dropped to 30MB/s. Iostat showed that the destination disk was the bottleneck. Turned out the disk I'd picked was an SMR model. And that's exactly what's expected from SMR drives - once their write cache fills up, write speed drops to unacceptable values. I checked my HDDs, luckily one of my CMR drives (WD Red Plus) also had enough free space. Copying speed was a more sensible 100MB/s (the bottleneck was now the source drive, and I couldn't achieve anything better from this hardware).

Later in the same copy job, speed dropped to just a few MB/s for a different reason: a scheduled mdadm RAID consistency check had started and was competing for reads on the same array. That was more tricky to find, since the kernel task didn't show up on iotop. `cat /proc/mdstat` showed what was happening and that the task would take 10 hours to complete; `echo idle > /sys/block/md0/md/sync_action` paused it. I didn't need the check, in a moment I'd be wiping the array anyway.
