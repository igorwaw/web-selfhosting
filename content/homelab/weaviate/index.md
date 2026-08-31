---
title: "Weaviate: a proper vector database for RAG"
date: 2026-08-21T10:00:00
draft: true
tags: ["ai"]
---

The [embeddings post](/homelab/embeddings-vector-search/) ended with a toy retrieval-augmented generation (RAG) pipeline: a handful of documents, embedded with Ollama, stored in a plain numpy array, searched with a hand-rolled cosine similarity function. That's the whole idea of RAG in about fifteen lines, which is exactly why it's worth building once by hand. But a numpy array isn't something you'd actually run anything on. It lives in memory and disappears when the script exits, there's no way to filter "only PDFs from this folder" alongside the similarity search, and searching it is O(n) - fine for three documents, not fine for a real document collection. That's the gap a vector database fills.

## What a vector database actually adds

Three things, mainly, on top of "store some vectors and find the nearest ones":

**A real index instead of a linear scan.** Nearest-neighbour search over millions of vectors by brute force doesn't scale. Vector databases build an approximate nearest-neighbour (ANN) index - most commonly **HNSW** (Hierarchical Navigable Small World), a layered graph structure that finds *very probably* the closest vectors in roughly logarithmic time, trading a small amount of recall for a large amount of speed.

**Metadata alongside the vector.** Each object carries both its embedding and ordinary structured fields - source file, date, tags - so a query can combine "semantically similar to this" with "and also matches these filters," which a bare array can't do without scanning everything twice.

**Persistence and an API.** The index lives on disk, survives restarts, and is queried over a network API instead of being rebuilt in a Python process every time.

## Why Weaviate specifically

The field is fairly crowded - **Qdrant**, **Milvus**, **Chroma**, and **pgvector** (an extension bolted onto Postgres rather than a dedicated database) are the other names that come up constantly. Chroma is the simplest to start with but is really meant for local/embedded use rather than a standalone service; pgvector is the obvious choice if there's already a Postgres instance to extend rather than a new service to run; Milvus is built for a scale (billions of vectors, sharded clusters) well beyond anything a homelab needs. Weaviate sits in the middle: a real standalone service with a proper Docker image, a schema model that isn't an afterthought, built-in hybrid search (vector similarity plus keyword/BM25, combined), and optional modules that can call out to an embedding provider directly instead of embedding everything client-side. None of that makes it strictly better than Qdrant, which is a very close sibling in the same niche - Weaviate just had the more approachable docs and the module I wanted (`text2vec-ollama`, pointing straight at the Ollama instance from the [Ollama/Open WebUI post](/homelab/ollama-openwebui/)) already built in.

## Running it

Weaviate ships an official Docker image and needs essentially no configuration to start:

```yaml
services:
  weaviate:
    image: cr.weaviate.io/semitechnologies/weaviate:1.26.1
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "50051:50051"
    volumes:
      - weaviate-data:/var/lib/weaviate
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: /var/lib/weaviate
      ENABLE_MODULES: text2vec-ollama
      TEXT2VEC_OLLAMA_API_ENDPOINT: http://host.docker.internal:11434
      DEFAULT_VECTORIZER_MODULE: text2vec-ollama

volumes:
  weaviate-data:
```

[Full Docker Compose file](docker-compose.yml).

Port 8080 is the REST/GraphQL API, 50051 is gRPC (the newer client libraries use it by default and it's noticeably faster for batch imports - worth exposing even if nothing uses it on day one). `host.docker.internal` is Docker's way of letting a container reach a service running on the host itself - Ollama, in this case, already set up outside the compose file.

Anonymous access is fine for something bound to the home network; anything reachable from the internet needs an API key set instead, which Weaviate supports natively (`AUTHENTICATION_APIKEY_ENABLED` plus a key list) rather than needing a reverse proxy in front just to gate access.

## Configuring: collections and vectorizers

Weaviate's schema unit is a **collection** (older docs call it a "class") - roughly a table, if thinking in database terms. Two ways to get vectors into one:

**Bring your own vectors.** Embed client-side (with Ollama, as in the previous post) and hand Weaviate the finished vector alongside the object. Full control, no coupling between Weaviate and whatever's doing the embedding.

**Let Weaviate do it.** Configure a vectorizer module on the collection - `text2vec-ollama` here - and Weaviate calls out to Ollama itself whenever an object is added or a text query comes in. Less code at the call site, but it does mean Weaviate needs network access to Ollama and inherits its latency.

I went with the second - the whole point of running a real service instead of the toy script was to stop hand-wiring the embedding step:

```python
import weaviate
from weaviate.classes.config import Configure, Property, DataType

client = weaviate.connect_to_local()

client.collections.create(
    "Document",
    vectorizer_config=Configure.Vectorizer.text2vec_ollama(
        api_endpoint="http://host.docker.internal:11434",
        model="nomic-embed-text",
    ),
    properties=[
        Property(name="text", data_type=DataType.TEXT),
        Property(name="source", data_type=DataType.TEXT),
    ],
)

client.close()
```

`nomic-embed-text` is the same embedding model from the previous post, pulled through Ollama the same way. Everything after this point - inserting objects, querying - just sends plain text, and the vector never needs to be seen or handled directly.

## Using it

Inserting is a batch call with plain text and metadata, no manually computed vectors in sight:

```python
docs = client.collections.get("Document")

with docs.batch.dynamic() as batch:
    batch.add_object({"text": "The NAS uses SnapRAID plus mergerfs, not a RAID array.", "source": "nas-4"})
    batch.add_object({"text": "vLLM needs the model to fit in VRAM, no CPU offload of consequence.", "source": "vllm"})
    batch.add_object({"text": "Weaviate's ANN index is HNSW, a layered navigable graph.", "source": "weaviate"})
```

Querying by meaning:

```python
from weaviate.classes.query import MetadataQuery

result = docs.query.near_text(
    query="why won't my drives mount",
    limit=2,
    return_metadata=MetadataQuery(distance=True),
)

for obj in result.objects:
    print(obj.properties["text"], obj.metadata.distance)
```

Same query as the numpy version from the previous post, and it should rank the same NAS document first - but this time backed by an index that survives a restart, and one call away from adding `filters=Filter.by_property("source").equal("nas-4")` to combine the semantic search with a metadata filter, which the toy version had no way of doing at all.

[Full script](weaviate_demo.py).

**Hybrid search** is the other piece bare cosine similarity can't do: `docs.query.hybrid(query=..., alpha=0.5)` blends the vector search above with a BM25 keyword search, weighted by `alpha` (0 = pure keyword, 1 = pure vector). Useful for the cases pure embeddings handle badly - an exact model number, an error code, anything where the literal characters matter as much as the meaning.

## Closing the loop

This is the missing piece between the hand-rolled RAG toy and something worth pointing an actual document collection at: persistent storage, an index that scales past "fits in a numpy array," metadata filtering alongside semantic search, and hybrid search for the queries where keyword matching still matters. Next logical step is wiring this into something that generates answers instead of just returning ranked chunks - Open WebUI's document upload does a version of this already, but a from-scratch pipeline (retrieve from Weaviate, splice into a prompt, send to vLLM) is worth doing once by hand for the same reason the toy embeddings search was.
