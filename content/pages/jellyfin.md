Title: Jellyfin, a streaming server for home
Date: 2023-04-14 17:40
Status: published
Tags: services

We made a lot of hard work in the previous steps, time for relax. My NAS holds, in addition to other things, a small collection
of videos. Mostly some old movies and  TV shows not available in streaming services or my favourites that I want to keep no
matter what. The PCs can easily play video files from an SMB share using VLC or another player, but mobile devices, smart TVs
etc. need streaming. Plus, commercial streaming services made us used to features like easy searching, categories, recommendations,
resuming on another device. Fortunately it's easy to run your own streaming server.

There are two main contenders in this field in addition to a plethora of less popular solutions. **Plex** is a well-established
one with a 15 years of history. Recently many users are annoyed by the GUI changes, mostly done to promote *Plex Pass*, an optional
subscription service extending features of Plex. **Jellyfin** is a fully open-source alternative that doesn't include any
subscriptions or outside components, it's fully self contained. It has fewer plugins and clients than it's main competitor, but
it's growing rapidly and already supports most platforms.

Jellyfin has a client-server srchitecture, meaning you install server software that reads your media files and streams them to
the clients, and client software on the devices you want to use for viewing. There are clients for Android, iOS, popular smart TVs
and digital media players, there's also a web client. Installing a client is a completely no thrill experience, just install it
from an app store, open it and it will automatically detect the server on the LAN.

## Installing the server

There are several ways to install Jellyfin server, I chose the simplest for my setup: run it in a Docker container on my NAS.
That way, Jellyfin doesn't need to access media files using network, I can bind mount media directories inside the container.
I used an image from <https://docs.linuxserver.io/images/docker-jellyfin> and a very simple Ansible role.

Here is the task:

```yaml
- name: Create directory for docker-compose.yml
  ansible.builtin.file:
    path: "/home/{{ create_user }}/compose"
    state: directory
    owner: "{{ create_user }}"


- name: copy docker-compose.yml
  ansible.builtin.copy:
    src: files/docker-compose.yml
    dest: "/home/{{ create_user }}/compose/docker-compose.yml"
    owner: "{{ create_user }}"


- name: start containers
  community.docker.docker_compose:
    project_src: "/home/{{ create_user }}/compose/"
    state: present
  register: result

- name: print compose output
  ansible.builtin.debug:
    var: result
    verbosity: 2

```

And  the main part is a Docker Compose file:

```yaml
version: '3.5'
services:
  jellyfin:
	image: lscr.io/linuxserver/jellyfin:latest
	container_name: jellyfin
	environment:
	  - PUID=1001
	  - PGID=1002
	  - TZ=Europe/London
	network_mode: 'host'
	volumes:
	  - /data/noshare/jellyfin/config:/config
	  - /data/noshare/jellyfin/cache:/cache
	  - /data/filmy:/media1:ro
	  - /data/video2:/media2:ro
	  - /data/seriale1:/media3:ro
	  - /data/seriale2:/media4:ro
	restart: 'unless-stopped'
```

And that's it. The things that need customization are:

- PUID and PGID - the user and group that owns the media files,
- TZ is my timezone
- Volumes: first two are for config and cache. I have a hard drive mounted at /data/noshare which, as the name suggests, is not shared by NAS. The rest are media directories, the same ones I also share using SMB. Naming here can be anything you want, in the hindsight I should have used something more descriptive than media1, media2 etc. but it's not a big deal.


## Configuring Jellyfin server

Point your browser to port 8096 of your server, in my case it's <http://firefly.home.arpa:8096> and go through the settings. First you need to create admin account. Next important thing is to add media sources, it's not enough to make the volumes available to the container. It it recommended that a media source contains movies, TV shows, music etc. but not a mixture of different media types. Note that media sources in the Jellyfin GUI don't need to be the same as volumes in the container:

- you can have one volume split into multiple data sources, eg. a volume called /videos containing directories /vidoes/movies and /videos/shows
- or the other way around, you can have volumes /movies1 and /movies2 combined into one data source.

There are some options specifying how should Jellyfin check for changes, where to get metadata etc. - usually you can leave the defaults. Scanning the data source will take between few minutes and few hours but the media will start appearing immediately.

In the beggining I wrote that Jellyfin doesn't need online services. Well, it was a small lie. When it detects new contents, it will download metadata such as cover image, movie descripton, actor list etc. It's optional, but on by default and uses free data sources.

## More configuration

You can create multiple user accounts. They can have limited access to the data sources, eg. child account might only have access to child-friendly shows (or vice versa, adult account without access to cartoons).

Transcoding options have a huge impact on CPU usage. First, use hardware accelaration if possible. This setting is available on the server. See Jellyfin manual for details, unfortunately my hardware doesn't support acceleration so I  can't speak from experience. I also have rather weak CPU. More than adequate for all other purposes, in fact it rarely goes above 1% usage, but sometimes too slow for transcoding. If you find yourself in my place, you need to tune the transcoding settings on each client (not the server):

- on Android, choose "integrated player" instead of "web player"  in "client settings" - it supports more codecs, meaning it will do more processing on the client instead of the server
- in "Playback", choose option to prefer fMPG Media Container - again, it means more direct playback, less transcoding.
