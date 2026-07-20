---
title: "Backup, part 2: Borg, backing up to the NAS"
date: 2026-07-20T10:00:00
draft: false
tags: ["backup"]
---

In [part 1](/home/backup-choices/), I reviewed several backup solutions and hated most of them. Borg seemed to be the least repulsive; I ended up almost liking it.

## Installing and configuring with Ansible

Two Ansible roles: *borg_client* is applied to every host that needs backing up. Firefly, which is both the client and the target, only backs up /etc. My laptop backs up /etc and my home dir, with some exclusions. The role also delegates some tasks to the Borg server - mainly, creating a dedicated user account (one per each client) and the directory. Since Borg writes lots of small files, and btrfs's copy-on-write fragments badly under that pattern, the repository directory gets `chattr +C` applied before any repo is created in it. Which means btrfs will not do checksumming for that directory, but Borg already does chunk-level integrity checking.

Second role *borg_server*, applied only to firefly, doesn't actually install the server - there's no separate client and server app, the same binary does both. Instead, it configures retention (deleting old archives) and compacting the repositories.

### Locking down the server side

Each client gets its own dedicated SSH key and its own dedicated Unix account on firefly. The account's authorized_keys entry is what actually enforces append-only:

```bash
command="borg serve --restrict-to-path /data/noshare/borg/<client> --append-only",restrict
```

*--restrict-to-path* confines that key to its own client's repository and nothing else on the box; *restrict* (modern OpenSSH shorthand) turns off port/agent/X11 forwarding and PTY allocation. The account's shell is */bin/sh*, not *nologin* - that one tripped me up, since *nologin* seemed like the more locked-down choice, but sshd runs the forced *command=* through the account's configured shell, and nologin refuses to run anything at all, forced command included.

### Passphrases without leaving a trace

Passphrases live in Ansible Vault and get written once to a file readable only by root, then handed to the backup service via systemd's *LoadCredential=*, which copies them into a private, auto-cleaned runtime directory for just that one run. The script reads it with:

```bash
BORG_PASSCOMMAND="cat ${CREDENTIALS_DIRECTORY}/borg-passphrase"
```

instead of setting *BORG_PASSPHRASE* directly - Borg runs that command whenever it needs the passphrase, so the value never sits in the process environment (readable via `/proc/<pid>/environ`) or in the deployed script itself.

### Coping with a laptop that isn't always on

My laptop travels with me, so it often ends up on another network than my NAS. Rather than let every missed connection page me as a failed backup, the script sets a short connect timeout and inspects what Borg's output actually says before deciding whether to fail:

```bash
BORG_RSH="ssh -o ConnectTimeout=10 -o BatchMode=yes ..."
```

Timeout, refused, unreachable, DNS failure - logged and treated as "nothing to do this run" (exit 0). Anything else - a real auth failure, a full disk, repo corruption - still exits non-zero.

Everything is scheduled through systemd timers rather than cron, mainly for `Persistent=true` - a laptop that's asleep at 2am simply runs its backup on next wake instead of silently skipping it. Pruning runs afterwards, on firefly, well clear of any backup that might still be in progress.

The end result: every night, each machine pushes an encrypted, deduplicated, tamper-resistant backup to firefly, and I don't have to think about it again until I actually need a restore.

## What I didn't like

- My perfect backup software would have both a full-featured CLI and the GUI. I want CLI for scripting, GUI would be better for less-used operations, such as "find and compare several past versions of this file to see which one I need". There are 3rd party GUIs, I might try one some day.
- Some server-side configuration is done by the client role. I couldn't find any other sane way.
- I have to keep passwords in plain text in one file on the server. That is a tough choice. I want per-client encryption, but also the scripts running on the server need a way to access the repository for pruning and compacting (since all clients use append-only mode, they can't handle that, it has to be done server-side).

## What I liked

- Borg plays well with the way I already use my Linux machines: it uses SSH, it's scriptable, doesn't need a GUI, it can be easily configured with Ansible. I expected that since every client needs a separate user account, SSH keypair and cron/systemd jobs, adding another machine would be a long process. I admit I spent an hour or two writing the playbook. But after that, it's now dead simple: just add borg_client role to the new client's playbook, add new password to the vault, configure includes/excludes if you want to back up something more than /etc - and that's it, Ansible will do the rest.
- Borg deduplicates and compresses at the chunk level, so daily backups of mostly-unchanged data cost very little extra space. Encryption and authentication is always on - another layer of security, maybe an overkill for an encrypted NAS on a trusted LAN, but I'm getting it for free.
- The append-only mode is a killer feature. A client only gets permission to add new archives to its repository on the server, never to delete or rewrite existing ones. If a client machine is ever compromised (e.g. by ransomware), the attacker can't destroy the backups along with the live data.
