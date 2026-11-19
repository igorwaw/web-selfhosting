---
title: "Self-hosted coding agent, part 2: in practice"
date: 2026-11-12T00:00:00
draft: true
tags: ["ai", "gpu"]
---

In [part 1](/homelab/coding-agent-1/) I went through the options and made the choices. Now it's time to put it all together and see whether it can do any useful work.

## Dress rehearsal on Serenity

The L40S costs $3.54 per hour, and the meter runs from the moment the VM starts - including the time I spend reading error messages, fixing typos in config files and waiting for Docker images to download. From the [vLLM](/homelab/vllm/) and [TensorRT-LLM](/homelab/tensorrt-llm/) posts I know that the first run of anything rarely works. So before starting the expensive machine, I ran the whole stack on Serenity first.

It won't be practical. The RTX 3050 has 6GB of VRAM, so the model has to be tiny, and as I mentioned in part 1, tiny models are useless for agentic coding. But that's not the point. The goal is to get every command and config file right, so that on the VM it's just copy, paste and wait for the download.

The stack is the same as on the VM, all on one machine:

- **vLLM** in Docker, serving the model on port 8000.
- **SearXNG** in Docker, on port 8888.
- **mcp-searxng** - the adapter between Pi and SearXNG. Pi starts it on its own when it needs it.
- **Pi** itself, running directly on the host.

### Choosing a tiny model

I wanted a model as close to the real one as possible. Qwen3.6 only comes in 27B and 35B-A3B sizes, but the previous generation, Qwen3.5, has small siblings: 0.8B, 2B, 4B and 9B. Same family means the same chat template, the same tool-call parser (`qwen3_coder`) and the same reasoning parser (`qwen3`). If those work with Pi at home, they will work with Qwen3.6 on the VM.

I went with **Qwen3.5-0.8B**. The bigger ones would need 4-bit quantisation to fit in 6GB with vLLM's overhead, and there are no official 4-bit builds of the small Qwen3.5 models - only community ones. The 0.8B version runs in the original BF16 precision, at about 1.8GB of weights, and leaves plenty of room for the KV cache. The RTX 3050 doesn't support FP8 anyway, so there's no way to test the quantisation I'm going to use on the VM.

<!-- TODO: did 0.8B manage a single tool call? If it's too dumb to call even one tool, try a community AWQ build of Qwen3.5-4B -->

### vLLM and SearXNG

Both services in one Docker Compose file - the same file will go to the VM, with only the model lines changed.

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    restart: unless-stopped
    runtime: nvidia
    ipc: host
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - hf-cache:/root/.cache/huggingface
    command:
      - --model=Qwen/Qwen3.5-0.8B
      - --served-model-name=qwen3.5-0.8b
      - --language-model-only
      - --gpu-memory-utilization=0.85
      - --max-model-len=32768
      - --max-num-seqs=2
      - --enable-auto-tool-choice
      - --tool-call-parser=qwen3_coder
      - --reasoning-parser=qwen3

  searxng:
    image: docker.io/searxng/searxng:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:8888:8080"
    volumes:
      - ./searxng/config:/etc/searxng
      - ./searxng/data:/var/cache/searxng

volumes:
  hf-cache:
```

Most of the vLLM parameters are explained in the [vLLM post](/homelab/vllm/). New ones:

- `--language-model-only` - Qwen3.5 and Qwen3.6 models have a vision encoder. I'm not going to send them images, so there's no point wasting VRAM on it.
- `--tool-call-parser=qwen3_coder` - as I wrote in part 1, the wrong parser doesn't fail loudly. The model answers in prose and the agent waits forever for a tool call. This is the one recommended in vLLM's recipes for both Qwen3.5 and Qwen3.6.
- `--reasoning-parser=qwen3` - Qwen models think before answering. The parser moves the thinking into a separate field of the response, so the harness can show it (or hide it) instead of treating it as part of the answer.
- `--max-model-len=32768` - the bare minimum for a coding agent, as I wrote in part 1. Pi's system prompt and tool definitions alone take a few thousand tokens.
- `--max-num-seqs=2` - one user, one agent. No need to reserve memory for more.
- Both ports are bound to `127.0.0.1`. Neither vLLM nor SearXNG has any real authentication, and everything that talks to them runs on the same machine.

<!-- TODO: does 32K fit on the 3050? vLLM prints the KV cache size at startup - add the number -->

SearXNG has one problem out of the box: the JSON API, which is all the agent needs, is disabled. It has to be enabled in `searxng/config/settings.yml`:

```yaml
use_default_settings: true

server:
  secret_key: "change-me"
  limiter: false

search:
  formats:
    - html
    - json
```

- `use_default_settings: true` - takes all the defaults and only overrides what's listed below. Without it, I'd have to copy the whole (very long) default config.
- `secret_key` - SearXNG refuses to start with the default one. `openssl rand -hex 32` generates a good one.
- `limiter: false` - the limiter is a bot protection for public instances. Here, the only "user" is a bot, and it's my own.

Start both and check that they respond:

```bash
docker compose up -d
curl -s localhost:8000/v1/models
curl -s 'localhost:8888/search?q=vllm&format=json' | head -c 500
```

If SearXNG returns `403 Forbidden`, the JSON format is not enabled.

<!-- TODO: startup time of vLLM on Serenity (image was cached from earlier posts?) -->

### Testing tool calling without the agent

Before adding Pi to the mix, I checked that vLLM really returns tool calls, not prose. A single request with one fake tool:

```bash
curl -s localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen3.5-0.8b",
    "messages": [{"role": "user", "content": "What is the weather in London?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "parameters": {
          "type": "object",
          "properties": {"city": {"type": "string"}},
          "required": ["city"]
        }
      }
    }]
  }' | jq '.choices[0].message'
```

The answer should have a `tool_calls` array with `get_weather` and `{"city": "London"}`, and an empty `content`. If the call is inside `content` as text, the parser is wrong.

<!-- TODO: paste the actual response; reasoning field visible? -->

### Pi

Pi installs with a script or from npm:

```bash
curl -fsSL https://pi.dev/install.sh | sh
# or
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

<!-- TODO: which one did I use, Node version on Serenity -->

Pi keeps its configuration in `~/.pi/agent/`. Three files there are relevant.

**`models.json`** - tells Pi where the model is. vLLM speaks the OpenAI Chat Completions API, which Pi supports out of the box:

```json
{
  "providers": {
    "vllm": {
      "baseUrl": "http://localhost:8000/v1",
      "api": "openai-completions",
      "apiKey": "none",
      "models": [
        { "id": "qwen3.5-0.8b" }
      ]
    }
  }
}
```

The `id` has to match `--served-model-name` from the compose file. The API key is a dummy - vLLM doesn't check it, but Pi only shows models from providers that have one.

**`mcp.json`** - the web search. mcp-searxng can run with `npx` (Node.js 22 or newer) or in Docker. I chose Docker, so I don't need to care about the Node version on the host:

```json
{
  "mcpServers": {
    "searxng": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--network", "host",
               "-e", "SEARXNG_URL", "isokoliuk/mcp-searxng:latest"],
      "env": { "SEARXNG_URL": "http://localhost:8888" }
    }
  }
}
```

`--network host` is needed because SearXNG listens on the host's `127.0.0.1`, which is not reachable from a container on the default Docker network.

`pi mcp list` connects to all configured servers and prints their tools - a quick way to check it works without starting a session. mcp-searxng has four: `searxng_web_search`, `web_url_read`, `searxng_search_suggestions` and `searxng_instance_info`.

<!-- TODO: output of pi mcp list -->

**`extensions/`** - the permission gate. As I wrote in part 1, Pi runs every command without asking. On a disposable VM I can live with that, but Serenity is a real machine with real data. The example extension from the Pi repository asks for confirmation before `rm -rf`, `sudo` and `chmod 777`:

```bash
mkdir -p ~/.pi/agent/extensions
curl -fsSL -o ~/.pi/agent/extensions/permission-gate.ts \
  https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/examples/extensions/permission-gate.ts
```

It's a guardrail against accidents, not a security boundary. For the rehearsal I also ran Pi in a fresh test directory, with no git credentials or API keys in the environment.

<!-- TODO: does Pi auto-load from ~/.pi/agent/extensions/ or does it need the "extensions" setting / -e flag? -->

Finally, start it with the model selected:

```bash
mkdir -p ~/pi-test && cd ~/pi-test
pi --model vllm/qwen3.5-0.8b
```

<!-- TODO: first task on Serenity - e.g. "write a bash script that..." + web search test. Did it call tools at all? -->
<!-- TODO: what broke during the rehearsal and what I fixed - this is the useful part -->
<!-- TODO: list of files to copy to the VM: docker-compose.yml, searxng/config/settings.yml, ~/.pi/agent/{models.json,mcp.json,extensions/} -->

## On the rented GPU

<!-- TODO: Lightning AI setup - GPU type and price, SSH access (link to /homelab/vllm/ for the basics) -->
<!-- TODO: vLLM - model, FP8, context length, tool-call parser and reasoning parser, MTP speculative decoding -->
<!-- TODO: from the abandoned draft: prefix caching (the whole conversation is resent each turn), wrong parser fails silently -->
<!-- TODO: SearXNG in Docker + mcp-searxng, connected to Pi -->
<!-- TODO: Pi - provider config for vLLM, permission-gate extension, narrowly scoped git token -->
<!-- TODO: vLLM + harness on the same VM - the GPU box is the sandbox -->
<!-- TODO: a real coding task, results, speed, cost per session -->
<!-- TODO: conclusion -->
