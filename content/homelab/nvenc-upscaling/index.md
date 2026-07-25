---
title: "NVENC and Real-ESRGAN: video encoding and AI upscaling"
date: 2026-07-25T14:00:00
draft: true
tags: ["ai"]
---

[Part 1](/homelab/gpu-guide-1/)'s shopping list mentioned hardware video encode/decode as a reason to want a GPU at all, for transcoding on [Jellyfin](/home/jellyfin/). Worth separating that out from the neural-network experiments elsewhere in this series, because it isn't one - and worth pairing it with something that is: using the same card to upscale video with an actual AI model, for the contrast.

## Two different things on the same card

**NVENC/NVDEC** are dedicated hardware blocks on the GPU die for encoding and decoding video - H.264, HEVC, AV1 depending on the card's generation. Not CUDA cores, not AI, just fixed-function silicon built for one job. Fast, low power, and it runs alongside whatever else is using the CUDA cores, because it isn't competing for them.

**Real-ESRGAN** is a proper neural network, trained to upscale an image - or a video, frame by frame - while inventing plausible detail rather than just interpolating pixels. This one does run on the CUDA cores, and it's slow, in the way everything else in this series involving an actual model has been slow.

Worth trying both back to back, if only to feel how differently "GPU-accelerated" can mean two things.

## NVENC: transcoding with ffmpeg

The Container Toolkit setup from [part 2](/homelab/gpu-guide-2/) already covers what a container needs to see the GPU at all, so this is just ffmpeg with the right encoder selected:

```bash
docker run --rm --gpus all -v $(pwd):/data jrottenberg/ffmpeg:6-nvidia \
  -i /data/input.mkv \
  -c:v h264_nvenc -preset p5 -cq 23 \
  -c:a copy \
  /data/output.mp4
```

`-c:v h264_nvenc` is the switch that matters - everything else is a normal ffmpeg encode. `-preset p5` trades a bit of compression efficiency for speed; NVENC's presets run p1 (fastest) to p7 (slowest, best compression), a different scale from libx264's `veryfast`-to-`veryslow` naming but the same idea. On this card, a 1080p transcode runs several times faster than realtime - which is the entire point when Jellyfin needs to transcode a stream for a client that can't play the source format directly.

`nvidia-smi dmon` shows encoder/decoder utilisation as separate columns from GPU utilisation - worth checking once, to see that a transcode barely moves the general utilisation figure while the encoder column sits near 100%, confirmation it's genuinely using the dedicated block rather than falling back to software encoding.

## Real-ESRGAN: AI upscaling

```bash
pip install realesrgan
```

Real-ESRGAN ships a few pretrained models - a general-purpose one, and `realesr-animevideov3`, tuned specifically for animation, where the usual photographic-detail assumptions don't hold as well.

```bash
realesrgan-ncnn-vulkan -i frame.png -o frame_upscaled.png -n realesrgan-x4plus
```

(The `ncnn-vulkan` build is worth knowing about specifically because it's not CUDA-locked - it runs through Vulkan instead, so the same binary works on AMD or Intel GPUs, unlike almost everything else this series has covered.)

For video rather than a single image, the practical approach is ffmpeg extracting frames, Real-ESRGAN upscaling each one, then ffmpeg re-encoding the result - and this is where the gap from NVENC really shows. Upscaling a frame at a time, at 4x, took multiple seconds per frame on this card. A short clip is a real wait; a full episode is not something to start and expect to check back on the same evening.

## The contrast, in one line

NVENC transcoding is the closest thing in this whole series to "genuinely production-ready on a budget card" - fast, low overhead, exactly why it was worth having a GPU for Jellyfin in the first place. Real-ESRGAN is back in familiar territory for this series: works, is legitimately impressive when it's done, and is not something to plan around finishing quickly on 6GB.
