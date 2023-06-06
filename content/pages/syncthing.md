Title: Syncthing, synchronizing files between the devices
Date: 2023-05-10 17:40
Status: published
Tags: services

Sharing files between your devices using a cloud service such as Google Drive or Dropbox is incredibly convenient.
Wouldn't it be nice to do the same locally, with complete privacy and without using your internet connection? Sure it would.

**Syncthing** works on Linux, Windows, MacOS, FreeBSD and Android. There are also packages for commercial NASes from Synology,
QNAP, WD and others. It doesn't require a server - you can directly sync two computers, or computer with a phone,
or 3 devices can all sync with each other. That's what I did before I got the NAS. But if you have a home server which is
always on, it makes sense to treat it as a central point and have all other devices synchronize with it.

## Installation

On my Linux laptops and desktop, I just installed the package and set syncthing to autostart using my
user account (no need to run it as root and a dedicated account wouldn't have access to my files):

```bash
apt install syncthing
systemctl enable syncthing@igor
systemctl start syncthing@igor
```

On the NAS, it was similar, but I used Ansible. This is the task file I added to the *firefly* role:

```yaml
---
- name: Install syncthing
  apt: 
    name: ['syncthing'] 
    state: present

- name: Create directory for syncthing
  ansible.builtin.file:
    path: /data/noshare/syncthing
    state: directory
    owner: igor

- name: Restart syncthing
  service:
    name: syncthing@igor
    state: restarted
    enabled: true
```

I could run syncthing in a Docker container, but I don't see much value in it. It's just one package,
data is all contained in one place and an up to date package is widely available for Linux distros.

On Windows I installed SyncTrayzor package, which includes SyncThing and a system tray widget. Finally,
on Adroid it's just installing the package from either Play Store or F-Droid.

## Configuration

Syncthing isn't really well suited for automated configuration. It stores its settings in ~/.config/syncthing/config.xml
You could generate this file if you really wanted to, but more sane option is to configure using the web GUI and then
backup this file so you can recreate the setup if needed. For configuring your computer, just point your browser to
<http://localhost:8384>.

It's a bit more tricky with the NAS. By default, syncthing only listens on the local interface. You can change this
option in your config file or, since it's only needed for a moment and the default is better for security, you can
setup an SSH tunnel. On my laptop, I typed `ssh -L 8385:localhost:8384 firefly` and pointed the browser to <http://localhost:8385>.
How does the tunnel work? It means that ssh will forward local port 8385 through firefly to localhost:8384 - but that's localhost
from the firefly's point of view. Note that I can open the tunnel *through* firefly *to* another server, sysadmins often use this
technique to connect to servers using on IPs through one jumphost available on the internet.

Back to the point. In one of your browser tabs, click "Add Folder" and choose what you want to share. In my case, I'm sharing
~/CloudStation between all my computers. The folder name is due to historical reasons, few years ago I used Synology CloudStation
for the same purpose. Don't share your whole home directory as some config file are system-specific.

Next, click "Add Remote Device". You can than paste the ID of your another device (or scan the QR code) or very likely, you'll
see a list of other devices on the network. Remember to type a name that will be displayed in the GUI instead of the ID. Then,
on your other machines, confirm you want to pair with this device. A moment later you'll see a message: this device wants to
share a folder. Click to confirm. Note that the path of the shared folder doesn't need to be the same, on my computers I use
~/CloudStation, but on the NAS I chose /data/noshare/syncthing/CloudStation.

## Syncing the phone

There are some things I like to sync between my computers - code snippets, financial stuff, home related documents - that I
would never access on the phone. I decided to share only a subset of files, inside my ~/CloudStation folder, I have 
~/CloudStation/na-telefon (which translates as "to the phone"). Syncthing warns that one shared folder is contained
within the other, but allows such setup.

One other use for syncthing is to **auto upload my photos** from my phone to Elsa, my graphics workstation. On the 
phone, I chose to sync the camera folder with Elsa, but there's one twist: the synchronization is only in one
direction. Phone will send files, I can view them on the computer and delete those I don't need, the changes won't be
synced back. 

## Dealing with conflicts

Most of the time, nothing will stop you from modifying the same file on multiple devices at once. Some applications
create lock files, those warn about opening the same file more than once and often suggest to open it read-only.
Depending on your workflow, this might be a huge problem ("I'm getting conflicts all the time"), none at all
("I'm always editing this file on this computer anyway, others only read it") or something in between.

When you do get a conflict, syncthing will keep both versions of the file, adding "syncconflict" plus timestamp
and device ID. It is then up to you - and your applications - to resolve it. For example, Keepassxc will merge
two DBs without any issues, text files (source code etc.) can be compared with diff, vimdiff or similar tools.