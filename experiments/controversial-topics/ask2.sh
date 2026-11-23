#!/bin/bash
# ask2.sh - every question in a fresh context, results go to results-2/
# questions-<lang>.txt: one question per line, "<number><TAB><question>"
mkdir -p results-2
for model in qwen3.5:2b deepseek-v2:16b ministral-3:8b; do
  for lang in en fr ru hy tr he ar; do
    echo "$(date +%T) $model $lang" >&2
    out="results-2/${model/:/-}-$lang.txt"
    : > "$out"
    while IFS=$'\t' read -r n q; do
      jq -n --arg m "$model" --arg q "$q" \
        '{model: $m, messages: [{role: "user", content: $q}], stream: false,
          options: {num_ctx: 16384}}' |
      curl -s http://localhost:11434/api/chat -d @- |
      jq -r --arg n "$n" --arg q "$q" \
        '"## \($n). \($q)\n\n(\(.total_duration / 1e9 | floor)s, \(.eval_count) tokens)\n\n### Thinking\n\n\(.message.thinking // "-")\n\n### Answer\n\n\(.message.content)\n"' >> "$out"
    done < "questions-$lang.txt"
  done
done
echo "$(date +%T) done" >&2
