#!/usr/bin/env bash
# Launch the Bastion serving layer on the MI300X (inside the ADC notebook).
#
#   bash gpu/serve_multilora.sh          # 8B base + tenant LoRAs (port 8000)
#   ENABLE_70B=1 bash gpu/serve_multilora.sh   # also start 70B instance (port 8001)
#
# One 192 GB MI300X hosts: base model + every tenant adapter (+ optionally a
# 70B for the hard tier). That single fact is the company.

set -euo pipefail

BASE_MODEL="${BASE_MODEL:-meta-llama/Llama-3.1-8B-Instruct}"
MODEL_70B="${MODEL_70B:-meta-llama/Llama-3.3-70B-Instruct}"
ADAPTERS=/workspace/adapters

echo "=== Bastion serving layer — MI300X (192 GB) ==="
rocm-smi --showmeminfo vram || true

# --- 8B base + multi-LoRA (tenant tier) -------------------------------------
# gpu-memory-utilization left low so the 70B can co-reside on the same card.
vllm serve "$BASE_MODEL" \
  --port 8000 \
  --gpu-memory-utilization "${GPU_UTIL_8B:-0.20}" \
  --max-model-len 8192 \
  --enable-lora \
  --max-lora-rank 16 \
  --lora-modules \
      legal-lora="$ADAPTERS/legal-lora" \
      finance-lora="$ADAPTERS/finance-lora" \
  &> /workspace/vllm_8b.log &
echo "8B multi-LoRA server starting on :8000 (log: /workspace/vllm_8b.log)"

# --- 70B (hard tier, optional) ----------------------------------------------
if [[ "${ENABLE_70B:-0}" == "1" ]]; then
  vllm serve "$MODEL_70B" \
    --port 8001 \
    --gpu-memory-utilization 0.70 \
    --max-model-len 8192 \
    &> /workspace/vllm_70b.log &
  echo "70B server starting on :8001 (log: /workspace/vllm_70b.log)"
  echo "Set VLLM_70B_URL=http://localhost:8001/v1 for the router."
fi

echo
echo "Wait for 'Application startup complete' in the logs, then verify:"
echo "  curl -s localhost:8000/v1/models | python3 -m json.tool"
wait
