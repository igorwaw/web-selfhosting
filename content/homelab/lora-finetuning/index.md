---
title: "Fine-tuning a small model with LoRA"
date: 2026-07-25T16:00:00
draft: true
tags: ["ai"]
---

Everything so far in this series - [Ollama](/homelab/gpu-guide-3/), [Whisper](/homelab/whisper/), [Stable Diffusion](/homelab/stable-diffusion/) - has been inference: running an already-trained model. This one is training, in the smallest form that fits on 6GB: fine-tuning with LoRA.

## Why not just fine-tune normally

Full fine-tuning updates every weight in a model, and needs to hold the gradients and optimiser state for each of them alongside the weights themselves - commonly 3-4x the model's own size in VRAM, on top of the model. A 3B model that comfortably fits for inference is nowhere close to fitting for full fine-tuning on this card.

**LoRA** (Low-Rank Adaptation) sidesteps this: the original weights stay frozen, untouched, and training instead learns a small pair of low-rank matrices inserted alongside certain layers (typically the attention projections). At inference, their output gets added to the frozen layer's output. The number of trainable parameters drops by orders of magnitude - often under 1% of the base model - and so does the VRAM needed to train them.

Combine that with loading the frozen base model itself in 4-bit (the same quantisation idea as [GGUF](/homelab/gpu-guide-3/#gguf-and-quantisation), though via a different library, covered below) and this is called **QLoRA**, and it's what actually makes this practical on 6GB.

## Software

The Hugging Face stack, not Ollama this time - training isn't what Ollama's built for:

```bash
pip install transformers peft bitsandbytes accelerate datasets
```

- **`transformers`** - loads the base model and handles the training loop.
- **`peft`** ("Parameter-Efficient Fine-Tuning") - Hugging Face's LoRA implementation.
- **`bitsandbytes`** - the 4-bit quantisation used to load the frozen base model, NF4 format rather than GGUF - a training-time equivalent of the same idea, not the same file format.
- **`datasets`** - loading and batching the training data.

## Setting expectations on the model and data

Small, deliberately: a 1-3B base model, and a dataset measured in hundreds to a few thousand examples, not millions. This is a toy fine-tune, teaching a narrow style or a persona the base model doesn't already have - not teaching it new facts, and not something to expect production quality from. Real fine-tuning runs are exactly the case [part 1](/homelab/gpu-guide-1/) flagged for renting a bigger GPU instead of owning one.

## Configuring the LoRA

```python
from peft import LoraConfig

config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    task_type="CAUSAL_LM",
)
```

- **`r`** - the rank of the adapter matrices, the main size/capacity knob. Higher captures more, at the cost of more trainable parameters and more VRAM; 8 is a common, conservative starting point.
- **`target_modules`** - which layers get an adapter. The query and value projections in attention are the usual minimum; more modules means more capacity and more memory.
- **`lora_alpha`** - a scaling factor on the adapter's contribution, conventionally set to twice `r`.

Training itself uses `transformers`' standard `Trainer`, just with the LoRA-wrapped model in place of the base one - batch size 1 with gradient accumulation, and fp16, both necessary rather than optional at this VRAM budget.

## Using the result

Training produces a small adapter - megabytes, not gigabytes, because that's the entire point - loaded on top of the base model:

```python
from peft import PeftModel

model = PeftModel.from_pretrained(base_model, "./my-lora-adapter")
```

From here, `peft` has a `merge_and_unload()` call that bakes the adapter back into the base weights, producing an ordinary model again - which is also the point where this loops back to the start of the series: merge, convert to GGUF, and it's something [Ollama](/homelab/gpu-guide-3/) can run like any other model.

Train small, merge, quantise, run - the full path from "toy fine-tune" back to the same inference stack the rest of this series has been using.
