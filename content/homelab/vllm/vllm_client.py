#!/usr/bin/env python3
"""Talk to a vLLM server with the OpenAI SDK - no vLLM-specific client needed."""

import concurrent.futures

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",  # vLLM doesn't check this, but the SDK requires a non-empty string
)

MODEL = "qwen2.5-1.5b-awq"  # must match --served-model-name in docker-compose.yml


def list_models():
    for m in client.models.list():
        print(m.id)


def chat_once():
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Explain PagedAttention in two sentences."},
        ],
        temperature=0.7,
        max_tokens=200,
    )
    print(response.choices[0].message.content)


def chat_streaming():
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Count from 1 to 5, one number per line."}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()


def concurrent_requests(n=5):
    """Fire several requests at once - this is what continuous batching is for."""

    def ask(i):
        r = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Say the number {i} and nothing else."}],
            max_tokens=10,
        )
        return i, r.choices[0].message.content.strip()

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        for i, text in pool.map(ask, range(n)):
            print(f"[{i}] {text}")


if __name__ == "__main__":
    print("== models ==")
    list_models()

    print("\n== single request ==")
    chat_once()

    print("\n== streaming ==")
    chat_streaming()

    print("\n== concurrent requests (batching demo) ==")
    concurrent_requests()
