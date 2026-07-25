---
title: "Stable Diffusion: image generation on a 6GB card"
date: 2026-07-25T13:00:00
draft: true
tags: ["ai"]
---

After [text generation](/homelab/gpu-guide-3/) and [transcription](/homelab/whisper/), the third obvious thing to try is the other direction: turning text into an image. Diffusion models work nothing like an LLM under the hood, which was reason enough on its own to give this a go.

## How this differs from the LLM posts

An LLM predicts the next token, one at a time. A diffusion model starts from pure noise and repeatedly denoises it, guided by the prompt, over some number of steps - 20 to 50 is typical - until an image falls out the other end. There's no equivalent of GGUF quantisation carrying over directly, but the same underlying pressure applies: the base model is a few GB of weights, and VRAM is what limits resolution and batch size rather than context length.

SD1.5, the older and smaller family, fits on 6GB without any fuss. SDXL - bigger, generally better output - is tighter, though far from impossible with the right settings, covered below.

## Software choice

[AUTOMATIC1111's stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) is the closest thing to Ollama's role here: a wrapper that turns "downloading a checkpoint and writing a Python script" into a web UI and a `pip install`. [ComfyUI](https://github.com/comfyanonymous/ComfyUI) is the other big option, node-based and more flexible, more the tool for someone building a specific repeatable pipeline rather than poking around. A1111 was the better starting point for exploring what this even does before building anything more deliberate.

Unlike Ollama, there's no official Docker image from the project itself, but [AbdBarho/stable-diffusion-webui-docker](https://github.com/AbdBarho/stable-diffusion-webui-docker) packages it well enough that it fits the same Docker-first approach as the rest of this series.

## Installing

```bash
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui-docker
cd stable-diffusion-webui-docker
docker compose --profile auto up --build
```

First run downloads a default SD1.5 checkpoint and builds the image, which takes a while. After that, the UI is on `localhost:7860`.

## Configuring for 6GB

A few flags matter more here than anywhere else in this series, because SDXL genuinely doesn't fit at full precision on this card without them:

- **`--medvram`** - keeps only the model component currently in use on the GPU, moving the rest to system RAM between steps. Slower, but the difference between SDXL running and SDXL not running at all.
- **`--xformers`** - enables memory-efficient attention, cutting VRAM use during generation with close to no quality cost. About as close to a free win as any flag here gets.
- **Precision** - fp16 by default, which is already the right call; there's no reason to go back to fp32 on a card this size.

For SDXL specifically, the more reliable path was skipping the flags-and-hope approach and using **SDXL-Turbo** or an **LCM** variant instead - distilled versions of SDXL built to produce a usable image in 4-8 steps instead of 20-50. Lower quality ceiling than full SDXL, but it's the difference between a few seconds and running out of memory.

## Using it

Text-to-image, from the UI: a prompt, an optional negative prompt (what to steer away from - extra fingers, warped text, the usual list), a step count, and a CFG scale (how strictly the model follows the prompt versus wandering). SD1.5 at 512x512, 20 steps, lands in a handful of seconds on this card. SDXL-Turbo at its native few-step setting is comparable; full SDXL at 50 steps is minutes, not seconds.

`nvidia-smi` during a generation looks different from an LLM's steady trickle - GPU utilisation spikes hard for the duration of each step then briefly dips between them, one burst per denoising step rather than one continuous stream of tokens.

Same conclusion as the rest of this series: enough VRAM to see how the pieces fit and get a genuinely fun result out of it, not enough to run the largest models at their intended settings.
