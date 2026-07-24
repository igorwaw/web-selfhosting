---
title: "Wazuh, part 2: installing and configuring"
date: 2026-07-13T17:45:00
draft: true
tags: ["security"]
---

In [part 1](/homelab/wazuh-1/) I explained what Wazuh is and admitted it's overkill for a home network. Here's how I actually set it up on Firefly, my NAS.

## Installation choices

Wazuh can be deployed as a single all-in-one server or split into separate manager, indexer and dashboard nodes - the distributed setup is for when you have enough agents that one box can't keep up. I have a handful of machines at home, so that's not my problem. Single server it is.

The official docs push you towards the Docker/Kubernetes route. I went with the native packages instead, from Wazuh's own apt repository. Fewer moving parts, one less thing to keep updated, and it fits the rest of the NAS setup (everything else there is either apt or a plain systemd service).

## Disk layout

`/var/ossec` is where the manager keeps its data - the indexer's data, in particular, is not small and grows continuously. Firefly's data disks are already encrypted and only unlocked manually after boot (see [part 5 of the storage series](/home/nas-5/)), and I wanted the same for Wazuh's data instead of leaving it on the unencrypted system disk.

So, before installing anything, I created a dedicated btrfs subvolume on the encrypted RAID1 pool:

```bash
mount /dev/mapper/luks-btrfs1 /mnt/btrfs-root
btrfs subvolume create /mnt/btrfs-root/wazuh
umount /mnt/btrfs-root
mkdir -p /var/ossec
mount -o subvol=wazuh,nodatacow /dev/mapper/luks-btrfs1 /var/ossec
```

`nodatacow` because copy-on-write and a database-heavy workload like the indexer don't mix well - same reasoning I'd use for a VM image or a database data directory.

This subvolume isn't available until the pool is unlocked, same as `/data/other` and `/data/noshare`, so the fstab entry is `noauto,nofail` again, and I added it to the same `BTRFS_SUBVOLUMES` array in `unlock-mount.sh`:

```bash
BTRFS_SUBVOLUMES=(
  "othervol:/data/other"
  "noshare:/data/noshare"
  "wazuh:/var/ossec"
)
```

Which meant Wazuh itself couldn't be started at boot either - its systemd services went in `SYSTEMD_SERVICES` alongside Grafana and Jellyfin, started only after the unlock script mounts everything:

```bash
SYSTEMD_SERVICES=(
  "syncthing@igor.service"
  "smbd.service"
  "wazuh-manager.service"
  "wazuh-indexer.service"
  "wazuh-dashboard.service"
)
```

Installed with the services disabled from autostart, same as I did for the other dependent services when I migrated the storage:

```bash
systemctl disable wazuh-manager wazuh-indexer wazuh-dashboard
```

## Cutting down the noise

Default rule set is chatty. Before adding agents I spent a while in `/var/ossec/etc/rules/local_rules.xml` raising the level of low-value rules I didn't care about (repeated cron logs, routine sudo use from my own account) to a level below my alert threshold, rather than disabling them outright - I'd rather have them in the log for correlation later than lose them entirely.

Disk usage is the other side of the same coin. Alert retention and the indexer's own indices can quietly eat the subvolume I just created. I set a shorter retention on `alerts.log` rotation and lowered the indexer's index retention policy - default assumes a fleet of servers with a security team to review it, not one NAS.

## Adding agents

For Linux, I wrote an Ansible role - registration and agent install are both a handful of tasks, and I already have Ansible everywhere:

```yaml
- name: Install Wazuh agent
  ansible.builtin.apt:
    name: wazuh-agent
    state: present
  environment:
    WAZUH_MANAGER: "firefly.home.arpa"

- name: Enable and start the agent
  ansible.builtin.systemd:
    name: wazuh-agent
    enabled: true
    state: started
```

Windows machines got the agent installed by hand - only two of them, not worth the Ansible/WinRM setup for that.

## Network devices

My router and switch can't run an agent, but they can send syslog, so that's how they get into Wazuh - pointed them at Firefly's IP on UDP 514, and added a `<remote>` block of type `syslog` to `ossec.conf` on the manager side. Doesn't give the depth an agent would (no file integrity monitoring, no process list, just whatever the device chooses to log), but it's enough to see authentication attempts and configuration changes on the one box that everything else depends on.
