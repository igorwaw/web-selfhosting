---
title: "GPU for CUDA experiments, part 2: driver and Docker setup"
date: 2026-07-23T09:00:00
draft: true
tags: ["hardware"]
---

In [part 1](/homelab/gpu-guide-1/) I went through what's actually worth buying for CUDA experiments, and why. Card bought, here's how I got it working: drivers, Secure Boot, and Docker.

## What this covers

Getting a GPU from "physically installed" to "usable and monitored" involves a few distinct layers, each with its own moving parts:

- **The driver** - the kernel module and userspace libraries that actually talk to the card. Nothing else here works without this in place.
- **Secure Boot signing** - not really a separate layer, more a gate the driver's kernel module has to get through, if Secure Boot is staying on.
- **The Container Toolkit and CDI** - lets containers see the GPU at all, whether that's a plain `docker run` or a nested runtime like Minikube's, rather than every process needing driver access on the host directly.
- **Monitoring** - `nvidia-smi` for a quick look, `dcgm-exporter` and Prometheus for the ongoing picture.

That's roughly the order this post goes in, bottom to top: without the driver nothing else matters, and without the Container Toolkit there's nothing for the monitoring stack to reach into.

## Installing drivers on Linux

On Debian, the proprietary driver lives in the `contrib` and `non-free-firmware` components, which aren't enabled by default:

```
deb http://deb.debian.org/debian/ trixie main contrib non-free non-free-firmware
```

After `apt update`, install the driver and firmware:

```bash
sudo apt install linux-headers-$(uname -r) build-essential dkms
sudo apt install nvidia-driver firmware-misc-nonfree
```

A reboot is needed for the kernel module to load. After that, `nvidia-smi` should show the card, its driver version, and current power/temperature - the basic sanity check that everything is talking to the hardware correctly.

## Tools that come with it

The driver package doesn't just install a kernel module - it drops a handful of command-line tools onto the system too, most of which won't get mentioned again after this section, but worth knowing they exist:

- **`nvidia-smi`** - the one used throughout this post, for the initial sanity check and later for monitoring; covered in more depth further down.
- **`nvidia-settings`** - a GUI for fan curves, overclocking, and display configuration. Built for desktop use, not much use on a headless server.
- **`nvidia-persistenced`** - a daemon that keeps the driver loaded between uses, the always-running equivalent of calling `nvidia-smi -pm 1` by hand.
- **`nvidia-modprobe`** - loads the kernel module and creates device nodes with the right permissions, mostly invoked automatically by other tools rather than run directly.
- **`nvidia-bug-report.sh`** - bundles logs and diagnostics into an archive, the thing to attach to a support request if something's misbehaving.

Worth naming here even though it comes from a separate package installed later in this post: **`nvidia-ctk`**, the Container Toolkit's own CLI, used both for wiring the GPU into Docker and for generating the CDI spec Minikube needs - both covered in their own sections below.

## Signing the driver for Secure Boot

I kept Secure Boot on - one gotcha isn't a reason to give up a real security feature - which meant sorting out the unsigned kernel module properly instead of just switching it off.

First, generate a signing key and a self-signed certificate. A hundred-year expiry is the usual convention here, since this key only needs to mean something to my own machine:

```bash
sudo mkdir -p /var/lib/dkms
cd /var/lib/dkms
sudo openssl req -new -x509 -newkey rsa:2048 -keyout mok.priv -outform DER -out mok.der -nodes -days 36500 -subj "/CN=DKMS module signing/"
```

Enrol the certificate as a Machine Owner Key. This asks for a one-time password, used only to confirm the enrollment at next boot:

```bash
sudo mokutil --import /var/lib/dkms/mok.der
```

Tell DKMS to use this key and certificate for everything it signs from now on, so future kernel or driver updates get signed automatically instead of repeating this by hand:

```bash
echo 'mok_signing_key="/var/lib/dkms/mok.priv"' | sudo tee -a /etc/dkms/framework.conf
echo 'mok_certificate="/var/lib/dkms/mok.der"' | sudo tee -a /etc/dkms/framework.conf
```

Rebooting after `mokutil --import` drops into MokManager - a plain blue-and-white screen that appears before GRUB, separate from the usual boot flow. Choosing "Enroll MOK", then "Continue", then entering the password from the previous step is what actually gets the key trusted; skipping this screen (or not noticing it flash by) means the import silently didn't happen.

After that, rebuilding the module picks up the new signing key, and `modinfo` confirms it took:

```bash
sudo dkms install nvidia/$(dkms status | grep -oP 'nvidia/\K[0-9.]+' | head -1)
modinfo -F signer nvidia
```

That last command should print the certificate's CN from the first step. If it doesn't, or `nvidia-smi` still can't find the card, `mokutil --sb-state` is the first thing to check - it's easy to enable Secure Boot in the UEFI, do all of the above, and still have it be off (or on in "Setup Mode", which doesn't enforce anything) without the key ever having mattered.

## Installing the NVIDIA Container Toolkit

Since everything on my servers runs in [Docker](/home/docker/), I want containers to be able to see the GPU rather than installing CUDA directly on the host for every experiment. That's what the NVIDIA Container Toolkit is for:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install nvidia-container-toolkit
```

Then point Docker's runtime at it and restart the daemon:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

A quick test that a container can see the card:

```bash
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu24.04 nvidia-smi
```

If that prints the same output as the host's `nvidia-smi`, containers can use the GPU, and I'm ready to actually start experimenting.

## Enabling CDI mode

Docker's `--gpus` flag above is a Docker-specific mechanism - the daemon calls into the NVIDIA Container Runtime, which knows how to bind-mount the right device nodes and libraries into a container. That's fine for a plain `docker run`, but it doesn't help when the GPU needs to reach further down, into a container runtime running inside another container - which is exactly the situation with [Minikube's](/homelab/minikube/) Docker driver.

That's what CDI (Container Device Interface) is for: a vendor-neutral, CNCF-defined spec for describing a device - the device nodes, mounts, environment variables it needs - as a static file, rather than logic baked into one specific runtime. Any CDI-aware runtime (Docker, containerd, CRI-O) can read the same spec and wire the device in the same way, without needing any NVIDIA-specific knowledge of its own.

Generating the spec:

```bash
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
```

This writes a YAML file describing the GPU as one or more named devices - `nvidia.com/gpu=0`, `nvidia.com/gpu=all`, and so on. From here, anything that understands CDI can request `nvidia.com/gpu=all` and get a working GPU, whether that's a plain container or one nested inside another.

Not quite a one-off, though: the spec pins exact, version-numbered library files - `libnvidia-ml.so.535.129.03` and the like - alongside the device nodes. A driver upgrade removes and replaces those files, so a stale spec can point at libraries that no longer exist on disk. Worth rerunning this command after every driver update, as part of the same maintenance step. A Container Toolkit upgrade alone doesn't invalidate an existing spec the same way - `nvidia-ctk` is just the tool that writes the file - so it's lower-stakes, though worth regenerating too if a release specifically mentions a CDI change.

## nvidia-smi: there's more to it than the default screen

I've used `nvidia-smi` a few times above just as a sanity check, but the plain command is a summary screen, not the whole tool.

**Which process is actually using the GPU.** Below the summary table, `nvidia-smi` lists every process with a handle on the GPU and how much memory each is using - genuinely useful once more than one container might touch the card, rather than guessing which one left VRAM allocated.

**A live view instead of a snapshot.** `watch -n1 nvidia-smi`, or `nvidia-smi -l 1` for the tool's own built-in loop, refreshes the summary every second - utilisation, memory, temperature, power draw and fan speed all updating live, useful while a stress test or a training run is going.

**Why the clocks dropped, not just that they did.** `nvidia-smi -q -d CLOCK` includes a "Clocks Throttle Reasons" section with fields like `SW Thermal Slowdown` (running hot, but not dangerously) and `HW Slowdown` (the serious one - overheating, a power supply that can't keep up, or a triggered power brake). That's the direct way to check the thermal-throttling concern from [part 1](/homelab/gpu-guide-1/)'s mining section, rather than inferring it from temperature alone.

**Persistence and power limits.** `sudo nvidia-smi -pm 1` keeps the driver loaded rather than letting the GPU drop to a low-power state between requests - worth it on a headless server that runs CUDA jobs sporadically, since it removes a small delay on the first call after idle. `sudo nvidia-smi -pl <watts>` sets a power cap below the card's default, handy if a PSU is a bit short of the card's rated draw rather than replacing it outright.

**Scriptable output for actual monitoring**, rather than reading the summary screen by eye:

```bash
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit --format=csv,noheader,nounits -l 5
```

That's the same shape of data a Prometheus exporter needs, and it's enough to bolt one together by hand. NVIDIA already ships a proper one, though.

## Running dcgm-exporter in Docker

DCGM (Data Center GPU Manager) is NVIDIA's own GPU monitoring stack, and `dcgm-exporter` is its Prometheus-format wrapper. It reads the driver through the same NVML library `nvidia-smi` uses, but exposes a much wider set of fields as proper metrics - ECC errors, NVLink stats, per-process accounting - rather than something to parse out of CSV.

It runs as just another container, using the same GPU passthrough set up earlier in this post:

```bash
docker run -d --restart unless-stopped \
  --gpus all \
  --cap-add SYS_ADMIN \
  -p 9400:9400 \
  --name dcgm-exporter \
  nvcr.io/nvidia/k8s/dcgm-exporter:3.3.5-3.4.1-ubuntu22.04
```

`--cap-add SYS_ADMIN` is needed for the profiling metrics (NVLink, some utilisation counters) that DCGM reads through performance counters rather than plain NVML calls. Without it the container still starts and exports the basic fields, just with a warning in the logs about the ones it can't reach - worth knowing before spending time wondering why a field is missing.

Metrics land on `/metrics` on port 9400, in Prometheus format:

```bash
curl -s localhost:9400/metrics | grep DCGM_FI_DEV_GPU_UTIL
```

Point Prometheus at it like any other scrape target:

```yaml
scrape_configs:
  - job_name: dcgm-exporter
    static_configs:
      - targets: ["localhost:9400"]
```

From there it's the same [Prometheus and Grafana](/home/prometheus-1/) setup already watching everything else on this server - NVIDIA even publishes a ready-made Grafana dashboard (ID 12239) that plots most of the useful fields without having to build one from scratch.

## What about multi-GPU?

Everything above assumes a single card, because that's all I've got. Multiple GPUs mostly change things at the container/orchestration layer, not the driver install itself:

- Driver installation and Secure Boot signing are identical regardless of card count.
- Picking which GPU a container gets needs an extra flag - `CUDA_VISIBLE_DEVICES`, or `--gpus '"device=0,1"'` instead of this post's `--gpus all`.
- `nvidia-smi topo -m` shows whether multiple cards talk over plain PCIe or NVLink, which matters for how well multi-GPU workloads actually scale.
- The CDI spec generated earlier already lists every GPU as its own named device once there's more than one installed.
- Kubernetes' device plugin hands out whole GPUs by default; splitting one physical GPU into isolated slices (MIG) is only a thing on datacentre-class cards, not anything covered in [part 1](/homelab/gpu-guide-1/).
- Monitoring barely changes - `dcgm-exporter` already labels metrics per-GPU.


