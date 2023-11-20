Title: IDrive, backup to the cloud
Date: 2023-11-20 17:40
Status: published
Tags: backup

That is against the spirit of selfhosting, but keeping data safe is more important keeping purity. Your computers can backup to your NAS (I'll cover that in the next step), that protects you from disk failure, ransomware, accidental deletion and losing your laptop on a train. But a fire or flood can destroy both at the same moment. A proper disaster recovery plan requires 3 copies of data: 1 working copy, 1 on-site backup for quick restore and 1 off-site backup if the previous backup fails. One option is to find another self-hoster and arrange for mutual backup to each other's NAS, another is to use cloud service.

## Cloud storage choices

Popular options include Google Drive, Microsoft OneDrive and Dropbox. They are convenient for sharing files, but you can also use them for backup. That is, if the space is large enough for you (you can buy more, but it will cost you) and you trust that your files will be private enough for your needs (best way - encrypt them before sending).

Another way is to use an object storage such as Amazon S3, Google Cloud Storage, Azure Blob Storage or many S3-compatible offerings. Some providers have a special tier called cold storage. It's much cheaper then the standard tier, but be careful: you also pay for data retrieval. For an archive or backup that you'll probably never need, this might not be a big issue. A big advantage of such service is that you can use any backup tool that works with cloud storage (Duplicati, Restic and many others).

## IDrive

Probably the cheapest way to store several TB of data at a time of writing this (November 2023) is IDrive. Their personal plan starts from $99 per year for 5TB, $149 for 10TB, but you can find some affiliate links with special offer: $4 for the first year. I got mine at <https://www.tomsguide.com/reviews/idrive-cloud-storage-review>. 

Downside of IDrive: this service doesn't provide S3-compatible API, REST interface or any other standard way that's supported by various backup programs. You have to use their own client. In case of Linux, it's a set of scripts. They have limited functionality compared to a Windows version. There's also no way of automating installation and configuration. Good sides? It's cheap, it's reasonably fast, it offers pretty good security (2FA, encrypted storage and transfer), and it works.

Sending or receiving terabytes of data takes days, even on a fast broadband. IDrive gives an option of using USB drive for a restore or for initial backup. I haven't used this option, so I can't rate it.

## Getting started

Sign up for an account. It's also wise to turn on 2FA, preferably with an TOTP app. Now, the Windows and Mac clients are available for download, but for the Linux scripts you need to contact support. I'm not sure why, do they need to enable any special options for the account? Anyway, I asked on the live chat and got a download URL in 2 minutes. Beware of IDrive scripts you can find on the internet - I found some, they were so old they failed to connect - and even failed to auto-update.

Following the documentation at <https://www.idrive.com/readme> I unpacked the client to the directory of my choice. I used /opt and ran the client as root. If you don't need to backup files belonging to different users, you can use a standard account. After unpacking you need to make the scripts executable: `chmod a+x *.pl`.

First script to run is `account_setting.pl`. It detected some missing dependencies, tried to install them - some with apt, some using Perl CPAN - and failed. I ran the script again and chose not to install dependencies, but list them instead. I tried manual installation to see what was wrong. The first Perl module tried to create directory in /usr/local/man, but on my system it wasn't a directory, but a dead symlink. I fixed it, tried automatic installation again - it worked. I then logged in to my account and answered a few questions - default choice should work most of the time.

## First backup

Next script to run is `edit_supported_files.pl`. It is used for editing backup sets, exclude lists etc. I chose a reasonably sized directory (few GB) for a first test and added more directories later.

Manual backup is started with `Backup_Script.pl`. Remember to run it under cron or tmux if you expect your job to run longer then a few minutes. It shows progress, has an option to pause/resume backup and to set bandwidth limit.

Make sure you can restore your data. You can use `Restore_Script.pl` on your Linux machine or the web interface.

Last thing to do is to run `scheduler.pl` to schedule automatic backup. Choose your frequency (hourly/daily/weekly) and time to start. Once the scheduled job starts, you can watch its progress and pause/resume/throttle using `status_retrieval.pl`.

![IDrive web UI]({static}/images/idrive.png)