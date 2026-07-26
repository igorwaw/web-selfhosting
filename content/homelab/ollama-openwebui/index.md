---
title: "Ollama plus Open WebUI: running a local LLM"
date: 2026-07-25T09:00:00
draft: true
tags: ["ai"]
---

Now that I have a GPU, it's time for experiments. The obvious first thing is to run a local LLM.

## What's possible on my hardware

The impressive models powering ChatGPT or Claude require several hundred GB of VRAM. My GPU has 6GB. There are some ways to reduce hardware requirements, but even with them I won't be able to host anything practical (for a chatbot or agent, that is - there are other uses). High-end consumer GPUs can run a limited model that serves a real purpose, but my card is far from high-end. I expect my chat to be slow - few tokens per second - and prone to hallucinations. In a few moments, I'll see if I'm right.

The point is learning: how the software stack fits together, how reducing the hardware requirements affects the model's output. Making the model work acceptably on a limited hardware is actually a useful skill.

## Where to get models

The best current models are tightly kept secrets, but companies decide to publish some of their work as **open weight**. That is the equivalent of Open Source in the ML world (though the analogy isn't perfect: the training data and code behind a model like Llama or Qwen usually isn't published, only the result of training it).

**[Hugging Face](https://huggingface.co/)** is a hosting platform for machine learning models (and datasets), the closest thing this space has to a package registry. You can browse the models from the web interface and download them directly, if your software doesn't have it in its own repository.

There are several file formats for publishing models, the most popular is **GGUF**. It's a convenient package: one file per quantised model, storing the weights together with the tokeniser, neural network structure and metadata. The full layout is documented in the [GGUF spec](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md).

![GGUF file structure: header, metadata key-value pairs, tensor info, then tensor data](gguf-structure.png)

*Diagram by [@mishig25](https://github.com/mishig25), from the GGUF spec (MIT-licensed).*



## Reducing hardware requirements

### Quantisation

Models are trained and originally published at FP16 or BF16 - the formats from [part 1](/homelab/gpu-guide-1/)'s floating point table - because that precision is what training stability needs. That means 16 bits, or 2 bytes, per parameter.

**Quantisation** is reducing that precision after training, storing each weight in fewer bits. Common levels are Q8, Q6, Q5, Q4 and Q2 - that many bits per weight. Though the "K-quants" most people use (*Q4_K_M*, *Q5_K_S*, etc.) mix bit-depths across a model's layers rather than using one flat width throughout, and the S/M/L suffix is a size/quality tradeoff within that same nominal bit count. Confused? Don't worry about that, just experiment.

As a rough rule of thumb, size in GB is **parameters (billions) × bits ÷ 8**. A 7B model at BF16 needs 14GB just for the weights, reduced to Q4 is about 3.5GB. Small enough for my 6GB card - I need to leave some space for context and other purposes.

### Distillation

The largest models available on Hugging Face - e.g. DeepSeek-V4 - are well over 1T parameters. The same creators publish much smaller models. **Distillation** means a "student" model is trained to mimic a larger "teacher" model's outputs, rather than being trained from scratch on raw data alone. The idea being that the teacher's outputs already encode a lot of what's worth learning, so the student converges on more capability per parameter than an equivalently-sized model trained the usual way.

### Tradeoffs

The two techniques work together: distillation shrinks the parameter count, quantisation shrinks the bits used to store each parameter. But there's a cost.

Smaller and less stable models are more prone to hallucinations than LLMs you know from publicly available chats. Not only do they fabricate facts, they often include words from other languages in their output or drift completely off topic.

Some models are trained for a specific task, rather than being universal. For example, Polish model [Bielik](https://bielik.ai/) is mostly trained on Polish sources and despite small size (11B) can answer Poland-related questions correctly, but struggles on everything else.

### Using VRAM and system RAM together

A model is a stack of identical transformer layers, and there's nothing stopping different layers living in different places - llama.cpp (and Ollama on top of it) loads as many as will fit into VRAM, and puts the remainder in ordinary system RAM. But that means the parts that sit in RAM are computed on CPU, which obviously can't do massively parallel processing. Offloading even a small part of the model to RAM has a huge impact on how many tokens per second it can process. But it's the only way to load a model larger than VRAM. Iin theory, I could even load a full-blown LLM into swap space, but I wouldn't like the inference speed.

## Software stack

The most popular engine for small platforms is **[llama.cpp](https://github.com/ggml-org/llama.cpp)**. It runs GGUF models directly. It gives the most control, but requires a lot of manual work.

**[Ollama](https://ollama.com/)** is a wrapper around llama.cpp that turns it into something with a package manager: `ollama pull <model>`, `ollama run <model>`, a REST API on top. Most of llama.cpp's capability, much less of the manual setup.

**[Open WebUI](https://openwebui.com/)** is a chat frontend, that gives a nice web GUI and talks to Ollama's API.


## Ollama

### Installing Ollama 

Ollama ships an official Docker image with GPU support:

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

which should just reply *Ollama is running*.

### Configuring Ollama

Most of the useful configuration is environment variables, set with `-e` on the `docker run` above (or in a compose file):

- **`OLLAMA_MODELS`** - where models are stored, if the default volume location isn't where I want it.
- **`OLLAMA_KEEP_ALIVE`** - how long a model stays loaded in VRAM after the last request before it's unloaded. Default is 5 minutes.
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

Context length is worth setting on a small card: it's not free, the KV cache for a longer context takes VRAM away from the model weights themselves. A large num_ctx is one of the easier ways to push parts of the model from VRAM into RAM.

### Using Ollama

Model choice is where the 6GB limit matters. Quantised (GGUF, mostly Q4) 7-8B models are roughly the ceiling - a bit under 3.5-4GB for the weights, leaving a little for context and the rest of the system. Smaller ones fit far more comfortably:

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

While a request is running, `nvidia-smi` shows exactly what's landing on the card - utilisation jumping up, VRAM climbing as the model loads. If the model doesn't fully fit in VRAM, GPU utilisation is noticeably lower, when the GPU has to wait for the CPU.

## Open WebUI

### Installing Open WebUI

Open WebUI ships its own Docker image, and expects to reach Ollama over the network. It doesn't need the GPU. Putting both containers on the same user-defined network lets them address each other by container name instead of hardcoding an IP:

```bash
docker network create ollama-net

docker network connect ollama-net ollama

docker run -d --restart unless-stopped \
  --network ollama-net \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  -v open-webui:/app/backend/data \
  -p 3000:8080 \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

`-v open-webui:/app/backend/data` is where chat history, accounts and settings are stored. Remember to use the volume so you don't lose them on container restart.

### Configuring Open WebUI

Once the container is up, `http://<server>:3000` in a browser gets a setup screen asking to create the first account. It will have admin rights. After that, `WEBUI_AUTH=false` can be set to skip login entirely (fine for a single-user box on the home network), or left as-is and additional accounts created from the admin panel, each with their own chat history.

A few other settings in the admin panel:

- **Which models are visible** - anything already pulled with `ollama pull` shows up by default, you can hide some models.
- **Default model and system prompt** - set once instead of typing the same instruction into every new chat.
- **Per-model parameters** - context length, temperature and similar, the same things a Modelfile sets, but adjustable per-conversation from the UI instead of baked into a build.

### Using Open WebUI

It's just an AI chat like any other - only slower and dumber. You can pick a model from the dropdown, type, and get an answer. A few things seemed different compared to commercial products:

- **Model switching in the middle of the conversation.** It works, but on a 6GB card it means a long pause: Ollama will unload the first model and load the second one.
- **Document upload / RAG** - Open WebUI can embed a document, then pull relevant knowledge into the chat. It works, sort of, it would give excellent privacy. But it needs an embedding model in addition to the chat model. On a 6GB card, there's no room for both.
