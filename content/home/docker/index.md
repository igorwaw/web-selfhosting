---
title: "Docker: the container engine"
date: 2026-07-20T09:00:00
tags: ["services"]
---

A general-purpose self-hosting server ends up running a pile of unrelated services. Even worse if it doubles as a homelab - I want to experiment with new software and be able to clean up afterwards. For software that comes as an apt package it's doable, for something you install manually (perhaps with the infamous "curl | sudo bash") it will become a mess.

Containers solve that: each service gets its own image with everything it needs, isolated from the others. Of course, now you have an extra layer to manage, but it's a good tradeoff.

## Docker vs other container engines

Docker isn't the only container engine, and I already wrote a whole post on
[switching from Docker to Podman](https://random.too-many-machines.com/posts/from-docker-to-podman/) for one of my other servers. Short version of that post: whenever there's a choice between convenience and security, Docker defaults to convenience and Podman to security. Most of the manuals and tutorials assume you use Docker, for Podman you often need to adjust the configs and commands.

For a server I use at my job I want the extra security, even if it means spending a few more minutes setting things up. For a home server sitting behind my router, convenience wins.

## Installing Docker with Ansible

As usual, the whole thing is one Ansible task file:

```yaml
---
- name: Add docker apt repo
  ansible.builtin.deb822_repository:
    name: docker
    types: deb
    uris: https://download.docker.com/linux/debian
    suites: "{{ ansible_distribution_release }}"
    components: stable
    signed_by: https://download.docker.com/linux/debian/gpg
    state: present
    install_python_debian: true

- name: Remove standalone docker-compose package (conflicts with docker-compose-plugin)
  ansible.builtin.apt:
    name: docker-compose
    state: absent

- name: Install docker packages
  ansible.builtin.apt:
    name: ['docker-ce', 'docker-ce-cli', 'containerd.io', 'python3-docker', 'docker-compose-plugin']
    state: present
    update_cache: true
```

Nothing surprising here: add Docker's own apt repo (Debian's own docker.io package tends to lag behind), and install the engine plus the Compose plugin. One gotcha I hit: on an old installation (server that started as Debian Bullseye and got updated to Bookworm first and to Trixie next) there was a standalone `docker-compose` package (the Python-based v1) which conflicts with the new `docker-compose-plugin`. It needs to be removed first, or the install fails.

## Moving the data root before it's too late

By default Docker stores everything - images, containers, volumes, build cache - under `/var/lib/docker`, which on this server is a small SSD used for the system only. That's fine while I'm only running a couple of lightweight containers, but I'm about to install something a lot bigger and more disk-hungry, and I'd rather move the data root to the large HDD before I fill up the space.

```yaml
- name: Check whether new docker data-root already exists
  ansible.builtin.stat:
    path: "{{ docker_data_root }}"
  register: docker_data_root_stat
  when: docker_data_root != '/var/lib/docker'

- name: Move docker data-root to {{ docker_data_root }}
  when:
    - docker_data_root != '/var/lib/docker'
    - not docker_data_root_stat.stat.exists
  block:
    - name: Get IDs of currently running containers
      ansible.builtin.command: docker ps -q
      register: docker_running_containers
      changed_when: false

    - name: Stop docker stack to safely move its data
      ansible.builtin.service:
        name: "{{ item }}"
        state: stopped
      loop:
        - docker.socket
        - docker
        - containerd

    - name: Create new docker data-root directory
      ansible.builtin.file:
        path: "{{ docker_data_root }}"
        state: directory
        owner: root
        group: root
        mode: '0711'

    - name: Copy existing docker data to new data-root
      ansible.builtin.command: "rsync -a /var/lib/docker/ {{ docker_data_root }}/"
      changed_when: true

    - name: Configure docker data-root
      ansible.builtin.template:
        src: daemon.json.j2
        dest: /etc/docker/daemon.json
        mode: '0644'

    - name: Start docker with new data-root
      ansible.builtin.service:
        name: docker
        state: started

    - name: Restart containers that were running before the move
      ansible.builtin.command: "docker start {{ item }}"
      loop: "{{ docker_running_containers.stdout_lines }}"

- name: Add user to docker group
  ansible.builtin.user:
    name: "{{ create_user }}"
    state: present
    groups: docker
    append: true

- name: Start docker
  ansible.builtin.service:
    name: docker
    state: started
    enabled: true
```

The `docker_data_root_stat` check makes the whole block idempotent - if the target directory already exists, I assume the move already happened and skip it, rather than re-running rsync and restarting containers on every playbook run.

The move itself is straightforward but has to happen in the right order: note down which containers are currently running (so I can start the same ones back up afterwards - `docker start` doesn't touch anything that wasn't already running), stop `docker.socket`, `docker` and `containerd` so nothing writes to the data directory mid-copy, rsync the old data
across, then point Docker at the new location. That last part is a one-line `daemon.json` template:

```json
{
  "data-root": "{{ docker_data_root }}"
}
```

My role defaults to the standard location (/var/lib/docker) and only for this specific server overwrites it with /data/noshare/docker. The old data under /var/lib/docker is left in place - I'll clean it up by hand once I've confirmed everything still works after the move.

## Quick reference

**Containers**

- `docker ps` / `docker ps -a` - list running / all containers
- `docker logs -f <container>` - follow a container's logs
- `docker exec -it <container> bash` - get a shell inside a running container
- `docker start` / `docker stop` / `docker restart <container>` - control a container's state
- `docker rm <container>` - remove a stopped container

**Images**

- `docker images` - list downloaded images
- `docker pull <image>` - fetch (or update) an image without running it
- `docker build -t <name> .` - build an image from a Dockerfile in the current directory
- `docker rmi <image>` - remove an image

**Compose**

- `docker compose up -d` - start everything defined in docker-compose.yml, detached
- `docker compose down` - stop and remove a project's containers and networks (not volumes)
- `docker compose logs -f` - follow logs for the whole project
- `docker compose ps` - list containers belonging to a project

**Reclaiming space**

- `docker system df` - see how much space images, containers, volumes and build cache are using
- `docker system prune` - remove stopped containers, unused networks, dangling images and build cache
- `docker system prune -a` - also remove any image not currently used by a container
- `docker volume prune` - remove volumes not used by any container

**Inspecting**

- `docker inspect <container>` - full JSON config and state of a container or image
- `docker stats` - live CPU, memory and network usage per container
