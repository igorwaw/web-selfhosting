---
title: "Whisper: transcribing audio locally on the GPU"
date: 2026-07-25T12:00:00
draft: true
tags: ["ai"]
---

Of the GPU experiments on the list after [the LLM posts](/homelab/gpu-guide-3/), this is the one that's actually useful day to day rather than just a way to watch a 6GB card sweat: transcribing podcasts and recordings locally with Whisper.

## Why this one, and why local

Whisper turns speech into text - OpenAI's model, released openly rather than kept behind an API. Transcription runs fine on a CPU, but slowly: minutes of audio can mean minutes of waiting, sometimes longer than the recording itself. On the GPU, even this small card, it's close to real-time. That gap alone is worth having the card around for.

Local also means not uploading a recording anywhere to get text back - meetings, voice notes, anything not meant to leave the house. Given everything else on this blog is about keeping data at home, using a cloud transcription API here would have been an odd exception.

## Software choice: faster-whisper

The original `openai-whisper` package works, but [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - a reimplementation on top of CTranslate2 - is the more sensible pick for a small card: it supports the same quantisation idea from [the Ollama post](/homelab/gpu-guide-3/), running the model at int8 instead of float16, which both shrinks VRAM use and speeds things up. There's also `whisper.cpp`, llama.cpp's sibling project for this model, aimed more at CPU and embedded use than at squeezing a CUDA card.

Whisper comes in a handful of sizes - `tiny` up to `large-v3` - trading accuracy for VRAM and speed. `large-v3` at int8 fits on 6GB without trouble; there was no real need to compromise on model size here the way the LLM posts had to.

## Installing

```bash
pip install faster-whisper
```

No Docker container this time - it's a script I run occasionally against a file, not something that needs to stay up as a service the way Ollama does.

## Configuring

The choices that matter are all made where the model loads, not in a config file:

```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
```

`compute_type` is the quantisation knob - `int8_float16` runs the bulk of the model at int8 with float16 for the parts more sensitive to precision, a reasonable default. `device="cuda"` is what actually puts it on the GPU instead of falling back to CPU.

## Using it

```python
segments, info = model.transcribe("recording.mp3", beam_size=5)

for segment in segments:
    print(f"[{segment.start:.1f}s -> {segment.end:.1f}s] {segment.text}")
```

`info` includes the detected language and its confidence, useful when a recording isn't in English and I don't want to specify it by hand. Each segment comes with timestamps, which turns out to matter more than expected - it's what makes the output usable as actual subtitles, not just a wall of text.

For a whole folder of recordings, the same loop over `Path("podcasts").glob("*.mp3")` works, though this is also where the GPU's ceiling shows up: transcription is quick per file, but VRAM is shared with anything else on the card, and a `large-v3` model left loaded will elbow out an Ollama model I might also want running - the same trade every other post in this series has run into, just with less consequence here than an LLM refusing to fit at all.
