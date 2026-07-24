---
title: "Minikube: Kubernetes for learning and experiments"
date: 2026-07-22T09:30:00
tags: ["services"]
image: minikube.png
---

Kubernetes (or K8s if you don't want to type so much) is a system for running containers across a fleet of machines. It decides which node runs what, manages network connections, restarts things that crash, scales services up and down, rolls out updates without downtime. In short, a great tool for running hundreds or thousands of containers. Designed by Google, popular for large-scale cloud deployments.

## Why bother at home

I believe K8s has no practical purpose on a home server. My "fleet" is one or two boxes, there's no node to fail over to, no scaling problem to solve. For actually running services at home, plain Docker (or Docker Compose) is a much better fit.

But I want to experiment with Kubernetes, because I use it for my job, and the only way to really learn it is to break it a few times. The alternative would be paying for a managed cluster, all cloud providers (Amazon, Microsoft, Google and others) have this service. Which works, and for a short experiment it doesn't cost much (sometimes there are even free tiers), but I'm a self-hoster for a reason.

## Choosing Kubernetes distribution

Kubernetes consists of several components that communicate over TLS. You can install all of them manually, generate certificates, configure everything - a famous [Kubernetes The Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way) describes that.

The first time I used Kubernetes was soon after the project was first announced. I worked for IBM, supporting several customers and one of them wanted to try it. At that time, that guide didn't exist, and I ended up installing Kubernetes The Even Harder Way.

Today, it's different. Several Kubernetes distributions (k3s, kubeadm, RKE2, MicroK8s, and others) simplify the bootstrapping process, on VMs or on bare metal. It still isn't exactly easy. And I'm not the first person who wants a small experimental K8s. That's precisely why **Minikube** was created: it's a single-node Kubernetes cluster that runs entirely on one machine and can be created in a few minutes with one command.

## Installing Minikube

Minikube isn't packaged for Debian. Kubectl (the Kubernetes client) is, but it's an outdated version, so I got an official binary. As usual, I used an Ansible role:

```yaml
---
- name: Install minikube prerequisites
  ansible.builtin.apt:
    name: conntrack
    state: present

- name: Get latest stable kubectl version
  ansible.builtin.uri:
    url: https://dl.k8s.io/release/stable.txt
    return_content: true
  register: kubectl_stable_version

- name: Install kubectl
  ansible.builtin.get_url:
    url: "https://dl.k8s.io/release/{{ kubectl_stable_version.content | trim }}/bin/linux/{{ minikube_arch }}/kubectl"
    dest: /usr/local/bin/kubectl
    mode: '0755'

- name: Install minikube
  ansible.builtin.get_url:
    url: "https://storage.googleapis.com/minikube/releases/latest/minikube-linux-{{ minikube_arch }}"
    dest: /usr/local/bin/minikube
    mode: '0755'
```

`minikube_arch` is a role default (`amd64`), there to be overridden if I ever run anything on ARM.

## Starting Minikube

Minikube can run its single node using several drivers - directly on the host (messy), inside a VM (VirtualBox, KVM), inside a Docker container and a few more. Since I already have Docker installed and configured on this server, the Docker driver is the obvious choice. The "node" is just another container, so the stuff installed on K8s doesn't spill all over the server.

```bash
minikube start --driver=docker
```

This is, incidentally, the "something big" I moved Docker's data root to the large HDD for in the previous post - not Minikube itself (it's a few GB), but the stuff I intend to run on it. 

```bash
minikube status
kubectl get nodes
```

## The dashboard

And, if you want a GUI to click around in rather than typing `kubectl` for everything:

```bash
minikube addons enable dashboard
minikube dashboard
```

Firefly runs headless, and `minikube dashboard` proxies through `kubectl proxy`, which only binds to `127.0.0.1`. There are two ways to connect from my laptop: either expose the whole K8s API (not just the dashboard) to the local network, or use SSH tunnelling. Exposing an experimental cluster with no important services to a trusted network wouldn't be a big deal, but let's do it properly. First, I run this command to get the port number - it changes every time.

```bash
minikube dashboard --url
```

This prints something like `http://127.0.0.1:<port>/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/`. That path matters - `kubectl proxy` serves the whole Kubernetes API at the root, and the dashboard only lives at that specific sub-path, so browsing to just the tunnelled port gets you raw API output instead.

```bash
ssh -L 8001:127.0.0.1:<port> firefly
```

Then I browse to `http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/` - same path as above, just with my tunnel's local port instead.

## Reclaiming disk space

The whole point of Minikube, for me, is experimenting with different things that might fail, or that I might abandon halfway through. All of it leaves behind container images and build cache, and it adds up fast.

If deleting pods and volumes from within Minikube isn't enough, or an experiment leaves the cluster in a broken state, there's a nuclear option:

```bash
minikube delete
minikube start --driver=docker
```

`minikube delete` throws away the whole node and starting again gives me a clean slate in a few minutes. For something that only exists to be experimented on, that's usually faster than trying to fix it.

## GPU passthrough

Before Minikube can hand the GPU to the node at all, you need the NVIDIA driver and the Container Toolkit. I covered that in the GPU guide.

After that, start Minikube with the GPU(s) attached:

```bash
minikube start --driver=docker --container-runtime=docker --gpus=all
```

You need all these flags here (see Minikube's [own guide on using NVIDIA GPUs](https://minikube.sigs.k8s.io/docs/tutorials/nvidia/) for the full set of prerequisites):
- *--gpus=all* attaches the devices to the outer container - the one in which the K8s cluster is running
- *--container-runtime=docker* switches K8s from the default runtime (Containerd) to Docker. GPUs can only be used with the Docker runtime.

Being attached to the node container isn't enough for Kubernetes to schedule anything onto it - kubelet needs a device plugin to report the GPU as an allocatable resource. It's as simple as turning on one add-on:

```bash
minikube addons enable nvidia-device-plugin
```

That deploys NVIDIA's device-plugin DaemonSet, which exposes *nvidia.com/gpu* as a resource pods can request:

```bash
kubectl describe node | grep -A5 Allocatable
```

It should list *nvidia.com/gpu: 1* alongside CPU and memory. From there, a pod requests it the same way as any other resource limit. The easiest way to check if it works is to run `nvidia-smi` inside a pod.
