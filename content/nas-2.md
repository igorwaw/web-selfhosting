Title: Storage server, part 2: disk drives, RAID and SnapRAID
Date: 2023-04-14 17:36
Status: published
Tags: storage


## Which RAID is right?

I don't trust hard drives and neither should you. They WILL fail, it's just a matter of time. One way to deal with
drive failures is RAID (note: RAID is not a backup, you should have both, or if you have to choose between the
two, choose backup). RAID stands for Redundant Array of [Inexpensive|Independent] Disks. Linux can do
RAID in software. In the past, software RAID was slow, but modern CPUs are so fast they don't really notice the
extra load under normal conditions - although they could be a bottleneck during the array rebuild. Proper RAID
controllers, eg. MegaRAID, offload everything from the CPU. I worked with them on the real servers (in those unusual
cases when you still use a physical server), but I'm not buying one for home. Some home motherboards offer hardware
RAID, but do it so poorly that it's actually slower than software RAID. And I wouldn't trust them with my data.

The most basic form is RAID1 or mirroring. The same information is written to each drive in a pair. If one
fails, the other continues to function as if nothing happened. When both work, read throughput is increased
compared to a single drive  (data can be read from both simultaneously), write throughput is similar to a single
drive, maybe just a bit slower (need to write on both and it's mostly done simultaneously). Rebuilding the array
after replacing the drive is a simple process of copying data. It's a very safe level, but wastes half of the disk space. 
The nice thing about Linux software RAID is you can take out one disk from a pair, install it in a machine without
RAID support and just use it like a regular drive, all the files would be accessible.

RAID5 stores parity information. Think of it like this. Disk 1: data set A, disk 2: data set B, disk 3: A+B. If for example
drive 2 fails, it can be recreated by calculating disk 3 - disk 1. Except the data and parity is distributed between the
disks, not written on a dedicated one (that was RAID 3 and 4, but nobody uses them anymore). And you can have more
disks than 3. And the operation is not the sum. But you get the idea. RAID5 can survive a failure of one drive in the array,
if the other one fails before the rebuild is done, whole data is lost. RAID6 is similar but writes every parity block on 2
disks and survives the failure of 2 drives.

A huge advantage of RAID5 is the efficient use of storage. RAID1 always has a 50% capacity of disks. RAID5 on 3 drives - 66%,
on 4 drives - 75%, etc. But there are also huge disadvantages. Performance is not as good as in RAID1. Read throughput is
about the same as from a single disk, write throughput is worse and modifying small files is the biggest problem: the
controller (or OS) needs to read the original sector, recalculate parity, write new data and new parity. But the worst thing is
what happens when a drive fails. Every read requires calculating the data from parity, hurting performance. Rebuilding
requires recalculating the whole data contained on the failed disk from the information stored on all other disks.
This means the process is long and requires a lot of operations on the remaining disks, increasing the chance that one
of them fails as well.

For this reason, RAID5 is not recommended for professional use. For home uses, the opinions vary. I think that for small
arrays (3-5 disks) the efficiency might be worth the risk. And you have a backup anyway, right? If you want to be
extra safe, choose RAID1. What about RAID6? It only makes some sense for large arrays. Four disks are the minimum
size and would give you the same efficiency as RAID1, but with more complexity. It's a level of choice for large arrays
(that usually also have hot spares and replace disks every few years even if they don't show any problems, all to minimize
the risk of a second drive failure before the rebuild is done), but if you're managing one, you shouldn't be getting your
knowledge from some random guy's blog.

All of this is immaterial because I'm only doing RAID on two disks. But here's the nice thing about software RAID on
Linux: you can change the RAID level on the running array - add a third one to a 2-disk set and convert to RAID5 for the extra
space. You can even make RAID on one disk - declare the other disk missing for now, the array will start in degraded mode
and rebuild when you add the second drive. Check it on a VM if you don't believe me. So it's RAID1 for now,
maybe I will change it later. Or maybe I'll just move to bigger drives.


## SnapRAID

A relatively new option for home NAS is SnapRAID. It's an interesting take that combines the advantages of RAID5/6 with
the advantages of no RAID at all. How is that even possible? The name SnapRAID comes from Snapshot (backups)
and RAID, because it works like something in between the two:

- you have a number of data disks, they can have any filesystem such as ext4, XFS, JFS; could be different filesystems, different sizes,
- you have between 1 and 6 parity disks, they need to be as large as the largest data disk.

During normal operation, you only use the data disks, parity drives are not touched until you run the "snapraid sync" command
(which is run either by cron, eg. at night, or manually after you changed something on the data drives, depending on the use case).
That works best for large files that are written once and never change - such as video files. Compared to proper RAID, there are some
interesting advantages:

- you can add and remove disks whenever you like and combine sizes,
- the drives can already contain the data when added, they would still contain the data when removed,
- you can also use it to restore files that were accidentally deleted (if you're fast),
- there's very little disk space overhead (eg. if you use 1 parity disk for 4 data disks, that's only 20%)
- there's no slowdown and no CPU usage / extra IO during normal operation, only during sync,
- you can setup your disks to power down and only the one that's currently accessed will spin up (RAID5 or 6 would spin up all disks)
- if multiple disks break, you can still access the data on the other drives - unlike RAID5 and 6 when they would all be useless,
- while it is not recommended to use SnapRAID on USB drives, it is possible

The downsides: your files are not immediately protected from drive failure and the technology is not as well tested as mdraid.
My choice? Standard Linux RAID1 for general-purpose storage, SnapRAID for videos.


## Testing the drives

The disks I'm using are old, some of them more than 5 years old. But even with the new drives it's a good idea - especially if you
can replace them under warranty. I did the following to quickly check the USB drives:

- connected them to my laptop one by one,
- run the short self-test:  `smartctl -t short /dev/sdb`
- if there was already some data, checked the filesystem: `fsck -f /dev/sdb1`
- short self-test takes about 2 minutes, after that time I would see the results plus all other SMART data: `smartctl -a /dev/sdb`

Two drives were showing quite alarming results (failed self-test, high values in Reallocated_Sector_Ct). One of them had
some old backups on it, it was also showing filesystem corruption and some files could not be read (nothing important though).
I copied the data, wiped the drives and threw them away.

Should you immediately throw away the drive showing any errors in SMART data? It's up to you, if you trust your RAID and backup,
you might take your chances. I'd say that one-digit numbers in Reallocated_Sector_Ct or Current_Pending_Sector are no cause for
alarm. Some drives develop a few bad sectors early and then continue to work fine for years. But if you see the numbers raising
or SMART overall-health self-assessment goes bad, you better get a new drive soon. Remember that a drive can fail without
a SMART warning anyway.

In fact, two other drives were showing some "not great, not terrible" SMART attributes. I marked them as suspicious and made sure
they are backed up. It's handy to have a label writer when you're dealing with 20 USB drives...


Then after connecting the drives to the target system it was time for a proper checkup. First, a long SMART selftest which takes several
hours:  `smartctl -t long /dev/sdX`

Another thing I did was a badblocks test overwriting the whole disk: `badblocks -b 4096 -wsv /dev/sdX`
To reiterate, **it overwrites everything on the disk!** Only use it with an empty drive. And it takes days. It was quite a pain,
especially since some drives already had data, so I had to copy it around. But once it was done, I can be reasonably sure that
every sector of the disk works properly. And if any errors were discovered and corrected by the drive firmware, they should
show up in the SMART data.


## Formatting the drives

As I wrote before, I plan to keep some video files on USB drives. Disks  in Linux are usually
addressed by the device name. The problem with USB drives is the names are not persistent: the disk that's now /dev/sde
can become /dev/sdf on the next reboot. There are several ways to deal with it:

- assign device names in udev rules,
- use filesystem UUIDs,
- use filesystem labels,
- use LVM, it scans all devices and doesn't care about their order.

I chose labels, they are easy to use and good enough for a small setup. All I needed was an extra parameter when creating the filesystem:
`mkfs.ext4 -m 0 -T largefile4 -L 'video1' /dev/sde1`

Then use the same label in /etc/fstab :
```bash
LABEL=video1     /media/video1    ext4   nodev,noexec,noatime,nofail,x-systemd.device-timeout=4 0 0
```

A note on other mkfs options: -m 0 disables reserving space for root - by default 5% is reserved, that's only possibly useful on a system disk.
Option -T largefile4 changes the inode size to 4MB from the default of 16KB. Inode is an allocation unit. 4MB is a good value for
video files which are hundreds of MB to several GB in size. Unused inodes take up some disk space. But the size taken by each
file is rounded up to the inode size, so for filesystems containing text documents, photos, applications, etc. - pretty much
everything other than videos or filesystem images - you should stick to the default. 

What do the fstab options mean? Nodev and noexec are for increased security, they forbid executables and device files on the
data filesystems; noatime means access time will not be recorded (I use this option for all filesystems on all my machines);
nofail means the system will boot even if the device can't be mounted and device timeout is just that - how long the system will try to mount the drive before
giving up. By default systemd will stop if it can't mount the drive - it makes sense for system disks, but not for data.
In that case, I'd rather have my server available on the network so I can SSH and fix it.
