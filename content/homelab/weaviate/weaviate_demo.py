import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery, Filter

client = weaviate.connect_to_local()

# Create the collection, letting Weaviate call out to Ollama for embeddings
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

docs = client.collections.get("Document")

# Insert - plain text and metadata in, vectors handled behind the scenes
with docs.batch.dynamic() as batch:
    batch.add_object({"text": "The NAS uses SnapRAID plus mergerfs, not a RAID array.", "source": "nas-4"})
    batch.add_object({"text": "vLLM needs the model to fit in VRAM, no CPU offload of consequence.", "source": "vllm"})
    batch.add_object({"text": "Weaviate's ANN index is HNSW, a layered navigable graph.", "source": "weaviate"})

# Pure semantic search
result = docs.query.near_text(
    query="why won't my drives mount",
    limit=2,
    return_metadata=MetadataQuery(distance=True),
)

for obj in result.objects:
    print(obj.properties["text"], obj.metadata.distance)

# Semantic search narrowed by a metadata filter
result = docs.query.near_text(
    query="storage",
    filters=Filter.by_property("source").equal("nas-4"),
    limit=2,
)

# Hybrid search - blends vector similarity with BM25 keyword matching
result = docs.query.hybrid(query="HNSW graph", alpha=0.5, limit=2)

client.close()
