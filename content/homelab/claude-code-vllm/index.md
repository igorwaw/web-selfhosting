---
title: "Claude Code, self-hosted"
date: 2026-08-23T13:00:00
draft: true
tags: ["ai"]
---

The [vLLM post](/homelab/vllm/) ended with an OpenAI-compatible server running on Serenity. The obvious next question: can an actual coding agent - not just a `curl` or a Python script - be pointed at it? Specifically Claude Code, since that's what I use daily.

## Why this is possible at all

Claude Code only ever speaks Anthropic's Messages API (`/v1/messages`), not the OpenAI Chat Completions shape that Ollama, vLLM and TensorRT-LLM all export. Until recently that meant a translation proxy sitting between Claude Code and any self-hosted engine - something like `claude-code-router` or a LiteLLM proxy rewriting requests both ways.

That's no longer strictly true for two of the three engines I've tried on Serenity:

- **Ollama** added a native Anthropic-compatible `/v1/messages` endpoint in v0.14.0, built specifically so Claude Code (and anything else using the Anthropic SDK) can point at it via `ANTHROPIC_BASE_URL` with no proxy in between.
- **vLLM** did the same - `/v1/messages` and `/v1/messages/count_tokens`, implemented internally as an adapter that translates the request to its existing OpenAI path and re-parses the response back into Anthropic's event format.
- **TensorRT-LLM** (`trtllm-serve`) hasn't - it's still OpenAI-only. Pointing Claude Code at it would still need a proxy in front, so it's out of scope for this post.

## vLLM over Ollama, for a different reason than usual

The [vLLM post's](/homelab/vllm/) conclusion was that Ollama is the better fit for one person having one conversation at a time - vLLM's batching machinery is pure overhead when there's nothing to batch. An agent loop changes the shape of the workload enough that the same conclusion doesn't hold:

- **The context keeps growing and gets resent whole.** Claude Code doesn't send one message per turn - every turn of the agent loop resends the entire conversation so far, system prompt included. Ollama's Anthropic compat layer doesn't honour `cache_control` at all, so it reprocesses that whole growing prefix from scratch on every single turn. vLLM doesn't implement Anthropic's TTL-based cache semantics either, but it has **automatic prefix caching** on by default (its V1 engine's KV cache manager reuses matching blocks across requests, LRU-evicted) - so an unchanged prefix gets reused regardless of whether `cache_control` was ever set. Not spec-compliant, but it gets most of the practical benefit for a session that's mostly "same history plus one more turn."
- **Forced tool choice.** Claude Code leans on `tool_choice` to force the model to emit a specific tool call rather than prose, at several points in the agent loop. vLLM supports `tool_choice="required"` properly, via structured outputs. Ollama's compat layer ignores it - which, on a model that isn't rock-solid at tool calling to begin with, is exactly the kind of gap that leaves Claude Code sitting there waiting for a tool call that never arrives in the right shape.

Neither of these is about raw throughput or concurrency, which is why it doesn't contradict the earlier post - it's a different workload shape asking for a different property from the server.

## Turning on tool calling

vLLM doesn't parse tool calls out of a model's output unless told to, and it doesn't know which format to expect - that varies by model family. Qwen2.5's chat template already bakes in a Hermes-style `<tool_call>` block, so the matching parser is `hermes`:

```yaml
command:
  - --model=Qwen/Qwen2.5-1.5B-Instruct-AWQ
  - --served-model-name=qwen2.5-1.5b-awq
  - --quantization=awq
  - --gpu-memory-utilization=0.85
  - --max-model-len=2048
  - --max-num-seqs=4
  - --enable-auto-tool-choice
  - --tool-call-parser=hermes
```

[Full Docker Compose file](/homelab/vllm/docker-compose.yml) (in the vLLM post - same file, now with these two flags added).

`--served-model-name` is new too, and unrelated to tool calling - it just gives the model a clean name to answer to, since the raw Hugging Face repo id (`Qwen/Qwen2.5-1.5B-Instruct-AWQ`) has a `/` in it that doesn't work everywhere a model name is expected as a single path segment or config value.

Picking the wrong parser for a model, or forgetting `--enable-auto-tool-choice` altogether, doesn't fail loudly - the model just answers in prose instead of the tool-call format the harness is expecting, and Claude Code sits there stuck.

## Pointing Claude Code at it

Claude Code reads its target from environment variables, all documented on [vLLM's own Claude Code integration page](https://docs.vllm.ai/en/latest/serving/integrations/claude_code/):

```bash
ANTHROPIC_BASE_URL=http://localhost:8000 \
ANTHROPIC_API_KEY=not-needed \
ANTHROPIC_AUTH_TOKEN=not-needed \
ANTHROPIC_DEFAULT_OPUS_MODEL=qwen2.5-1.5b-awq \
ANTHROPIC_DEFAULT_SONNET_MODEL=qwen2.5-1.5b-awq \
ANTHROPIC_DEFAULT_HAIKU_MODEL=qwen2.5-1.5b-awq \
claude
```

A few things stand out compared to talking to vLLM directly with the OpenAI SDK, as in the [vLLM client script](/homelab/vllm/vllm_client.py):

- **`ANTHROPIC_AUTH_TOKEN` is required, not optional**, even when vLLM isn't checking it (no `--api-key` was set on this server, per the [earlier note on vLLM's auth model](/homelab/vllm/#a-note-on-authentication)). Claude Code refuses to start without something in it.
- **All three model tiers point at the same served name.** Claude Code normally talks to three different Claude models depending on the task (Opus/Sonnet/Haiku-equivalent tiers) - background tasks and quick classifications get routed to the cheap, fast one. There's only one model on Serenity, so all three env vars have to collapse onto it, or the calls meant for the "cheap" tier 404 against a model that was never served.
- If running an older vLLM (pre-0.17.1), vLLM's docs mention Claude Code's telemetry header defeats prefix caching unless `"CLAUDE_CODE_ATTRIBUTION_HEADER": "0"` is set in `~/.claude/settings.json` - worth checking given prefix caching is most of the point of picking vLLM over Ollama here.

## Does it actually work

Wiring the two together is the easy part - both sides speak the same protocol now, so the connection itself isn't really in question. The open question is whether a 1.5B AWQ model on a 6GB card can drive Claude Code's agent loop at all: reliably choosing the right tool, producing edits that apply cleanly, not losing the thread over a long multi-step task. That's a much higher bar than anything the [vLLM](/homelab/vllm/) or [TensorRT-LLM](/homelab/tensorrt-llm/) posts asked of this model, and I haven't run it through a real task on Serenity long enough yet to report actual results here in good conscience rather than guessing.

*(TODO before publishing: run a real multi-step task through this setup on Serenity and replace this section with what actually happened, good or bad.)*
