---
title: "Ollama: running a local LLM"
date: 2026-07-25T09:00:00
draft: true
tags: ["ai"]
---

Parts [1](/homelab/gpu-guide-1/) and [2](/homelab/gpu-guide-2/) were about buying the card and getting the driver, Secure Boot and the Container Toolkit sorted. With all of that in place, the obvious first thing to actually run on it is a local LLM.

## Why bother, on 6GB

An RTX 3050 with 6GB of VRAM is not a serious AI card. It won't run anything close to the models people are impressed by, and it won't be fast even at the models it can run. There's nothing practical here - no task I'm doing faster or cheaper than just using a hosted model.

The point is learning: how the software stack fits together, what quantisation actually buys you, what "offloading to CPU" looks like in practice when a model doesn't quite fit. All of that is visible on a small card in a way it might not be on something big enough to just brute-force past the awkward cases.

## GGUF and quantisation

Two terms come up constantly once you start looking at local models, and both are worth understanding before picking software: GGUF and quantisation.

Models are trained and originally published at FP16 or BF16 - the formats from [part 1](/homelab/gpu-guide-1/)'s floating point table - because that precision is what training stability needs. At that precision, a 7-billion-parameter model needs roughly 14GB just for the weights: 2 bytes per parameter. Nowhere near fitting in 6GB.

**Quantisation** is reducing that precision after training, storing each weight in fewer bits. Common levels are Q8, Q6, Q5, Q4 and Q2 - roughly that many bits per weight, though the "K-quants" most people actually use (`Q4_K_M`, `Q5_K_S`, and similar) mix bit-depths across a model's layers rather than using one flat width throughout, and the `S`/`M`/`L` suffix is a size/quality tradeoff within that same nominal bit count. As a rough rule of thumb, size in GB works out to roughly parameters (billions) × bits ÷ 8 - a 7B model at Q4 lands around 4-4.5GB, comfortably inside 6GB where the FP16 original wasn't. The cost is some accuracy lost in the rounding, though Q4-and-above is generally considered close enough to the original for most everyday use.

**GGUF** is the file format all of this ships in - one file per quantised model, bundling the weights alongside the tokeniser and metadata needed to run it, rather than the multi-file layout typical of a model straight off Hugging Face. It's the successor to an earlier format called GGML, and it's what both llama.cpp and Ollama consume directly.

Put together: GGUF is the container, quantisation is what makes the thing inside it small enough to matter here. Without it, none of what follows would fit on this card at all.

## Software choices: why Ollama

There are several ways to get a model running locally:

- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** - the engine most of the others are built on. Runs GGUF-format quantised models directly, no Python runtime needed. Most control, most manual work - picking the right build flags, the right quantisation, wiring up a server yourself.
- **[Ollama](https://ollama.com/)** - a wrapper around llama.cpp that turns it into something with a package manager: `ollama pull <model>`, `ollama run <model>`, a REST API on top. Most of llama.cpp's capability, much less of the manual setup.
- **[text-generation-webui](https://github.com/oobabooga/text-generation-webui)** (oobabooga) and **[LM Studio](https://lmstudio.ai/)** - GUI-first tools, built around someone sitting at the machine's own desktop. Less of a fit for a headless server reached over SSH.
- **[vLLM](https://github.com/vllm-project/vllm)** - built for throughput: serving many concurrent requests efficiently across one or more datacentre-class GPUs. Solving a problem I don't have, on hardware I don't have.

Given everything else on my servers already runs in [Docker](/home/docker/) and gets talked to over an API rather than a local GUI, Ollama was the obvious fit. It also does one thing that mattered a lot for a 6GB card: it inspects the GPU's free VRAM and decides how many of the model's layers to offload there, running the rest on the CPU, instead of just failing to load or leaving that decision to me.

## Installing

Ollama ships an official Docker image with GPU support, so it slots straight into what part 2 already set up:

```bash
docker run -d --restart unless-stopped \
  --gpus=all \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama
```

`-v ollama:/root/.ollama` keeps downloaded models in a named volume rather than inside the container, so they survive an image update. A quick check that it's alive:

```bash
curl localhost:11434
```

which should just reply `Ollama is running`.

## Configuring

Most of the useful configuration is environment variables, set with `-e` on the `docker run` above (or in a compose file):

- **`OLLAMA_MODELS`** - where models are stored, if the default volume location isn't where I want it.
- **`OLLAMA_KEEP_ALIVE`** - how long a model stays loaded in VRAM after the last request before it's unloaded. Default is 5 minutes; with only 6GB to go round, I lowered mine so an idle model isn't sitting on GPU memory the rest of the system might want.
- **`OLLAMA_MAX_LOADED_MODELS`** - how many models can be resident at once. On this card, that's staying at 1 - there isn't room for a second.
- **`OLLAMA_NUM_PARALLEL`** - concurrent requests handled per model. Left at the default; concurrency isn't the constraint here, VRAM is.

The other bit of "configuring" is per-model, via a `Modelfile` - Ollama's equivalent of a Dockerfile. It lets me set a system prompt, sampling parameters, or the context window size (`PARAMETER num_ctx`) for a model, then build it as a named variant:

```
FROM llama3.2
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
SYSTEM You are a concise assistant. Prefer short answers.
```

```bash
ollama create my-llama -f Modelfile
```

Context length is worth calling out specifically on a small card: it's not free, the KV cache for a longer context takes VRAM away from the model weights themselves. A bigger `num_ctx` than needed is one of the easier ways to push a model that fit into one that doesn't.

## Using it

Model choice is where the 6GB limit actually bites. Quantised (GGUF, mostly Q4) 7-8B models are roughly the ceiling - a bit under 5GB for the weights, leaving a little for context and the rest of the system. Smaller ones fit far more comfortably:

```bash
ollama pull llama3.2       # 3B, fits easily
ollama pull qwen2.5:7b     # closer to the limit
ollama run llama3.2
```

`ollama run` drops into an interactive prompt, fine for poking at a model by hand. The more useful interface, for anything scripted, is the REST API it's already serving on port 11434:

```bash
curl localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Explain what CUDA is in one sentence.",
  "stream": false
}'
```

While a request is running, `nvidia-smi` from [part 2](/homelab/gpu-guide-2/) shows exactly what's landing on the card - utilisation jumping up, VRAM climbing as the model loads, and (on a model that doesn't fully fit) noticeably lower utilisation than a model that does, the CPU-offloaded layers being the slow part.

A proper chat frontend - [Open WebUI](https://github.com/open-webui/open-webui) talks to Ollama's API directly and is itself just another Docker container - is the obvious next step, but that's for another post.
