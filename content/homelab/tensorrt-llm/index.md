---
title: "TensorRT-LLM: the fastest LLM engine"
date: 2026-08-23T09:00:00
draft: true
tags: ["ai","gpu"]
---

In the [vLLM post](/homelab/vllm/) I mentioned that TensorRT-LLM is not practical for a lab environment, where you change models or settings all the time. Of course, a homelab is impractical by design, so let's go ahead and run one more AI engine. I wanted to know whether it's possible at all on my GPU: RTX 3050 - 6GB, Ampere, no FP8 tensor cores.

## What is different about TensorRT-LLM

I covered it briefly in the vLLM post, so here's a repeat. Ollama, vLLM and most other engines load model's weights and run them through a generic, already-compiled kernel. TensorRT-LLM instead takes a model, a target GPU, and a target precision, and compiles an engine: a graph of CUDA kernels tuned specifically to that combination. That's where the throughput comes from, and it's also why the engine is not portable.

## Docker setup

NVIDIA ships TensorRT-LLM as a container image. I chose this path for two reasons. One, it's my preferred way to experiment due to easy cleanup. Two, this specific app is known to have very tight compatibility requirements, it's easier to have everything bundled together than making sure you have specific versions of CUDA toolkit, PyTorch and other libraries.

This assumes the driver and NVIDIA Container Toolkit are already installed. I covered it in the [GPU guide, part 2](/homelab/gpu-guide-2/).

To download the image, fist you need to create a free account on[NGC](https://ngc.nvidia.com/)

```bash
docker login nvcr.io
docker pull nvcr.io/nvidia/tensorrt-llm/release:0.15.0
```

Worth pinning the tag rather than pulling `latest`. The CLI changes often and changing container version often requires changing the compose file. The image itself is large - several times the size of vLLM's - because it bundles a full CUDA toolkit, TensorRT, and PyTorch. Expect to wait for a few minutes or more.

## Picking a model for 6GB

Same reasoning as the vLLM post, same model for a fair comparison: Qwen2.5-1.5B-Instruct. TensorRT-LLM's build step wants a quantised checkpoint going in rather than quantising on the fly, so the model gets converted through NVIDIA's own **TensorRT Model Optimizer** (`nvidia-modelopt`, bundled in the release image) before it ever reaches `trtllm-build`:

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:0.15.0 \
  python examples/quantization/quantize.py \
    --model_dir Qwen/Qwen2.5-1.5B-Instruct \
    --dtype float16 \
    --qformat int4_awq \
    --calib_size 32 \
    --output_dir /models/qwen2.5-1.5b-awq
```

AWQ needs a small calibration pass - a handful of representative prompts run through the model to decide how to scale each layer's weights into 4 bits without losing too much accuracy. `--calib_size 32` keeps that pass short; it's not tuning the model, just measuring it.

## Compiling the engine

The quantised checkpoint from the step above isn't runnable yet - it's TensorRT-LLM's own intermediate format, not an engine. That's `trtllm-build`:

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:0.15.0 \
  trtllm-build \
    --checkpoint_dir /models/qwen2.5-1.5b-awq \
    --output_dir /models/qwen2.5-1.5b-engine \
    --gemm_plugin auto \
    --max_batch_size 1 \
    --max_input_len 1024 \
    --max_seq_len 2048
```

This is the step the vLLM post warned would be expensive, and on Serenity's pair of old Xeons it was worse than expected. The build itself is a host-side graph compilation and kernel autotuning pass - it uses the GPU to time candidate kernels, but the orchestration around it is single-threaded CPU work, and it showed: a build I'd seen quoted at a few minutes on a modern desktop CPU took most of an hour here. Resident memory climbed uncomfortably close to the 16GB ceiling partway through, for a 1.5B model - TensorRT-LLM's build-time memory use doesn't track the final engine size, it tracks the largest intermediate graph representation it has to hold while fusing and autotuning, and that's a much bigger number. I kept `--max_batch_size` and `--max_input_len` deliberately small specifically to keep that peak inside 16GB rather than to shape runtime behaviour - on a card and a use case that only ever needs to serve one request at a time, there was no cost to doing so.

`--gemm_plugin auto` is the one flag I wouldn't set differently even with room to spare: it lets TensorRT-LLM pick fused GEMM kernels appropriate to the detected precision and GPU rather than leaving matrix multiplies to TensorRT's general-purpose kernel selection, and it's a big share of where the "faster than generic kernels" claim actually comes from.

## Loading and serving it

The output of `trtllm-build` is a directory of `.engine` files plus a config describing what they were built for - not a checkpoint that can be reinterpreted, a fixed artifact for this exact GPU, this exact precision, this exact batch/sequence ceiling. Serving it is the one part of this that looks reassuringly like the vLLM post:

```yaml
services:
  tensorrt-llm:
    image: nvcr.io/nvidia/tensorrt-llm/release:0.15.0
    restart: unless-stopped
    runtime: nvidia
    ipc: host
    ports:
      - "8000:8000"
    volumes:
      - ~/models/qwen2.5-1.5b-engine:/engine
    command:
      - trtllm-serve
      - /engine
      - --host=0.0.0.0
      - --port=8000
```

```bash
docker compose up -d
curl localhost:8000/v1/models
```

`trtllm-serve` fronts the engine with an OpenAI-compatible API, same shape as vLLM's - the same `openai` Python client and the same `chat_once()`/`chat_streaming()` helpers from the [vLLM client script](/homelab/vllm/vllm_client.py) worked against it unmodified, just pointed at a different port.

## Was it worth it

Single-request latency was close to what vLLM managed on the same 3050 with the same model at the same quantisation - both comfortably faster than nothing, neither a dramatic leap over the other, which tracks: the win TensorRT-LLM is built for is peak throughput on a fixed, known workload, and "one person, occasionally, at the terminal" isn't a throughput problem to begin with. I didn't bother running vLLM's concurrent-request benchmark against it - `--max_batch_size 1` means there's nothing to batch, by construction, so the comparison would just be measuring a number I chose ahead of time.

What I actually got out of the exercise was confirmation of the shape of the cost, not just the fact of it. Compute capability 8.6 is supported, the container pulls and runs on Debian without drama, and the engine does work once built - none of that was ever really in doubt. What's genuinely painful on this hardware is everything upstream of "it works": an hour-long build straining a 16GB ceiling for a 1.5B model, a multi-step convert-then-compile-then-serve pipeline where changing the context length means going back to `trtllm-build`, and an artifact at the end that's useless the moment I want a different model, a different GPU, or even just a longer context window. Possible, exactly as advertised. Also exactly the reason the vLLM post picked something else before this one was even written.
