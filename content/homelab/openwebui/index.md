---
title: "Open WebUI: chat frontend for Ollama"
date: 2026-07-25T11:00:00
draft: true
tags: ["ai", "services"]
---

[Part 3](/homelab/gpu-guide-3/) got Ollama running and talking to it with `curl`. That's fine for checking the API works, but not how I actually want to sit down and use a model. [Open WebUI](https://github.com/open-webui/open-webui) is the missing piece: a proper chat interface, self-hosted, running as just another container next to Ollama.

## Why a frontend at all

`ollama run` gives an interactive prompt, and that's enough for a quick test. It's not enough for actual use: no chat history, no way to switch models mid-conversation without restarting, nothing to point a second machine on the home network at without SSHing in first. Open WebUI covers all of that - it's a normal web app, reached from any browser on the network, backed by Ollama's API rather than replacing it.

## Installing

Open WebUI ships its own Docker image, and expects to reach Ollama over the network rather than a GPU of its own - it's a plain frontend, all the GPU work still happens in the Ollama container from [part 3](/homelab/gpu-guide-3/).

Putting both containers on the same user-defined network lets them address each other by container name instead of hardcoding an IP:

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

`-v open-webui:/app/backend/data` is where chat history, accounts and settings live - worth keeping in a named volume for the same reason as Ollama's model volume in part 3: it should survive an image update. Once it's up, `http://<server>:3000` in a browser gets a setup screen asking to create the first account.

## Configuring

The first account created is the admin account - after that, `WEBUI_AUTH=false` can be set to skip login entirely (fine for a single-user box on the home network, less fine for anything more shared), or left as-is and additional accounts created from the admin panel, each with their own chat history.

A few other settings worth knowing about, all reachable from the admin panel rather than needing a container restart:

- **Which models are visible** - anything already pulled with `ollama pull` shows up automatically, but individual models can be hidden from the picker if there's no reason to offer them.
- **Default model and system prompt** - set once instead of typing the same instruction into every new chat.
- **Per-model parameters** - context length, temperature and similar, the same things a [Modelfile](/homelab/gpu-guide-3/) sets, but adjustable per-conversation from the UI instead of baked into a build.

## Using it

Day to day, this is just a chat window: pick a model from the dropdown, type, get streamed tokens back the same as any hosted chat product. A few things stood out as different from that, worth a mention:

- **Model switching mid-chat** works, but on a 6GB card it's not free - swapping models means Ollama unloading one and loading the next, a multi-second pause rather than an instant switch, same VRAM constraint as [part 3](/homelab/gpu-guide-3/) discussed.
- **Document upload / RAG** - Open WebUI can chunk and embed a document, then pull relevant pieces into a chat automatically. Works, but needs an embedding model loaded alongside the chat model, which on this card means even less room for either. Something to come back to once there's a better GPU, not a 6GB workflow.
- **It's still just hitting the same API** - anything done through the UI, `curl` from part 3 can still do directly. The UI is convenience, not a different underlying system.

That's as far as this GPU takes the local LLM experiment for now - 6GB is enough to see how the pieces fit together, not enough to forget the constraint it started with.
