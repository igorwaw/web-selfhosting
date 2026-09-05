---
title: "TensorRT-LLM: the fastest LLM engine"
date: 2026-09-05T09:00:00
draft: false
tags: ["ai","gpu"]
---

In the [vLLM post](/homelab/vllm/) I mentioned that TensorRT-LLM is not practical for a lab environment, where you change models or settings all the time. Of course, a homelab is impractical by definition, so let's go ahead and run one more AI engine.

## What is different about TensorRT-LLM

I covered it briefly in the vLLM post, so here's a repeat. Ollama, vLLM and most other engines load model's weights and run them through a generic, already-compiled kernel. TensorRT-LLM instead takes a model, a target GPU, and a few parameters, and compiles an engine: a graph of CUDA kernels tuned specifically to that combination. That's where the throughput comes from. And it also means that changing model or parameters takes hours instead of seconds and the compilation needs some serious resources.

### Hardware limitations

- GPU: RTX 3050 - only 6GB VRAM, Ampere, no FP8 tensor cores.
- RAM: slow (DDR3) and not much of it (16GB)
- CPU: 2x Xeon E5-2609 from 2012

I'm limited on every front. Except the disk space, I've got plenty.

## Docker setup

NVIDIA ships TensorRT-LLM container image. I chose this path for two reasons. One, it's my preferred way to experiment due to easy cleanup. Two, this specific app is known to have very tight compatibility requirements, it's easier to have everything bundled together than making sure you have specific versions of CUDA toolkit, PyTorch and other libraries.

This assumes the driver and NVIDIA Container Toolkit are already installed. I covered it in the [GPU guide, part 2](/homelab/gpu-guide-2/). 

Download the image well ahead of the time when you want to play with it. It's huge: the version I used was 59GB. The download itself was a simple `docker pull nvcr.io/nvidia/tensorrt-llm/release:1.2.1`

Worth choosing an exact version rather than `latest`. The parameters often change, new versions often mean modifying the compose file. Also, if you're not using the latest driver from NVIDIA (e.g. you use an outdated one from your distro), check the release notes for compatibility. You might need to choose an older tag.

## First test: a small model

### Step 1: Model Optimizer

I tried a small model first: *Qwen2.5-1.5B-Instruct*. First step is quantisation from FP16 to AWQ with **TensorRT Model Optimizer**:

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:1.2.1 \
  python examples/quantization/quantize.py \
    --model_dir Qwen/Qwen2.5-1.5B-Instruct \
    --dtype float16 \
    --qformat int4_awq \
    --calib_size 32 \
    --output_dir /models/qwen2.5-1.5b-awq
```

AWQ needs a small calibration pass - a sample of prompts run through the model to decide how to scale each layer's weights into 4 bits without losing too much accuracy. `--calib_size 32` keeps that pass short.

This step took 17 minutes 45 seconds on Serenity. Looking at `top`, `nvidia-smi` and relevant Grafana dashboards showed that most of job was CPU-bound, and even worse - single-threaded. Serenity's CPUs are terrible at single-threaded tasks. Sometimes I wish I had a less interesting machine than a 2012 NUMA workstation.

### Compiling the engine

The result of the previous step isn't runnable yet, it's an intermediate format. Now comes `trtllm-build`:

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:1.2.1 \
  trtllm-build \
    --checkpoint_dir /models/qwen2.5-1.5b-awq \
    --output_dir /models/qwen2.5-1.5b-engine \
    --gemm_plugin auto \
    --max_batch_size 1 \
    --max_input_len 1024 \
    --max_seq_len 2048
```

This is the step I expected to take very long time. It uses the GPU to time candidate kernels, but most of it is again single-threaded CPU job. I also expected memory pressure. It turned out it wasn't so bad: it finished in 2 minutes 30 seconds and reported peak memory usage at 6.4GB. 

`--gemm_plugin auto` is the flag that gives a lot of performance boost. It lets TensorRT-LLM pick fused GEMM kernels appropriate to the detected precision and GPU rather than leaving matrix multiplies to TensorRT's general-purpose kernel selection. The other 3 flags set the concurrency (or in this case disable it) and context length.

### Serving the model

Now I can finally run the engine. This step looks closer to the vLLM post - though there are many flags and they all matter. With some trial and error, I got this:

```yaml
services:
  tensorrt-llm:
    image: nvcr.io/nvidia/tensorrt-llm/release:1.2.1
    restart: unless-stopped
    runtime: nvidia
    ipc: host
    ports:
      - "8000:8000"
    volumes:
      - ~/models/qwen2.5-1.5b-engine:/engine
    command:
      - trtllm-serve
      - serve
      - /engine
      - --backend=tensorrt
      - --tokenizer=Qwen/Qwen2.5-1.5B-Instruct
      - --max_batch_size=1
      - --max_seq_len=2048
      - --host=0.0.0.0
      - --port=8000
```

```bash
docker compose up -d
curl localhost:8000/v1/models
```

- `trtllm-serve` is finally the engine part of TensorRT-LLM.
- The `serve` subcommand is, I suppose, obvious.
- Not obvious, why it defaults to the pytorch backend (which expects a Hugging Face compatible model) and needs `backend=tensorrt` to switch to its own format
- The compiled engine directory has no tokenizer, so `--tokenizer` points to the original Hugging Face repo. That's a download, not a live dependency: the tokenizer files get pulled at startup and then run locally for every request. But it's not cached - which means the engine (with this configuration) can't start offline.
- `--max_batch_size` and `--max_seq_len` passed to `trtllm-serve` have to match what was used at the `trtllm-build` stage, or it refuses to start.

Starting the container - up to the point when it was ready to answer - took 1 minute 30 seconds. The engine now has an OpenAI-compatible API (older versions didn't have it). Which means the same clients I tried with Ollama and vLLM - a simple Python script, Open WebUI and `vllm bench serve` all worked.

### Timings

| Step | Time |
|---|---|
| Quantisation | 17m 45s |
| Engine build | 2m 30s |
| Engine start | 1m 30s |
| **Total** | 21m 45s |

### Benchmark against vLLM and Ollama

The [vLLM post](/homelab/vllm/) benchmarked vLLM and Ollama on this same Qwen2.5-1.5B model on this same RTX 3050, at concurrency 1, 2, 4 and 8. I wanted the same comparison, which meant going back to `trtllm-build` - I compiled it with `--max_batch_size 1` on my first try. Rebuilding with `--max_batch_size 8` and everything else unchanged took 3 minutes 56 seconds, slightly longer than the original build.

Then the same `vllm bench serve` command as before, once per concurrency level:

```bash
docker run --rm --network host --entrypoint vllm \
  vllm/vllm-openai:latest bench serve \
  --backend openai-chat \
  --base-url http://localhost:8000 --endpoint /v1/chat/completions \
  --model engine --tokenizer Qwen/Qwen2.5-1.5B-Instruct \
  --dataset-name random --random-input-len 512 --random-output-len 256 \
  --ignore-eos --seed 42 \
  --num-prompts 32 --max-concurrency 1 --request-rate inf
```

(`--max-concurrency` set to 1, 2, 4 and 8 in turn, one run each.)

| Concurrent requests | TensorRT-LLM tok/s | vLLM tok/s | Ollama tok/s |
|---|---|---|---|
| 1 | 103 | 15 | 63 |
| 2 | 216 | 30 | 80 |
| 4 | 380 | 59 | 92 |
| 8 | 698 | 59 | 132 |

(vLLM and Ollama figures are from the [vLLM post's benchmark table](/homelab/vllm/#the-rtx-3050-at-home).)

TensorRT-LLM already wins at concurrency 1. But at 8, it just flattens the competition. Throughput climbs almost linearly, 6.75x gain for 8x the concurrent requests. While Ollama barely scaled (2x output for 8x requests) and vLLM plateaud at 4. Mean time per output token on the TensorRT-LLM only increased from 9.0ms at concurrency 1 to 11.2ms at concurrency 8. 

## Second test: a larger model

The [Ollama post](/homelab/ollama-openwebui/) used *Qwen2.5-7B-Instruct* as a model that barely fits on the 6GB card. There was no chance of running it with vLLM, which needs more VRAM for itself. With TensorRT-LLM I wasn't sure. So I tested it.

### Model Optimizer

Same command, just different model.

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:1.2.1 \
  python examples/quantization/quantize.py \
    --model_dir Qwen/Qwen2.5-7B-Instruct \
    --dtype float16 \
    --qformat int4_awq \
    --calib_size 32 \
    --output_dir /models/qwen2.5-7b-awq
```

This took 67 minutes 15 seconds. Compared to 1.5B model, that's 3.8x the time for a model that's 4.7x bigger. And that includes 18 minutes for downloading the model from Hugging Face. Not a bad result, but damn, it felt long.

### Compiling the engine

Initially, same flags as the small model:

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:1.2.1 \
  trtllm-build \
    --checkpoint_dir /models/qwen2.5-7b-awq \
    --output_dir /models/qwen2.5-7b-engine \
    --gemm_plugin auto \
    --max_batch_size 1 \
    --max_input_len 1024 \
    --max_seq_len 2048
```

7 minutes 7 seconds, no errors. But one number in the build log should have told me trouble was coming: max VRAM usage was 5306MB - on a 6GB card. The build only needed VRAM for weights, serving will need KV cache on top of it.

### Serving it - the hard way

The compose file was identical to the small model's, except the model and tokenizer name. It crashed:

```console
RuntimeError: [TensorRT-LLM][ERROR] CUDA runtime error in ::cudaMalloc(ptr, n): out of memory
```

I checked the logs: `Memory usage when calculating max tokens in paged kv cache: total: 5.67 GiB, available: 0.03 GiB`. Only 30MB free, not enough for the KV cache.

I tried one parameter `--free_gpu_memory_fraction` - it sets how much of the free memory left after loading weights to reserve for the KV cache.

- **0.5** - crashed differently: `Failed to create cublas handle... Free Memory: 7 MB (0.1%)`. So there was enough VRAM for the KV cache, but nothing for cuBLAS handle, so the first inference request killed the process.
- **0.05** - didn't crash, but the server reported `max sequence length=1`. A KV cache that can hold one token isn't useful for anything. The first request failed with: `Prompt length (30) exceeds maximum input length (0)`.

The fix was to shrink the engine and that meant rebuild, not a runtime flag. Rebuilding at `--max_input_len 384 --max_seq_len 512` (down from 1024/2048) dropped the activation memory from 262MB to 91MB, which left 0.19GB free instead of 0.03GB.

That was still very tight, but combined with `--free_gpu_memory_fraction=0.3` it finally started. The chat was very fast (it answered in 2.9 seconds cold, 0.36 seconds warm), though with 512-token context length, not very practical.

The working configuration:

```yaml
services:
  tensorrt-llm:
    image: nvcr.io/nvidia/tensorrt-llm/release:1.2.1
    restart: unless-stopped
    runtime: nvidia
    ipc: host
    ports:
      - "8000:8000"
    volumes:
      - ~/models/qwen2.5-7b-engine-512:/engine
    command:
      - trtllm-serve
      - serve
      - /engine
      - --backend=tensorrt
      - --tokenizer=Qwen/Qwen2.5-7B-Instruct
      - --max_batch_size=1
      - --max_seq_len=512
      - --free_gpu_memory_fraction=0.3
      - --host=0.0.0.0
      - --port=8000
```

### Why it was easy on Ollama and barely possible here

Different quantisation. Both are nominally "4-bit," but nominal isn't the same as real. Qwen2.5-7B has ~7.6B parameters. If every weight was truly 4 bits, that's ~3.8GB. But the build log reported 5.3GB of weights for the TensorRT-LLM version. The public model Q4_K_M GGUF that Ollama pulled is around 4.7GB. Still more than 3.8GB a true 4-bit would have, but 1GB less than AWQ.

Squeezing all the model weights from 16 to 4 bits would result in a very unstable model,
so the common way is to have the most important parts - vocabulary and output tensors either at full FP16 resolution, or quantised, but at higher bit-depth. The public model was probably carefully tested to find the right balance between size and quality. While my naive quantisation just left some tensors at FP16.

Ollama can also automatically offload some transformer layers to RAM (and compute them on CPU), so a slightly too large model still works, but slower. Though I confirmed, this one ran 100% on the GPU. TensorRT-LLM has no such fallback.

### Timings

| Step | Time |
|---|---|
| Quantisation | 67m 15s |
| Engine build, attempt 1 (max_seq_len 2048 - built fine, couldn't serve) | 7m 7s |
| Engine build, attempt 2 (max_seq_len 512 - working) | 6m 35s |
| Cold start (working config) | 2m 26s |
| **Total, checkpoint to serving (working path only)** | 76m 16s |

### Benchmark against Ollama

I never tried vLLM at this size on Serenity (only on a rented L4). So this round is just the two engines, at concurrency 1.

TensorRT-LLM's context window is capped at 512 tokens by the rebuild above, so this benchmark uses shorter prompts than the small-model one: 128 input tokens, 128 output tokens instead of 512/256.

```bash
docker run --rm --network host --entrypoint vllm \
  vllm/vllm-openai:latest bench serve \
  --backend openai-chat \
  --base-url http://localhost:11434 --endpoint /v1/chat/completions \
  --model qwen2.5:7b --tokenizer Qwen/Qwen2.5-7B-Instruct \
  --dataset-name random --random-input-len 128 --random-output-len 128 \
  --ignore-eos --seed 42 \
  --num-prompts 32 --max-concurrency 1 --request-rate inf
```

(Same command against TensorRT-LLM, swapping the URL for `http://localhost:8000` and `--model engine`.)

| Engine | Quantisation | Output tok/s (1 request) | Mean TPOT | Mean TTFT |
|---|---|---|---|---|
| Ollama | Q4_K_M (GGUF) | 25 | 32.6ms | 752ms |
| TensorRT-LLM | AWQ-INT4 | 31 | 30.0ms | 291ms |

TensorRT-LLM still wins, but not by a large margin like with the 1.5B model. Though it's running a 20% bigger model.

## Third test: big model and big GPU

The [vLLM post](/homelab/vllm/) also benchmarked vLLM and Ollama on a 7B model on a rented VM with an L4 (24GB VRAM, CC 8.9, supports FP8), because Serenity's 6GB RTX 3050 wasn't going to show real multi-user behaviour. I wanted the same comparison for TensorRT-LLM, I'm not re-running the vLLM and Ollama benchmarks - those numbers are lifted straight from [that post's L4 table](/homelab/vllm/#the-rented-l4).

### Setup

I pulled the TensorRT-LLM image onto the VM before requesting a GPU for it, thinking that would save time once the GPU was attached. It didn't - attaching the GPU reset the instance's Docker state. Had to pull it again. Not much loss - Lightning AI's connection is much faster than at my home, so it was a few minutes rather than half an hour.

### Quantisation and engine build

Similar commands as above. This time I had no shortage of VRAM, so I could also have a longer context. The batch size was important, since I was going to run the concurrency test.

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:1.2.1 \
  python examples/quantization/quantize.py \
    --model_dir Qwen/Qwen2.5-7B-Instruct \
    --dtype float16 \
    --qformat int4_awq \
    --calib_size 32 \
    --output_dir /models/qwen2.5-7b-awq-l4
```

```bash
docker run --rm --runtime nvidia --gpus all \
  -v ~/models:/models \
  nvcr.io/nvidia/tensorrt-llm/release:1.2.1 \
  trtllm-build \
    --checkpoint_dir /models/qwen2.5-7b-awq-l4 \
    --output_dir /models/qwen2.5-7b-engine-l4 \
    --gemm_plugin auto \
    --max_batch_size 64 \
    --max_input_len 1024 \
    --max_seq_len 2048
```

| Step | Time |
|---|---|
| Quantisation | ~10 min |
| Engine build | 2m 30s |
| Engine start | ~1m 20s |

The build log reported a peak of 5306MB GPU memory during compilation - trivial for this card.

Serving command:

```yaml
services:
  tensorrt-llm:
    image: nvcr.io/nvidia/tensorrt-llm/release:1.2.1
    restart: unless-stopped
    runtime: nvidia
    ipc: host
    ports:
      - "8000:8000"
    volumes:
      - ~/models/qwen2.5-7b-engine-l4:/engine
    command:
      - trtllm-serve
      - serve
      - /engine
      - --backend=tensorrt
      - --tokenizer=Qwen/Qwen2.5-7B-Instruct
      - --max_batch_size=64
      - --max_seq_len=2048
      - --host=0.0.0.0
      - --port=8000
```

### Benchmark against vLLM and Ollama

Same `vllm bench serve` command and parameters as the vLLM post's L4 test - `--random-input-len 512 --random-output-len 256`, `--num-prompts 256`, concurrency 1, 8, 32 and 64:

```bash
docker run --rm --network host --entrypoint vllm \
  vllm/vllm-openai:latest bench serve \
  --backend openai-chat \
  --base-url http://localhost:8000 --endpoint /v1/chat/completions \
  --model engine --tokenizer Qwen/Qwen2.5-7B-Instruct \
  --dataset-name random --random-input-len 512 --random-output-len 256 \
  --ignore-eos --seed 42 \
  --num-prompts 256 --max-concurrency 64 --request-rate inf
```
| Concurrent requests | TensorRT-LLM tok/s | vLLM tok/s | Ollama tok/s |
|---|---|---|---|
| 1 | 49 | 29 | 45 |
| 8 | 345 | 209 | 71 |
| 32 | 1057 | 668 | 82 |
| 64 | 1345 | 997 | 213 |

TensorRT-LLM wins at every concurrency level. Worth noticing though that vLLM scaled better, just from a much lower starting point. Latency was better too. Mean time per output token went from 19.8ms at concurrency 1 to 47.0ms at 64 (vs. vLLM's 34ms to 59ms and Ollama's 20ms to over 200ms).

### Resource usage during the benchmark

No Grafana wired up on a rented VM, so I just watched `nvidia-smi` and `top` live during the runs. Regardless of concurrency, the L4 sat at around 99% utilisation, pulling its full 72W power limit (even exceeding it briefly) at 79°C, with about 21GB of the 24GB VRAM in use. 

The CPU showed 100% usage on 1 core while the other 7 were idle. RAM usage was under 8GB.

## What have I learned

I used Ollama and vLLM before writing the posts, but TensorRT-LLM was a new territory for me. Some things were different than I expected.

Building steps were a pain, but not because of the time it took. Even on my limited hardware, it wasn't a big issue. It was the number of parameters that you had to get right, by reading docs and trial-and-error. Add to that the ever changing CLI, so the tutorials you found on the web are most likely outdated.

I expected a better performance. I didn't expect an epic difference I saw with the 1.5B model. The big model-big GPU version was less dramatic, but still significant, 10-70%.

Only the 7B model on RTX didn't see much improvement. I have no explanation here, just the conclusion: when resources are tight, use Ollama.

And Ollama remains my default choice for experiments at home. It doesn't crash when you attempt to use 101% of VRAM, it makes it so easy to try different models and parameters, and even if other engines were much faster, it's irrelevant for this use case.

But for production, I might rethink. I've always used vLLM, but the performance gains of compiled kernels are substantial when you're doing inference at scale. The building step is only painful the 1st time: once you get the parameters right, you can just reuse them when updating a model or doing small tweaks.

And for the preparation and loading, single-core CPU performance is more important than the number of cores. Isn't it ironic?
