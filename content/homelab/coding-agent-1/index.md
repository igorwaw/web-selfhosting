---
title: "Self-hosted coding agent, part 1: concepts and choices"
date: 2026-11-12T00:00:00
draft: true
tags: ["ai", "gpu"]
---

## Why a self-hosted agent

There's only one reason to run an agent powered by a self-hosted model: you work with very sensitive data that can't leave company premises. It's definitely not about saving money. At current prices for tokens, and especially with fixed-price monthly subscriptions, self-hosting is more expensive, and by a large margin. A model that can do real agentic coding needs a big GPU (or at least a powerful Mac with lots of unified memory), and hardware prices are not going down any time soon. On top of that, the subscription gets you a frontier model that is noticeably better than open-weight models. If you want to check the numbers for your own hardware and usage, [Sunk Cost](https://sunkcost.ai) calculates how long a local AI machine takes to pay for itself compared to paying for an API.

It might change in the future. Open models keep getting better at smaller sizes, and subscription prices are subsidised today - they don't have to stay that way. But that's the situation as of now.

Of course, you can always experiment. I did it some time ago at work. The company owned on-prem GPUs and wanted to see whether a self-hosted coding agent was worth it. In the end they decided not to go this route - the GPUs were usually needed for something else and they would have to dedicate a significant portion of their hardware to achieve the same thing that a $20/month subscription did. I can't share details of that setup, as they are confidential, so I decided to recreate something similar as a personal experiment.

So this goes into a homelab category, though strictly speaking, it was hosted outside the home. Serenity's 6GB RTX 3050 can't run a model that is any good at this - I tried, and a 3B model can't even do a simple bash script. Previously in the [vLLM](/homelab/vllm/) and [TensorRT-LLM](/homelab/tensorrt-llm/) posts, I compared my GPU to a rented VM on Lightning AI. This time, I only used the remote VM. Yes, that defeats the privacy argument. But I'm not going to use it for real workloads, and the setup is exactly the same as it would be with on-prem hardware. And I'm certainly not buying a 48GB GPU.

## Software stack

A coding agent is two separate things glued together: the **harness** (the program in your terminal that reads files, runs commands and talks to the model) and the **model** itself. Both can be swapped independently, as long as they speak the same API.

And then, there are **add-ons**, like web search, guardrails and other things. Some harnesses have them bundled, with others you have to provide them yourself (or live without them). 

## The harness

Most popular software as of mid-November 2026. Everything in this space moves fast - expect the version numbers to be outdated by the time you read this.

### Claude Code

I use Claude Code, so I'll compare everything to it. The harness can work with a self-hosted model (or a model provided by another company), though it's rarely used this way.

**Strong points:** the most polished of the bunch. Sub-agents, plan mode, hooks, skills, MCP, permission modes, fine-grained tool approval. Huge ecosystem of plugins and guides.

**Limitations:** closed source, so only half of the stack is self-hosted. It only speaks Anthropic's Messages API. vLLM and Ollama have an Anthropic-compatible endpoint now, so it works without a translation proxy, but not every feature maps cleanly. If you use a different engine, you might need a translation proxy. The bigger problem is the size of the system prompt and tool definitions: tens of thousands of tokens before you type anything, written and tuned for Claude. A mid-size open model gets less room for your code, and more instructions it wasn't trained to follow.

### OpenAI Codex CLI

OpenAI's agent. Comes from a Big Tech company, but it is Open Source (Apache 2.0 licence).

**Strong points:** open source, fast, good sandboxing on Linux and macOS (commands run in a restricted environment by default, not just behind a "yes/no" prompt). Has a built-in `--oss` mode for local models (Ollama and LM Studio out of the box) and supports custom OpenAI-compatible providers, so vLLM works too.

**Limitations:** designed around OpenAI's models and the Responses API - the default local model is `gpt-oss`, and other model families are second-class citizens. Configuration for third-party providers changed a few times between versions, so older tutorials might not work.

### OpenCode

Open source (MIT) agent, currently version 2.2.x. TUI, desktop app and web interface.

**Strong points:** provider-agnostic from day one - any OpenAI-compatible server is a few lines in `opencode.json`. Feature-wise it's the closest to Claude Code: sub-agents, MCP, LSP integration, custom commands, context compaction. Big, active community.

**Limitations:** big and busy - new releases every few days, and recent ones focus on other features (the desktop app, GitHub Copilot and Claude integrations) rather than local models. The default system prompt and tool set are smaller than Claude Code's, but still large. Some model vendors explicitly say their model isn't supported in OpenCode (NVIDIA's Nemotron-Cascade-2, for example).

### Pi

A minimal agent by Mario Zechner (author of libGDX), MIT licence. Originally a one-person project, now under the Earendil umbrella. Version 1.0 came out on 1 October 2026, the current one is 1.5.2.

**Strong points:** small and opinionated. The core is four tools (read, write, edit, bash) and a short system prompt - around 3000-5000 tokens, depending on enabled options, a fraction of Claude Code's. Fewer and simpler tools mean fewer chances for a mid-size model to produce a malformed tool call. Everything else (MCP, sub-agents, custom tools) is an extension you can add or skip. Good support for OpenAI-compatible servers, including vLLM-specific fixes in recent releases.

**Limitations:** fewer features out of the box mean you likely need to spend more time configuring the add-ons. Probably the biggest issue is with permission prompts: none out of the box, the agent runs all commands without confirmation. They can be added with an extension: the repo has a [permission-gate.ts](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/examples/extensions/permission-gate.ts) example that asks for confirmation before dangerous commands (rm -rf, sudo and similar), and a protected-paths.ts one that blocks writes to .env or .git. But they only match the command text - they can't see what happens inside a script, so the scripts can do anything. That's a guardrail against accidents, not a security boundary. For real isolation the [docs](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/containerization.md) recommend using a container. Fine on a disposable VM, not great on your laptop. And whatever access tokens you give it (git, cloud, API keys), keep them narrowly scoped - read-only access to one repository, not your full account. Assume anything the agent can see, it can use. The "minimal" claim is also less true than it used to be - MCP support grew the prompt, although it can be turned off with `--no-mcp`.

### Qwen Code

Alibaba's fork of Google's Gemini CLI, tuned for Qwen models. Version 0.27.x, Node.js 22+.

**Strong points:** prompts and tool formats tuned for Qwen3-Coder and Qwen3.6, which are among the best open models in this size class. Very actively developed (weekly updates): sub-agents, worktree-isolated sessions, plan mode, MCP. Works with any OpenAI-compatible endpoint.

**Limitations:** optimised for one model family - it works with others, but that's not the point of it. A lot of new features revolve around Alibaba's cloud subscription and delegating work to Claude Code or Codex, not much use for a fully self-hosted setup.

### Aider

The veteran of the group, around since 2023. Apache 2.0, Python.

**Strong points:** doesn't rely on tool calling at all - the model returns edits in a text diff format, and Aider applies them. That's the most forgiving approach for weaker models, and the one most likely to work with anything. Excellent git integration (every change is a commit), and the "repo map" gives the model an overview of the codebase cheaply.

**Limitations:** it works in a different way than other agents - they call it "AI pair programming". It generates code, but it doesn't run commands and iterate on its own. Effectively in maintenance mode: latest version is 0.86.2 (February 2026), and the last feature release was in August 2025.

### Others

There are many more: **Goose** (Block, now under the Linux Foundation's Agentic AI Foundation), **Cline** and **Kilo Code** (VS Code extensions), **Mistral Vibe** (paired with Devstral models), **OpenHands** (a full platform with a web UI and Docker sandbox)..

### Summary

| Harness | Version | Licence | Talks to vLLM | Prompt overhead | Sandbox / approvals | Best for |
|---|---|---|---|---|---|---|
| Claude Code | 2.1.3xx | Proprietary | Via Anthropic-compatible endpoint | Very large | Approvals, permission modes | Claude models; reference point |
| Codex CLI | 0.162.x | Apache 2.0 | Custom provider | Medium | OS-level sandbox | gpt-oss; safety-conscious setups |
| OpenCode | 2.2.x | MIT | Native | Medium | Approvals | Claude Code experience with any model |
| Pi | 1.5.2 | MIT | Native | Small | None by default; extensions, container/VM | Mid-size models, disposable machines |
| Qwen Code | 0.27.x | Apache 2.0 | Native | Medium | Approvals, plan mode | Qwen models |
| Aider | 0.86.2 | Apache 2.0 | Native | Small (no tool calls) | Git commits as undo | Weak models; pair programming |


### My choice

I decided to experiment with Pi. It's a traditional open source project - not vibe coded, not affiliated with any provider - so I trust it a bit more. The "do the bare minimum, but do it right" approach is also close to the traditional Unix way. Lack of guardrails is a big limitation, but on the other hand - can you trust them anyway? The internet is full of stories about accidentally deleted DBs and services brought down, with agents apologising "you are completely right, you told me not to run this command but I did". 

My second choice would be OpenCode. Probably easier if you want your setup to just work.

## The model

### Hardware limitation

I decided to use a single 48GB GPU - an L40S, which costs $3.54/h on Lightning AI. I need to leave about 15GB-20GB of VRAM for the KV cache. Coding agents need a long context, 32K tokens is the bare minimum, 64-128K is comfortable.

BF16 weights would take too much space. 4-bit quantisation is sometimes not stable enough for coding, FP8 is the sweet spot (reports vary, for some tasks larger models with 4-bit weights might work better). That means I can run models of about 20B-30B parameters (up to 35B at the cost of a smaller KV cache). Models of that size are good enough for a lot of coding and document processing work.

Why didn't I use a bigger GPU? On Lightning AI an 80GB H100 costs $5.45/h, not much more. For a multi-user production setup it's the better choice - the extra memory goes to the KV cache, so several people (or several agents) can work in parallel. It also has about 4x the memory bandwidth, so it generates tokens 3-4 times faster. Alternatively, I could use the VRAM to fit a bigger model. But a 27B model should be good enough, and for the proof of concept I don't need a faster card. In my opinion, dealing with hardware limitations is a skill worth having.

### Qwen3.6-27B

Dense 27B model from Alibaba, released in April 2026, Apache 2.0. Official FP8 checkpoint, about 28GB, and vLLM lists a single 40GB GPU as the minimum. Thinking and non-thinking modes, 262K native context. Reported 77.2% on SWE-bench Verified and 59.3% on Terminal-Bench 2.0 - the best numbers in this size class.

**Where I'd use it:** the default choice when quality matters more than speed. Being dense, every token has to read all 27B parameters, so it's several times slower than the MoE models below. Multi-token prediction (MTP, a form of speculative decoding built into the model) helps a bit.

### Qwen3.6-35B-A3B

The MoE sibling: 35B parameters in total, but only 3B active per token. Same release, same licence and context length.

**Where I'd use it:** when speed matters - quick edits, lots of small tasks, interactive work. With only 3B active parameters it generates tokens much faster than the 27B. The FP8 weights take about 35GB, which leaves noticeably less room for the KV cache on a 48GB card. Community reports say it tends to get lost on longer multi-step tasks.

### Devstral Small 2

Mistral's 24B dense model built specifically for coding agents, released in December 2025, Apache 2.0 (unlike its big brother, Devstral 2 123B, which has a modified MIT licence with restrictions). 256K context, reported 68.0% on SWE-bench Verified.

**Where I'd use it:** a non-Chinese, non-thinking alternative. No reasoning phase means no waiting for the model to think before every tool call, which is nice for interactive work. The BF16 weights are exactly 48GB, so on this GPU it has to be FP8. A year old at this point, and it shows in the benchmarks.

### gpt-oss-20b

OpenAI's open model from August 2025, 21B parameters (3.6B active), Apache 2.0. Ships natively in the MXFP4 format, so the weights are only about 13GB. Reported 60.7% on SWE-bench Verified.

**Where I'd use it:** with Codex CLI, which is built around it. Tiny footprint means plenty of room for context, or for running a second model next to it. The oldest model here and with 4-bit weights, no wonder it's the weakest in benchmarks. Its bigger sibling, gpt-oss-120b, needs an 80GB card.

### Qwen3-Coder-Next (if I choose a bigger card)

80B MoE, 3B active, dedicated coding model, Apache 2.0. Probably the strongest agentic coder you can self-host without a multi-GPU server. But the FP8 version needs around 90GB, and even 4-bit AWQ is about 46GB - technically loads on 48GB, but no room left for context. It needs an 80GB card (H100 with AWQ) or bigger.

### Others

**Nemotron-Cascade-2-30B-A3B** (NVIDIA, March 2026) is strong in competitive programming benchmarks but weak in agentic ones (50.2% on SWE-bench Verified), and NVIDIA says it's meant for OpenHands, not general harnesses. **GLM-4.7-Flash** (Z.AI, 30B-A3B, MIT licence) is another MoE in the same size class worth a look.

### A note on Chinese models

American and European companies don't share their best models. Most Open Weight models come from Chinese companies (Alibaba, DeepSeek and others). Can you trust them? If you run them on your own server, they can't leak your data - a model can't make a network connection. What knowledge is stored in weights - that's a different matter. There were some well-known tests - people asked Chinese models about Tibet or Tiananmen Square and the models seemed evasive (especially when asked in Chinese).

Does it matter, if you want it to generate Python or JavaScript? Probably not. Stretching my imagination, I can think of an example (if you develop an app for learning geography, it might say Taiwan is a part of China). But for most coding tasks, it's not an issue.

### Summary

| Model | Params (active) | Licence | Released | Weights on GPU | SWE-bench Verified* | Tool-call parser (vLLM) | Use it for |
|---|---|---|---|---|---|---|---|
| Qwen3.6-27B | 27B dense | Apache 2.0 | Apr 2026 | ~28GB (FP8) | 77.2% | `qwen3_coder` | Best quality for this GPU |
| Qwen3.6-35B-A3B | 35B (3B) | Apache 2.0 | Apr 2026 | ~35GB (FP8) | 73.4% | `qwen3_coder` | Speed |
| Devstral Small 2 | 24B dense | Apache 2.0 | Dec 2025 | ~24GB (FP8) | 68.0% | `mistral` | No thinking, non-Qwen alternative |
| gpt-oss-20b | 21B (3.6B) | Apache 2.0 | Aug 2025 | ~13GB (MXFP4) | 60.7% | built-in (Harmony) | Codex CLI, long context |
| Qwen3-Coder-Next | 80B (3B) | Apache 2.0 | 2026 | ~46GB (AWQ) - doesn't fit | - | `qwen3_coder` | Best quality on an 80GB card |

\* As reported by the vendors, each with their own harness - not directly comparable.

One thing to watch out for: picking the wrong tool-call parser doesn't fail loudly. The model simply answers in prose, and the agent sits there waiting for a tool call that never comes.

### My choice

I experimented with Qwen3.6-27B. It's widely reported as the best coding model of this size.

## Web search

A model's knowledge stops at its training cutoff, months before you use it. For coding, it hurts more than you'd expect: library APIs change, new versions come out, error messages need looking up. If you want to use an agent for other tasks, such as writing texts or education, it's even more important.

Of all possible add-ons, a web search tool is the most important one. I chose **[SearXNG](https://github.com/searxng/searxng)**, an open source metasearch engine. It sends queries to Google, Bing, DuckDuckGo and others, and merges the results. It runs in a single Docker container and has a JSON API, which is all an agent needs.

The agent can't talk to SearXNG directly, so there needs to be a small adapter in between, exposing it as a tool. The standard way to do that is an **MCP server** (Model Context Protocol - a common format for giving agents extra tools). There are a lot of SearXNG MCP servers. I went with [mcp-searxng](https://github.com/ihor-sokoliuk/mcp-searxng), the most popular one, MIT licence. Besides search, it can also fetch a page and convert it to text, so the agent can actually read the documentation it finds, not just the search snippets.

A word on privacy, since that's the whole point of this exercise. SearXNG doesn't make searching private - the queries still go to Google or other providers. The queries don't carry your identity, but an agent might put a function name, an error message or a piece of your code into them. If that's a problem, leave web search out, or tell the agent (in `AGENTS.md`) to keep the queries generic.

There's also a cost on the model side: every MCP server adds its tool descriptions to the prompt. That works against the main reason for choosing a small harness. One server with two very important tools is worth it.

## What I left out

Web search is not the only thing commercial agents have and a self-hosted setup doesn't. Here's what else I considered, and why I skipped it - at least for now.

- **Up-to-date library documentation.** Services like Context7 give the agent current docs for thousands of libraries, but they see every query. The self-hosted alternative is [Grounded Docs](https://github.com/arabold/docs-mcp-server), which indexes documentation into a local vector store. Worth it when you work with one big framework every day, necessary if you need to query documents that are not indexed by search engines. But it means adding another MCP and an embedding model - make sure you have enough VRAM. For a mix of different tasks, which is what I usually do, I'll just let the agent run a web search instead.
- **A second, small model for background jobs.** Commercial agents use a cheap, fast model for small tasks. Claude Code uses Haiku for that. Self-hosted, it would be a second vLLM instance with a gateway like LiteLLM in front. Skipped because 48GB is not enough for two decent models plus their KV caches, and the main model can do these chores itself - just slower.
- **Code intelligence.** Language server integration (errors, go to definition, find references) and semantic search over the codebase, like Cursor does. OpenCode has LSP built in, Pi would need an extension. Skipped because CLI agents do fine with `grep`, and every extra tool is another chance for a mid-size model to get confused.
- **Vision and browser automation.** Claude can look at a screenshot, and with a Playwright MCP server it can drive a browser to check its own changes in a web app. Qwen3.6 has a vision encoder, so this is possible. Skipped because I hardly ever use it, and images eat a lot of context.
- **Observability.** Commercial agents show tokens and cost per session. Tools like Langfuse or Arize Phoenix can trace every turn of the agent loop: what was sent, which tool was called, how long it took. Skipped because for one person running a few experiments, vLLM's own metrics and Pi's session logs are enough.


None of these is hard to add. Each one is a container and a few lines of config. But each one also adds prompt tokens, VRAM use or both, and the budget here is tight. Better to start small and add what turns out to be missing.

## Next

That's the theory. In [part 2](/homelab/coding-agent-2/): setting up vLLM, Pi and SearXNG on a rented GPU.
