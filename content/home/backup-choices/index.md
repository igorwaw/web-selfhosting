---
title: "Backup, part 1: considerations for local backup"
date: 2026-07-20T17:40:00
draft: false
tags: ["backup"]
---

There's an old saying that there are two categories of people: those who do backups and those who will. It is, of course, completely false. There are also people who lost their data but it didn't teach them anything, people who don't care because they keep most of their stuff in the cloud... Last but not least, people who did backups in the past, know the importance, want to do them, just not today.

Why are so many people reluctant to back up? Simple: it's because all backup solutions are horrible - and I actually wanted to use other words, but I'm trying to keep this blog family friendly. Since I was in the last group, but I wanted to find a better solution than previously used, I started by listing the features I'd like to have. Then I checked open source backup software. Most didn't have all the features, and those that had were even more of a pain to configure. I had some experience with commercial software and it's no better when it comes to the pain part.

## Types of backup systems

I noticed that the modern backup solutions can be broadly divided into 2 groups:

- Personal backup systems for one machine. They usually don't have any server at all, they either copy to a standard Linux system (or something completely different, such as an S3 bucket) or the same software is both a client and a server.
- Large scale systems for backing up hundreds or thousands of machines. They have a server that's often difficult to set up and a simple client.

Nothing in between. What if you need to back up several machines - because you're a geek with several computers, because you have a family, or both? I'd say it's still better to use personal tools and configure a few copies, maybe with some kind of automation or templating. The big systems make it easy to add another machine, but the initial setup is more complex. At some point they might be worth the initial time investment, but it's probably around a few dozen clients, not 5 or 10.

## Features of backup software

### Features obligatory for me

- Backup over LAN to a hard drive on another machine (I'm not interested in tapes, optical media or clay tablets)
- Server for Linux/x86-64
- Client for Linux on x86 and Linux on ARM
- Needs to support all the standard features of the Linux filesystems: soft and hard links, ownership and access rights
- Incremental backups (or rsync-style snapshots)
- Command line (scriptable) client, at least for backup operations
- Easy to set up (that is relative; I'm a seasoned sysadmin so I COULD set up pretty much anything, but I don't want to waste time)
- Simple way to configure which directories are backed up and what files are excluded (that is a really basic requirement, but you'd be surprised that some applications failed on this point)
- Easy to find several older versions of a file to restore
- Generally secure (some kind of authentication, CVE history not terrible)
- Client cannot directly access the backup files

#### Ransomware protection

The last point is important to protect against ransomware. If it encrypts my laptop but can't touch my backups, no big deal: I can restore my files from the last clean backup. But if it's able to encrypt or delete my backups, I'm doomed. A typical ransomware would encrypt files on a mounted network drive. Would it scan the local network for available SMB (Windows file sharing) servers? Maybe. Would it scan a machine for SSH keys and configs? I seriously doubt it, most malware is designed for common environments, not something that's used by 0.0001% of users. Therefore, I plainly reject all solutions that back up files to an SMB share. But SSH based access (SFTP, rsync over SSH) is acceptable for me. In all such cases you can further reduce the risk by using non-default SSH keys, limiting rights of the remote user etc. However, if you think you're at risk of being targeted by APT groups (Advanced Persistent Threat, e.g. an intelligence agency), you need higher security.

### Features nice to have

- Installable with apt (preferably) or Docker
- Configurable with Ansible
- GUI (for less common operations, e.g. choosing a version to restore, GUI can be more convenient than a CLI)
- Client for Windows (I currently have only one Windows machine and it's not my daily driver, I can live without automated backups on it)
- Client and server for other OSes/devices (I don't need them now, but I might in future)
- Image backups in addition to file backups (not obligatory, since I can use another tool for that)
- Basic ability to back up open files, e.g. by taking an LVM snapshot on Linux, using VSS on Windows (it would be more important for Windows clients, on Linux you can safely copy most of the open files; if I occasionally miss some latest changes - whatever, it doesn't need to be perfect)
- Data deduplication (useful, but disk space is cheap and I'm not backing up dozens of almost identical machines)
- Encryption, at rest or in transit. (I'm not paranoid enough to implement Zero Trust Architecture at home, but might use the same solution elsewhere)

GUIs come in two flavours: a traditional client and a web-based interface. The former can sit in a tray to notify about problems and be within reach all the time, the latter is also useful for headless machines (servers). Since it's network accessible, it needs to be kept secure (password, listen on loopback only if not needed on the network / filtered by a firewall if needed). 

### Features that some people might need but are not important for me

Note that some software I considered have these features anyway, I don't mind them as long as they don't get in the way.

- Cloud backup. My plan is to back up the backups using IDrive.
- Easy bare metal restore. It's unlikely I'm going to need it, so if it's a complex process, or if I have to reinstall the system and restore only the data, I'm OK with it.
- Backup over the internet. My NAS is not available from the outside. 
- Advanced access control. It's a home solution, I'm not going to run an AD server here.
- DB backups. You can't simply copy files belonging to MySQL or Postgres (not to mention Oracle) while the DB is running. The files are constantly changed and at any given moment are not guaranteed to have a consistent state. You need to interact with the DB to get a snapshot in time. I don't use any DB at home (except for occasional experiments).

## Software considered

In alphabetical order. Some solutions I immediately rejected, some made it to the second round. YMMV.

Here's the summary, some details below.

| Software | Verdict | Easy to set up | Client can't touch backups | Linux client (x86 + ARM) | CLI | GUI | Incremental / snapshot backups | Include/exclude config |
|---|---|---|---|---|---|---|---|---|
| Amanda | Rejected | No - hard even by backup-software standards | Yes | Yes | Yes | only via paid Zmanda add-ons | Yes  | Harder than it should be |
| BackupPC | Rejected | Moderate | Yes | Yes (any rsync/SSH host) | Yes | Yes (web) | Yes | Harder than it should be |
| Bacula | Rejected | No - even worse than Amanda | Yes | Yes | Yes | GUI/web (Bacula Enterprise, Baculum) are add-ons | Yes | Harder than it should be |
| Borg | Maybe | Moderate | If hardened (easy process) | Yes | Yes | 3rd party | Yes | Yes |
| Custom rsync scripts | Rejected | No - every change means editing the script | If hardened (manually) | Yes (runs on anything that can run Linux) | No dedicated tools, standard Linux utilities | No | Yes | Yes |
| Duplicati | Rejected | Yes | If hardened | Yes | Yes | Yes | Yes | Yes (GUI or CLI) |
| Duplicity | Maybe | Moderate | If hardened | Yes | Yes | 3rd party | Yes | Yes |
| LuckyBackup | Rejected | Presumably moderate (it's a GUI wrapper around rsync), but unmaintained for years | No | Mainly x86 desktop Linux; ARM packaging unlikely given it's unmaintained | No | Yes | Yes | Yes |
| restic | Maybe | Moderate | If hardened  | Yes | Yes | 3rd party | Yes | Yes |
| UrBackup | Maybe | Yes | Yes | Yes  | Yes (client) / no (server) | Yes (web)  | Yes | Harder than it should be |

### Amanda
rejected

Fails on the "easy to set up" point, so I only did a very casual check for the rest of the points. It's a really old system, dating to the early 1990s. Designed with tape backups in mind, later expanded to back up to hard drives or even cloud services, e.g. S3. It has a lot of features that are usually found only in commercial products - it can back up several different DBs, can authenticate using various enterprise services, can control tape libraries. Combine age with lots of features and you'll get something that's really difficult to set up.

### BackupPC
rejected

It's an unusual solution since it reverses a common pattern. Most network backup applications have a client software that connects to a server process, some only have a client that copies files to a remote share. BackupPC only has a server daemon, which connects to the clients using common protocols such as rsync, SFTP, FTP or SMB. How does it do on my feature list?

- Ransomware protection - good. If a laptop gets encrypted, BackupPC might copy the useless encrypted data, but it will just waste some space, older unencrypted data will still be available.
- Server is written in Perl, it can run on Linux, any Unix system made in the current century, probably Windows with some effort. I generally don't touch Perl code with a 3.05m pole (we've got a metric system), but a config file with some Perl-style variables is acceptable.
- Linux (or any Unix) client is a first class citizen with rsync over SSH, all standard filesystem features are supported.
- Windows clients are a bit of a pain, either you need to share a directory (with every new version Windows gets stricter with security, which is generally a good thing, until your SMB share suddenly fails) or install some Unix-style software.
- You need to configure the server to find and recognise the clients on the LAN (it can deal with dynamic IPs though) by changing a configuration file.
- Everything else, including per-client configuration such as which files to back up, is also configured in the config file.
- There's a web GUI and a CLI for browsing/restoring files.
- Deduplication, supposedly very effective.
- No special support for open files.
- No support for image backups.

BackupPC would be a terrible option for an enterprise. You need to configure each client to accept incoming connections with enough access rights to read all files, without being prompted for passwords. That means using SSH keys for SSH-based protocols, storing unencrypted passwords for FTP/SMB; plus some careful configuration on the client side in all cases.

Can you do it securely? Taking into account that a laptop might also connect to other, untrusted networks? Maybe, on a small scale and if you control all the devices. For anything larger than a home network, I'd rather have a single point - the backup server - that needs to be kept secure, and most of the client devices should have all their ports closed and filtered. Even just adding/removing new devices and configuring custom exclude lists in one place would be a pain. For home, especially a geeky home where Linux machines outnumber Windows systems, it might be acceptable. But the alternatives seemed better.

### Bacula
rejected

Similar to Amanda, slightly more modern (created in 2000). Complex solution for large deployments, not really suitable for home.

### Borg
maybe

Borg can be used to back up some files to another directory on the same system (e.g. an external hard drive or a mounted network share). But it can also talk to a Borg process on another machine using SSH (there's no separate client and server package, it's the same binary run with different parameters). You don't even need to run a daemon, just create a user account and configure SSH (in ~/.ssh/authorized_keys) to run borg instead of a full-featured shell. Linux clients are fully supported, for Windows some bending over backwards is required. There are no official GUIs (there are 3rd party packages), but the CLI makes it easy to restore a specific version. Borg can also be used in the reversed way, like BackupPC, where the server pulls data from the client. The Borg project puts a strong emphasis on security, e.g. backups are properly encrypted, and on the efficient use of space and bandwidth, with deduplication and compression.

Since the client needs to connect to the server using SSH, ransomware protection depends on configuration, but Borg makes it easy to harden the setup. You can use a special account only for backups, with limited rights so it can only run borg, and set the repository in append-only mode so backups can't be deleted.

Maintaining a multi-machine setup is a bit tedious. For every client you need to generate an SSH keypair, create a script that runs borg, create an excludes list, add a crontab entry... On the plus side, it can be automated, there are Ansible playbooks (community, not official). And there's a Debian package. In general, Borg seems to be halfway between a typical self-contained backup software and hacking your own solution with common utilities such as tar or rsync.

### Custom rsync scripts for snapshot-style backups
rejected

What I have in mind is a script that runs on a client and copies files to a server using rsync over SSH, using hardlinks so that each backup looks complete, but unchanged files are only stored once. I used such scripts in the past, they work well, but these days there are better ways. This solution doesn't scale well, but might work for a small environment.

- Ransomware protection - see the note about SSH access.
- Linux client - sure, all features would work.
- Windows client - you'd need to install some Linux-style software. Doable, but a pain.
- Since you don't need any special binaries, it works with x86, ARM and anything else that can run Linux (or even another unix-like system). Big plus.
- Support for open files - possible, if you script it yourself (e.g. with LVM or btrfs snapshots), most people wouldn't bother. 
- No GUI or even CLI for restore, you'd need to copy files with standard utilities such as SFTP. But, since any incremental backup looks like a full one, it's easy to find files.
- Every new machine, every change in the backup set, every new feature you'd like - require customising the script. 

### Duplicati
Rejected

Duplicati has no server component. It can back up files to a locally attached drive (e.g. USB disk), cloud service or a network drive using several common protocols (SMB, SFTP, FTP and a few others). The usual caveat about ransomware protection applies. Since cloud is the usual target, files are properly encrypted by default. Backups are incremental with supposedly strong deduplication WITHIN ONE MACHINE. Duplicati specifically warns not to back up multiple computers to one location, so if you want to save space when backing up many similar machines, look somewhere else.

A nice thing about Duplicati is that it gives choice. There's a daemon with a web GUI, it allows you to configure the whole backup process, browse backups and will even run its own scheduler. Or you can use CLI tools for configuration and restore, run backups with cron, save some RAM and CPU cycles. Or anything in between.

Duplicati works well with both Linux and Windows. It's heavier on resource usage than traditional Unix tools - it's written in C# (on Linux you'll need to install Mono, it's available for all common CPU architectures, check if you're running something exotic) and keeps a small DB on the client. Not an issue for my laptop or any other modern computers. But I didn't feel like installing Mono just for one tool, given there were lighter alternatives.

### Duplicity
maybe

Despite the near-identical name, Duplicity is a different, older project, and reportedly one of the influences behind Duplicati's design. The core idea is similar: an initial full backup followed by incremental diffs computed with the same rsync algorithm, encrypted with GPG rather than Duplicati's own built-in AES. The differences compared to Duplicati:

- CLI only, no GUI and no built-in scheduler.
- Python-based rather than Mono/.NET - no special requirements on most Linux systems.
- The full+incremental chain needs periodic re-basing (a fresh full backup) to keep restores fast and avoid an ever-growing chain of diffs. Duplicati's local database and block-level deduplication sidestep that specific issue, though at the cost of Duplicati's own history of database-corruption complaints.

Backend support (SFTP, S3-compatible, WebDAV, various cloud providers) is similar to Duplicati.

If the daemon/GUI/scheduler is what you like about Duplicati, Duplicity won't win you over. If you'd rather have a lighter, cron-driven tool with no background service, it might be worth a look - I haven't run it myself, so take this as "worth investigating" rather than a recommendation.

### LuckyBackup
rejected

GUI only, not actively maintained. I stumbled upon it when researching, but rejected quickly without fully checking.

### restic
maybe

A bit similar to Borg: deduplicated and encrypted snapshots, single static binary. But it doesn't need its own binary on the other end. It can back up files to many storage types: local directory (e.g. USB drive or a mounted network share), SFTP, S3 (or compatible) and a few other cloud or self-hosted services. Or restic's own REST server.

Ransomware protection depends on the chosen storage medium and configuration. For SFTP, that's a bit of manual work, the REST server has a built-in *--append-only* mode enforced on the server side. It supports deduplication, unchanged data across runs (and across similar machines, unlike Duplicati) is stored once - big plus if you back up many similar machines (I don't).

Official binaries cover Linux on both x86 and ARM. There are 3rd party GUIs, and the official CLI client is comprehensive and easy to use.

### UrBackup
maybe

That was a strong contender. The list of features is impressive and very close to my needs:

- It can do both image backup and incremental file backups, with deduplication across machines.
- Server and client for Linux, Windows and a few others.
- It properly backs up open files.
- There's a convenient web GUI.
- It provides a bootable USB image for bare metal restore.
- Debian package available for server.

Downsides:
- Server configuration is all done via web UI, with no easy way to automate.
- Some features only work if the server stores files on ZFS.
- Include/exclude list with glob patterns, powerful, but error prone.
- No Debian package for the client.

## Summary

I ended up installing and trying two products: UrBackup and Borg. Neither filled all of my required points - especially around the ease of use and automation. Perfect backup software simply doesn't exist.

Borg, Duplicity and restic have similar features. I read the docs and had the slight preference for Borg. UrBackup has a different philosophy - GUI driven, with more control on the server side. I wanted to check which approach works better for me.

In the end, Borg won. But it was a matter of taste, not features.
