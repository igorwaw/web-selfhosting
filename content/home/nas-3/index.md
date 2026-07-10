---
title: "Storage server, part 3: ZFS and btrfs vs traditional filesystems"
date: 2026-07-09T14:00:00
draft: false
tags: ["storage"]
---

## What I have now

I use **btrfs RAID1** for all miscellaneous data filesystems on my NAS and **ext4 with SnapRAID** for video files. Previously, I used ext4 for all. Both approaches have their merits. But first, one important definition.

## What is bitrot (silent data corruption)?

Digital data, in general, is resistant to errors. There's always a large enough difference between 0 and 1, on any storage or transmission media, that background noise and other random factors won't flip one to the other. Unless the noise is so high it corrupts many bits, which is at least immediately detectable, but it can't flip a single bit.

Except it sometimes can. It's not impossible, just very improbable, and if your device contains billions of bits, it will happen - especially on modern high-density media, and especially when it ages. The causes are varied: magnetic domains weakening on HDDs, charge leaking from NAND cells on unpowered SSDs and USB drives, a short voltage spike, tiny movement of HDD head during write, cosmic rays (this one seems to get the most coverage, but it's the least probable).

The effect is the same. The device continues to function, but some individual bits are changed. No error is reported by the OS or drive electronics. Sometimes, when you read files from many years ago you might notice a weird rectangle in a JPG photo, or an MP3 file starts skipping. You begin to wonder whether the file was corrupt from the beginning, after all, digital files don't age. Now you know: they do.

It's more of a concern for a NAS than for a regular computer. It's a matter of probability: the more data you have, and the longer it sits there without being rewritten, the more likely the bit flip is.

### Protecting against bitrot

Standard RAID doesn't protect against bitrot, neither does standard backup. They might detect that two copies are different, but have no way to tell which one is right. You can store checksums of your files and regularly verify if they changed.

And that's exactly what ZFS and btrfs do. They both store a checksum alongside every block of data. On every read, the filesystem verifies the checksum; if it doesn't match, and you have redundancy (mirror, RAID-Z, RAID1), it automatically reconstructs the correct data from the good copy and can rewrite the bad block.

They also have a "scrub" command, that you should run regularly. It reads part of your dataset and verifies checksums, to also detect errors on those files that you don't read regularly.

SnapRAID also stores checksums of all files. But they are only checked if you run `snapraid scrub` (or `snapraid check`, which runs full verification of the whole drive), not on every read. All the more reason to schedule regular scrubs.

## Modern filesystem

ZFS and btrfs have some common features. It's not a coincidence - btrfs was inspired by ZFS and despite not sharing code, they ended in a similar place. There are other filesystems like that, on Linux and other platforms, though they don't have a full set of features.

Both ZFS and btrfs combine RAID and a volume manager with filesystem functionality. While old-time sysadmins (me included) may frown on this approach - so against the traditional Unix spirit of one tool doing one thing - there are reasons for it: 

- Bitrot correction, as described earlier. If you separated the layers, RAID would have 2 copies of data but doesn't know which one is correct; filesystem would detect bitrot, but would have no way to retrieve the correct copy.
- Array rebuild efficiency. Traditional RAID copies all blocks, because it has no way of knowing which are used, ZFS and btrfs skip empty blocks.
- Better performance without manual tuning. You don't need to align the filesystem's block size to the RAID layer's stripe width, you don't even need to know what that means.

Both also feature Copy-on-Write (CoW) snapshots. Snapshots look like an exact copy of a filesystem, but they only need extra space for the data that's different. Once you get used to working with snapshots, you'll wonder how you could have lived without them:

- Creating "system restore points" before a risky operation such as a distro upgrade and instantly rolling back if something goes wrong.
- Fast local backup with the ability to browse through old versions of a file (note, it doesn't replace regular backup, it lives on the same computer).
- Efficiently storing multiple VMs that are mostly identical.
- A read-only snapshot ensures the data is not modified in the middle of a backup session.
- Snapshots can be sent and received over a network, very efficiently (only changed blocks) allowing fast off-site backup or remote replication.

### ZFS

Older of the two. Started on Solaris in 2001. Later, when large parts of Solaris were published under an open source licence, ported to FreeBSD. The "ZFS on Linux" project began in 2008, but wasn't considered stable before version 0.6.0 from 2013.

Licence doesn't allow integrating it directly into the Linux kernel, the module needs to be built separately. Some distros ship ZFS kernel module and tools. Some don't, but a determined enough user can build the module themself. Yet, it feels a bit like a second class citizen in Linux. You can't boot the OS from it (except recent versions of Ubuntu that have experimental support), native Linux tools don't work with ZFS - you need to use ZFS tools that use a different vocabulary. Due to being out of kernel, it's often difficult to use it with Secure Boot. Other downsides include high resource usage (depending on features used, it might need a few GB of RAM for itself plus a noticeable amount of CPU time) and difficult performance tuning.

On the plus side, it's the better tested of the two and has more features. It can do equivalents of RAID1, 5 and 6 - and do them in a safer way. A known problem with RAID5/6 is called write hole. If the machine shuts down uncleanly in the middle of a write (e.g. due to a kernel bug or power outage), it's possible that the data was written, but metadata wasn't, leaving inconsistent state. In ZFS, write operations are atomic, they either fully succeed or fully fail.

I tested ZFS and decided against it, mostly due to friction with Linux (though appetite for RAM was a factor too). If your goal is something more akin to a commercial NAS, where you're more interested in file storage than tinkering, you might be satisfied with ZFS. Or if you don't have many years of Linux experience and therefore a strong bias.

### btrfs

The filesystem was developed in the late 2000s as a response to ZFS licensing problems. It has most (but not all) features of ZFS and is superficially similar, even if under the hood it's quite different.

Btrfs was merged into the mainline Linux kernel before it became stable. When it stabilised a few years later, it continued adding new, experimental features. Some users didn't understand which parts of btrfs were safe to use. This is the source of the bad reputation of btrfs.

In fact, these days it's safe to use btrfs on a single disk or in RAID1/10 mode. The features that distinguish it from traditional filesystems (data checksumming, snapshots, subvolumes, compression) work reliably. It is widely used in production e.g. at Facebook, on Synology devices, as a default filesystem in several Linux distros.

The remaining experimental part is RAID5 and 6. Stability is improving with each new version, but it's still considered not safe for production. Most posts about btrfs problems are from people who used the RAID5 mode, or from the very early years.

Compared to ZFS, btrfs is a bit more flexible - handles adding/removing disks in an existing array more easily. It also avoids licensing problems and all the "not invented here" problems that come from it. No extra modules that can lag behind the current kernel version or fail to build. Last but not least, for a greybeard sysadmin - less different from what I'm used to.

## Traditional filesystems

Old, boring filesystems such as **XFS** and (especially) **ext4** still have some upsides. They are simple and therefore predictable. They don't have hundreds of parameters for performance tuning (they have a few, but defaults mostly work). Decades of fsck, forensic tools, and "how to recover an ext4 filesystem" knowledge exist, including commercial data-recovery services. We can safely assume that all edge cases around unusual configurations were already discovered and fixed. Decoupling RAID, LVM and the filesystem means that if something isn't right, you're debugging one layer at a time. For simple use cases, reading and writing files (which, after all, are the main tasks of filesystems) they are usually faster. They use less RAM and CPU and don't need that much disk space for metadata.

Copy-on-write filesystems have an additional failure mode. They hate running out of disk space, and sometimes you can be hit by "write error, filesystem full?" message when df shows plenty of space left. Occasionally, you need to run `btrfs defrag`, `btrfs rebalance` or their ZFS equivalents (in my experience, in some unusual cases "occasionally" turns to "every night from cron", but these were real servers with high utilisation, not a home NAS).

That is why I used ext4 for my SnapRAID filesystems. SnapRAID handles bitrot protection, I don't need two layers doing the same, and I don't need snapshots for my video files - there was no reason for adding complexity. For the regular data, the balance was different. I decided that self-healing of btrfs is worth the additional hassle of setting up something I'm less familiar with. 
