Title: Storage server, part 3: software and configuration
Date: 2023-04-14 17:38
Status: published
Tags: storage


## Choosing the OS

There are some distributions of Linux or FreeBSD specially designed for NAS. Or you can use ordinary Linux
(or Windows, I won't judge). NAS distribution simplifies management, you get something similar to a Synology
or Qnap device. But you need to play by their rules, while ordinary Linux can be customized any way you like.
I don't have a problem configuring Linux servers without a GUI. Plus, on my last two attempts, I chose a vanilla
system and used Ansible. I can reuse the same playbook. That's the nice thing about Ansible: configuring my NAS for
the first time took me more time than doing the same thing by hand, but the next attempts were almost fully automated.
Installing the base system was the manual part (it could be automated as well, but it doesn't make much sense to
automate a one-time task). 


## How to share files

The two main contenders are Samba and NFS. NFS allows using Linux-specific attributes such as file ownership and ACLs 
while Samba does the same for Windows. You can run both services on the same machine and even share the same
files, if you need both Windows and Linux file permissions then go for it. If you have only one OS on your network, then
the choice is obvious too. 

The less common choice is iSCSI, which exports a block device instead of a filesystem. From the point of view of the
connected client, it will look a lot like a local drive which can be formatted and used in any way. Very useful for
many professional settings, for example for live migrating VMs between hosts. Not so much for the home, unless
you mostly want to train your sysadmin skills. 

For now, I went with Samba only. I don't really need any permissions, I'm OK with making all files on the share accessible to all
systems and users on my LAN. If I need it later, I can get NFS or iSCSI running in a few minutes.


## Configuration with Ansible

I installed the base system, set the static lease on the DHCP server and launched Ansible. Main playbook firefly.yml (that's
how I called my NAS) is very simple, because the real deal is in the roles. Most are shared with my other computers:

- linux_common is the basic configuration for all Linux systems, be it physical or VMs,
- docker_host and qemu_host are for running containers and VMs
- firefly is the main thing.

I'll describe the shared roles separately, now let's focus on the nas role. I based the files on several configurations I found in Ansible Galaxy.
It does quite a lot, so I split it for readability and once again the main file was made very simple:

```yaml
- import_tasks: pre-tasks.yml
- import_tasks: mountpoints.yml
- import_tasks: samba.yml
- import_tasks: post-tasks.yml
```

File tasks/samba.yml  is mostly taken from https://github.com/bertvv/ansible-role-samba with only minor modifications. I added three
files with tasks required before and after configuring Samba.

Before:

- create a system user for samba, it will own the shared files
- create mount points: make directories where the new filesystems will be mounted, modify fstab, mount filesystems
- change ownership of files

After:

- install and configure wsdd, or  Web Service Discovery, software that allows Windows to find Samba shares,
- install and configure hd-idle, software that turns off inactive USB drives (video disks are going to be unused most of the time)


### Alternative to SnapRAID

Before I discovered SnapRAID, when I tried to create a NAS only with USB drives, I used a different solution to keep my data safe from
drive failure. I added the drives in pairs, eg. if a main drive was called "video1" there was also "video1-backup". And I generated a script
to copy all data to the backup disk. That's where Ansible really shined. All I needed was a few lines in the playbook:

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

Where "samba_shares" contains the list of filesystems. Now, if I added another disk pair, I only need to edit "samba_shares" to modify fstab, smb.conf and the backup script.


