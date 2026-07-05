Title: UrBackup, local backup
Date: 2024-11-24 17:40
Status: draft
Tags: backup

In the previous step, I configured my NAS to backup files to iDrive. Now I'll configure my computers to backup to the NAS, and include the location in the iDrive backup. How many copies of data will I get?

- For files stored on the NAS only: local copy (on either RAID1 or Snapraid) on the NAS and iDrive - I think that counts for 2.5 copies
- For files on other computers: local copy, potentially a copy on my other computer, potentially a cloud copy (e.g. on GitHub), backup on the NAS (on RAID1) and backup of the backup on the iDrive - that would be 3.5 copies or more

## Why UrBackup

All backup solutions are horrible, but each one in a different way. UrBackup is no exception. Try to think and write down which features of the backup software are the most important for you and I dare you to find an app that fulfils more than half. 

## Getting started


After the installation, point your web browser to http://name.or.ip.of.your.server:55414/ and accept the insecure connection (UrBackup doesn't natively support HTTPS, but you can follow the step in the documentation to put it behind a web server doing TLS termination - I don't mind it on the home LAN). First check the backup storage path - better do it now before running a first job. The documentation recommends that the location:

- is easily extendable: check, it's on LVM and I even have some unallocated space on the VG
- on a filesystem that can be compressed (btrfs or ZFS)
- preferably ZFS, as the software can use some of its advanced features for deduplication

Tough luck, I've got a boring old ext4. Maybe in future. 

The next important step is to create a user with administrator rights - from then on, you'll be prompted for a password to the web interface. The account is called "admin" by default, but you can name it anything you like.