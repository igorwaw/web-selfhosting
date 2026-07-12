---
title: "Storage server, part 4: putting it all together"
date: 2023-04-14T17:38:00
draft: false
tags: ["storage"]
---

(partly based on old post from 2023.04.14, rewritten on 2026.07.09)


## Choosing the OS

There are some distributions of Linux or FreeBSD specially designed for NAS use. Or you can install ordinary Linux (or Windows, I won't judge). NAS distribution simplifies management, you get something similar to a Synology or QNAP device. But you need to play by their rules, while ordinary Linux can be customised any way you like.

I don't have a problem configuring Linux servers without a GUI and I wanted a place for experiments in addition to plain NAS. Plus, I already used a vanilla system (Debian, stable release) on my previous attempts to run a NAS. I configured it with Ansible. I was able to reuse the playbook for my 3rd NAS. That's the nice thing about Ansible: configuring my NAS for the first time took me more time than doing the same thing by hand, but the next attempts were almost fully automated.

### Not for everyone

I don't necessarily recommend everyone to follow these steps. I'm OK if my NAS is a bit difficult to configure, if it means I'm honing skills I need for my job. I don't go as far as having a dedicated homelab, I just mix the two uses for home servers.

In particular, Ansible doesn't make sense for a server that you're not going to rebuild. Unless you want to write a playbook because you haven't done it at your day job recently and you don't want your skills to deteriorate. Despite my enthusiasm for Ansible, I advise everyone to skip it, unless they have a good reason.

### Base installation

In my case, that was just a simple Debian install. Write the ISO to a thumbdrive, plug it into the NAS, connect screen and keyboard for the initial setup. Make sure the installer writes to the system drive only and doesn't touch the data HDDs at all (you can disconnect them to be sure).

Installing the base system and configuring the hard drives was the manual part. It could be automated as well, but it doesn't make much sense to automate a one-time task.

## Formatting the drives

### Main data drives

Btrfs RAID1 on top of two LUKS-encrypted HDDs. I created 2 subvolumes, they got mounted at:

- /data/noshare - stuff that won't be shared by SMB or NFS, mostly space for services running on the NAS (Syncthing, Jellyfin, Prometheus, photo archive)
- /data/other - stuff (other than videos) that's shared over LAN - my music and audiobook collection, old projects, files copied from old computers that I'm going to sort in mythical free time

I haven't used any extra options for btrfs and didn't do any performance tuning. So far, the defaults work well.

### Video drives

As I wrote before, I keep video files on several drives protected by SnapRAID. It does checksum-based bitrot protection and I see no reason to snapshot the filesystem, so there was no need for btrfs. I used ext4, but this time with some extra options when creating the filesystems: `mkfs.ext4 -m 0 -T largefile4 -L 'video1' /dev/mapper/luks-video1`

- `-m 0` disables reserving space for root - by default 5% is reserved, that's only possibly useful on a system disk. 
- `-T largefile4` changes the inode size to 4MB from the default of 16KB. An inode is an allocation unit. 4MB is a good value for video files which are hundreds of MB to several GB in size. Fewer inodes use less disk space for metadata, larger inodes increase performance for large files. But there's a tradeoff: the size taken by each file is rounded up to the inode size, and if you run out of inodes you can't write anything to the disk even if it has free space. For filesystems containing text documents, photos, applications, etc. - pretty much everything other than videos or filesystem images - you should stick to the default.
- `-L video1` adds a filesystem label. A convenience on a machine with multiple drives, one more way to select the right filesystem.

## How to share files

The two main contenders are Samba and NFS. NFS allows using Linux-specific attributes such as file ownership and ACLs while Samba does the same for Windows. You can run both services on the same machine and even share the same files, if you need both Windows and Linux file permissions then go for it. If you have only one OS on your network, then the choice is obvious too. 

The less common choice is iSCSI, which exports a block device instead of a filesystem. From the point of view of the connected client, it will look a lot like a local drive which can be formatted and used in any way. Very useful for many professional settings, for example for live migrating VMs between hosts. Not so much for the home, unless you mostly want to hone your sysadmin skills.

For now, I went with Samba only. I don't really need any permissions, I'm OK with making all files on the share accessible to all systems and users on my LAN. If I need it later, I can get NFS running in a few minutes.


## Configuration with Ansible

I installed the base system, set the static lease on the DHCP server and launched Ansible. Main playbook firefly.yml (that's how I called my NAS) is very simple, because the real deal is in the roles. Most are shared with my other computers:

- linux_common is the basic configuration for all Linux systems, be it physical or VMs,
- docker_host and qemu_host are for running containers and VMs
- firefly is the main thing.

I'll describe the shared roles separately, now let's focus on the nas role. I based the files on several configurations I found in Ansible Galaxy. It does quite a lot, so I split it for readability. The main file just imports the other four:

```yaml
- import_tasks: pre-tasks.yml
- import_tasks: mountpoints.yml
- import_tasks: samba.yml
- import_tasks: post-tasks.yml
```

File tasks/samba.yml is mostly taken from <https://github.com/bertvv/ansible-role-samba> with only minor modifications. I added three files with tasks required before and after configuring Samba.

Before:

- create a system user for samba, it will own the shared files
- create mount points: make directories where the new filesystems will be mounted, modify fstab, mount filesystems - change ownership of files

After:

- install and configure wsdd, or Web Service Discovery, software that allows Windows to find Samba shares,
- install and configure hd-idle, software that turns off inactive USB drives (video disks are going to be unused most of the time)

## Historical notes

### USB drives

My first attempt ran on Odroid and used only USB drives. It didn't work well. Later when I moved to a PC case, I still used several USB drives. When they failed or ran out of space, I replaced them with internal drives. I don't have any USB drives connected to NAS anymore.

The only reason I used USB drives is that I already had a large number of them.

### June 2023 update: SnapRAID recovery

It was inevitable that a disk would fail. In fact, two disks failed at once (at that time, I had more USB drives and didn't trust them, so I used two parity drives). How I dealt with it:

- I unplugged the failed disks (they were both USB drives).
- Plugged new disks of the same size (could be bigger, could probably be smaller if they weren't filled to the capacity, but I had the same size disks).
- Formatted them the same way (again, not necessary, but since the setup worked before, I didn't change anything), mounted in the same place.
- Checked the disk number in /etc/snapraid.conf, in my case these were d3 and d4.
- Ran the command to recover files: `snapraid -d d3 -l fix.log fix` for one disk and `snapraid -d d4 -l fix2.log fix` (I could have skipped '-d DISKNAME' to fix everything at once). Note: you should run it under screen or tmux as it will take a very long time - hours, maybe days.
- Ran the command to check the recovered files: `snapraid check` (again, many hours).
- Finally, re-synchronised the array just to be sure: `snapraid sync` (that was, as expected, quick).

### Alternative to SnapRAID

Before I discovered SnapRAID, when I tried to create a NAS only with USB drives, I used a different solution to keep my data safe from drive failure. I added the drives in pairs, e.g. if a main drive was called "video1" there was also "video1-backup". And I generated a script to copy all data to the backup disk. That's where Ansible really shone. All I needed was a few lines in the playbook:

```yaml
  name: Generate backup script
  template:
	dest: /etc/cron.daily/rsync-backup.sh
	src: rsync-backup.sh.j2
```

And a very short template:

```bash
#!/bin/bash
# rsync backup file -- Managed by Ansible, please don't edit manually
#
# {{ ansible_managed }}

{% for share in samba_shares %}
mount /data/{{ share.name }}-backup && \
  rsync -va /data/{{ share.name }}/ /data/{{ share.name }}-backup/
umount /data/{{ share.name }}-backup

{% endfor %}

```

Where "samba_shares" contained the list of filesystems. When I added another disk pair, I only needed to edit "samba_shares". Ansible modified fstab, smb.conf and the backup script.
