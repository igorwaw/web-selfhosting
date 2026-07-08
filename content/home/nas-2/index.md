---
title: "Storage server, part 2: disk drives, RAID and SnapRAID"
date: 2023-04-14T17:36:00
draft: false
tags: ["storage"]
---

(first published on 2023.03.14, rewritten on 2026.07.08)

## What I have now

Again, before going into details, this is my current setup.

- System drive: 256GB SSD (no redundancy)
- Array for miscellaneous data: software RAID1 (Linux mdadm) on 2x3TB drives
- Array for audio/video files: SnapRAID on 4 HDDs, mixed sizes (1TB, 1.5TB, 2x3.6TB), one of them USB

## Do you need RAID?

RAID stands for Redundant Array of (Inexpensive|Independent) Disks. Which means the data is stored on more than one disk. If one HDD fails, the array will continue to operate, your data will be still available. When you replace the failed drive, the array will rebuild.

### RAID vs backup

RAID protects you from drive failure.

Backup protects you from drive failure, controller failure, accidentally deleting a file, ransomware encrypting all your drives, fire, theft, flood and pretty much any other reason of data loss.

If you're going to choose between the two, choose backup. One good reason to have RAID in addition to backup is recovery time. Restoring terabytes of data from backup takes hours or days, RAID just continues to work. Which is why RAID is necessary for professional servers, to keep the business running, for home use it's optional.

## Which RAID is right?

### Hardware vs software

If you read very old articles, they might argue that software RAID is slow. That is not the case anymore. Modern CPUs (as in: made in the last 15 years or so) are so fast you won't notice any performance impact under normal conditions. Maybe during the array rebuild, but even then HDD speed will be the bottleneck.

Proper RAID controllers, e.g. MegaRAID or Dell PERC, offload everything from the CPU. I worked with them on real servers (in those unusual cases when you still use a physical server), but I'm not buying one for home. But if you happen to have one, you can consider using it.

Some home motherboards offer hardware RAID, but do it so poorly that it's actually slower than software RAID. And I wouldn't trust them with my data.

Hardware RAID gives an abstraction layer between your drives and your OS. You configure the array in BIOS setup tool or with an additional utility (e.g. megacli), the OS sees a single SCSI drive. It simplifies the view - either you work with physical drives or with filesystems, never mixing the two - but it also means you can't use standard Linux tools to test and monitor the hard drives.

For most people, the choice is between:

- standard Linux software RAID (built into kernel, configured with mdadm)
- modern filesystems (ZFS, btrfs) that combine filesystem, RAID and volume management
- RAID-like solutions such as SnapRAID 

There are, as usual, tradeoffs, more on that later. 

### RAID levels

### RAID0 - striping

R in RAID stands for Redundant. RAID0 isn't - it spreads the writes across all drives to increase performance. If you lose just one drive, you lose the whole array. 

### RAID1 - mirroring

The most basic form of RAID. The same information is written to each drive in a pair. If one fails, the other continues to function as if nothing happened. When both work, read throughput is increased compared to a single drive (data can be read from both simultaneously), write throughput is similar to a single drive, maybe just a bit slower (need to write on both and it's mostly done simultaneously). Rebuilding the array
after replacing the drive is a simple process of copying data. It's a very safe level, but wastes half of the disk space. 

The nice thing about Linux software RAID is you can take out one disk from a pair, install it in a machine without RAID support and just use it like a regular drive, all the files would be accessible.

### RAID5 - parity

RAID5 stores parity information. Think of it like this. Disk 1: data set A, disk 2: data set B, disk 3: A+B. If for example drive 2 fails, it can be recreated by calculating "disk 3 - disk 1". Except the data and parity are distributed between the disks, not written on a dedicated one (that was RAID 3 and 4, but nobody uses them anymore). And you can have more
disks than 3. And the operation is not the sum. But you get the idea.

RAID5 can survive a failure of one drive in the array, if the other one fails before the rebuild is done, the whole data is lost. 

A huge advantage of RAID5 is the efficient use of storage. RAID1 always has a 50% capacity of disks. RAID5 on 3 drives - 66%, on 4 drives - 75%, etc. But there are also disadvantages. Performance is not as good as in RAID1. Read throughput is about the same as from a single disk, write throughput is worse and modifying small files is the biggest problem: the controller (or OS) needs to read the original sector, recalculate parity, write new data and new parity.

But the worst thing is what happens when a drive fails. Every read requires calculating the data from parity, hurting performance. Rebuilding requires recalculating the whole data contained on the failed disk from the information stored on all other disks. This means the process is long and requires a lot of operations on the remaining disks, increasing the chance that one of them fails as well.

For this reason, RAID5 is not recommended for professional use. For home uses, the opinions vary. I think that for small arrays (3-5 disks) the efficiency might be worth the risk. And you have a backup anyway, right? If you want to be extra safe, choose RAID1.

### RAID6 - parity, but more of it

RAID6 is like RAID5, but it stores each parity block twice, on different drives. That means the array survives the failure of 2 hard drives.

Four disks are the minimum number of hard drives for RAID6 and would give you the same storage efficiency as RAID1, but with more complexity. It's a level of choice for large arrays in professional settings (that usually also have hot spares and replace disks every few years even if they don't show any problems, all to minimise the risk of a second drive failure before the rebuild is done). But if you're managing one, you shouldn't be getting your knowledge from some random guy's blog.

### RAID10 - 1+0

Combines mirroring and striping to give you both redundancy and performance. Sometimes used in professional settings, if throughput is more important than storage efficiency. Not much use at home.

### RAID levels at a glance

| RAID | Min. disks | Usable capacity | Fault tolerance | Read perf | Write perf | Notes |
|---|---|---|---|---|---|---|
| RAID 0 | 2 | 100% (all disks) | None - any disk failure loses everything | High | High | Striping only, no redundancy |
| RAID 1 | 2 | 50% (1 disk's worth) | 1 disk (per mirror pair) | High | Normal | Simple mirroring |
| RAID 5 | 3 | (n-1)/n | 1 disk | High | Reduced (parity calc) | Write hole risk on unclean shutdown |
| RAID 6 | 4 | (n-2)/n | 2 disks | High | Lower (double parity calc) | Safer than RAID5 for large/many disks |
| RAID 10 | 4 | 50% | 1 per mirror pair (up to half the disks, if spread right) | High | High | Mirror + stripe, best perf/redundancy balance, costly on capacity |
| RAID-Z1 (ZFS) | 3 | (n-1)/n | 1 disk | High | Reduced | Like RAID5, no write hole (COW) |
| RAID-Z2 (ZFS) | 4 | (n-2)/n | 2 disks | High | Lower | Like RAID6, no write hole |

## Flexibility of Linux RAID

One good feature of mdadm - if you're into DIY solutions and are not afraid of running strange configurations for some time - is the flexibility. If you plan to use RAID1 in future, but only have one drive now, you can create an array and declare one drive missing. It will show as degraded - obviously - but you can add the drive later and "rebuild". It works the other way too - you can remove the drive if you temporarily need it for something else. Even better, put it into another computer with no RAID configured and it will still show all the data.

If you need more space and decide to change RAID1 to RAID5, that's just two commands: one to add a 3rd drive and one to change RAID level. Similarly, you can convert RAID5 to RAID6.

Note that reshaping the array takes hours or days and your data might be at risk if the process is interrupted or if a drive fails mid-process (though RAID1 to RAID5 should be safe). Always check mdadm documentation, consider testing on VMs first and make sure you have a tested backup.

But still, such operations are occasionally useful for home scenarios when you need to manage limited disk space. And no other tool offers that kind of flexibility.

## SnapRAID

A relatively new option for home NAS is SnapRAID. It's an interesting take that combines the advantages of RAID5/6 with the advantages of no RAID at all. How is that even possible? The name SnapRAID comes from Snapshot (as in: snapshot backups) and RAID, because it works like something in between the two:

- you have any number of data disks, they can have any filesystem such as ext4, XFS, JFS; could be different filesystems, different sizes,
- you have between 1 and 6 parity disks, they need to be as large as the largest data disk.

During normal operation, you only use the data disks, parity drives are not touched until you run the "snapraid sync" command (which is run either by cron, e.g. at night, or manually after you changed something on the data drives, depending on the use case). That works best for large files that are written once and never change - such as video files. Compared to proper RAID, there are some interesting advantages:

- you can add and remove disks whenever you like and combine sizes,
- the drives can already contain the data when added, they would still contain the data when removed,
- you can also use it to restore files that were accidentally deleted (if you're fast),
- there's very little disk space overhead (e.g. if you use 1 parity disk for 4 data disks, that's only 20%)
- there's no slowdown, no CPU usage and no extra I/O during normal operation, only during sync,
- you can setup your disks to power down and only the one that's currently accessed will spin up (RAID5 or 6 would spin up all disks),
- if multiple disks break, you can still access the data on the other drives - unlike RAID5 and 6 when they would all be useless,
- while it is not recommended to use SnapRAID on USB drives, it is possible.

The downsides: your files are not immediately protected from drive failure and the technology is not as well tested as mdraid.

## Testing the drives

Some of the hard drives I use are old, maybe even 10 years old. But even with the new drives it's a good idea to test them. Especially if you can replace them under warranty. I had some old USB drives too and did the following to quickly check them:

- connected them to my laptop one by one,
- run the short self-test: `smartctl -t short /dev/sdb`
- if there was already some data, checked the filesystem: `fsck -f /dev/sdb1`
- short self-test takes about 2 minutes, after that time I would see the results plus all other SMART data: `smartctl -a /dev/sdb`

Two drives were showing quite alarming results (failed self-test, high values in Reallocated_Sector_Ct). One of them had some old backups on it, it was also showing filesystem corruption and some files could not be read (nothing important though).
I copied the data, wiped the drives and threw them away.

Should you immediately throw away the drive showing any errors in SMART data? It's up to you, if you trust your RAID and backup, you might take your chances. I'd say that one-digit numbers in Reallocated_Sector_Ct or Current_Pending_Sector are no cause for alarm. Some drives develop a few bad sectors early and then continue to work fine for years. But if you see the numbers rising or SMART overall-health self-assessment goes bad, you better get a new drive soon. Remember that a drive can fail without a SMART warning anyway.

In fact, two other drives were showing some "not great, not terrible" SMART attributes. I marked them as suspicious and made sure they are backed up. It's handy to have a label writer when you're dealing with 20 USB drives.

Then after connecting the drives to the target system it was time for a proper checkup. First, a long SMART self-test which takes several hours: `smartctl -t long /dev/sdX`

Another thing I did was a badblocks test overwriting the whole disk: `badblocks -b 4096 -wsv /dev/sdX`
To reiterate, **it overwrites everything on the disk!** Only use it with an empty drive. And it takes days. It was quite a pain, especially since some drives already had data, so I had to copy it around. But once it was done, I can be reasonably sure that every sector of the disk works properly. And if any errors were discovered and corrected by the drive firmware, they should show up in the SMART data.
