---
title: "Embeddings and a local vector search"
date: 2026-07-25T15:00:00
draft: true
tags: ["ai"]
---

[Part 4](/homelab/gpu-guide-4/) mentioned Open WebUI's document upload needing an embedding model alongside the chat model, and left it there as something for another post. This is that post: what an embedding actually is, and building the smallest possible version of what a document-upload feature does under the hood.

## What an embedding is

A normal search matches keywords. An embedding model instead turns a piece of text into a fixed-length vector of numbers - a point in some high-dimensional space - such that texts with similar meaning end up as nearby points, even if they don't share a single word. "The car wouldn't start" and "vehicle had a dead battery" land close together; "the car wouldn't start" and "recipe for banana bread" land far apart. Search becomes "find the nearest points to this query's vector" instead of "find documents containing these words."

This is a much smaller model than anything else in this series - tens to a few hundred million parameters, not billions - and correspondingly light on VRAM. It doesn't generate text at all, it just maps input to a vector, which is also why it's fast: one forward pass per piece of text, no token-by-token generation loop.

## Getting a model: reusing what's already running

Ollama, from [part 3](/homelab/gpu-guide-3/), already serves embedding models through the same API, no separate service needed:

```bash
ollama pull nomic-embed-text
```

```bash
curl localhost:11434/api/embeddings -d '{
  "model": "nomic-embed-text",
  "prompt": "The car wouldn'\''t start this morning."
}'
```

That returns a vector - a few hundred floating-point numbers - representing that sentence. On its own it's not useful; it needs somewhere to be compared against others.

## A vector store, minimally

A proper deployment reaches for a dedicated vector database - Qdrant, Milvus, pgvector as a Postgres extension - built for scaling to millions of vectors with fast approximate search. For a personal note archive that's a few hundred documents, that's solving a problem that doesn't exist yet. Plain `numpy` and a brute-force comparison is enough:

```python
import numpy as np
import requests

def embed(text):
    r = requests.post("http://localhost:11434/api/embeddings",
                       json={"model": "nomic-embed-text", "prompt": text})
    return np.array(r.json()["embedding"])

docs = ["note about the NAS rebuild", "recipe for banana bread", "GPU driver troubleshooting"]
doc_vectors = np.array([embed(d) for d in docs])

def search(query, k=2):
    qv = embed(query)
    scores = doc_vectors @ qv / (np.linalg.norm(doc_vectors, axis=1) * np.linalg.norm(qv))
    top = np.argsort(scores)[::-1][:k]
    return [(docs[i], scores[i]) for i in top]

search("why won't my drives mount")
```

`@` between the matrix and the query vector is a dot product per row, normalised into cosine similarity - the standard way to compare embedding vectors, since it cares about direction rather than magnitude. Querying "why won't my drives mount" against those three example documents should rank the NAS one first despite not sharing a single word with the query, which is the entire trick embeddings are for.

## Chunking, the part that's easy to skip and shouldn't be

Real documents are longer than one sentence, and embedding an entire long document as a single vector tends to blur together whatever topics it covers into a mushy average. The usual fix is chunking - splitting each document into paragraph-or-so pieces before embedding, so a search can point at the specific section that's relevant rather than the whole file. It's also the one step in this whole exercise that a real document-upload feature spends most of its complexity on: chunk size, overlap between chunks, whether to split on paragraphs or sentences or a fixed token count all measurably change search quality, more than the choice of embedding model usually does.

## Closing the loop

This is, at small scale, exactly what Open WebUI is doing when a document gets uploaded: chunk it, embed each chunk, store the vectors, and at query time fetch the closest ones to splice into the prompt sent to the chat model - retrieval-augmented generation, RAG, the term the acronym is short for. Worth having built the toy version by hand once, if only so the feature in part 4 stops being a checkbox that does something unexplained.
