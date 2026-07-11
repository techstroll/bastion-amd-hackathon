#!/usr/bin/env bash
# Launch the Bastion serving layer on the AMD GPU (inside the ADC notebook).
#
#   bash gpu/serve_multilora.sh          # base + tenant LoRAs (port 8000)
#   ENABLE_70B=1 bash gpu/serve_multilora.sh   # also start a larger instance (port 8001)
#
# GPU_UTIL_8B defaults to 0.85 (single-model card, e.g. 48 GB Radeon PRO
# W7900). On a high-VRAM card like MI300X (192 GB) where the base model
# co-resides with a larger "hard tier" model, lower it (e.g. 0.35) so both
# fit — set GPU_UTIL_8B accordingly.

set -euo pipefail

BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
MODEL_70B="${MODEL_70B:-Qwen/Qwen2.5-72B-Instruct}"
ADAPTERS=/workspace/adapters

echo "=== Bastion serving layer ==="
rocm-smi --showmeminfo vram || true

# --- base + multi-LoRA (tenant tier) ----------------------------------------
vllm serve "$BASE_MODEL" \
  --port 8000 \
  --gpu-memory-utilization "${GPU_UTIL_8B:-0.85}" \
  --max-model-len 8192 \
  --enable-lora \
  --max-lora-rank 16 \
  --lora-modules \
      legal-lora="$ADAPTERS/legal-lora" \
      finance-lora="$ADAPTERS/finance-lora" \
  &> /workspace/vllm_8b.log &
echo "Multi-LoRA server starting on :8000 (log: /workspace/vllm_8b.log)"

# --- larger model (hard tier, optional) -------------------------------------
# Needs a high-VRAM card (MI300X-class). A 72B in bf16 needs ~144GB — do not
# enable this on a <80GB card, it will OOM. The router already falls back to
# the base model (labeled "demo fallback") for hard queries if this is off.
if [[ "${ENABLE_70B:-0}" == "1" ]]; then
  vllm serve "$MODEL_70B" \
    --port 8001 \
    --gpu-memory-utilization 0.70 \
    --max-model-len 8192 \
    &> /workspace/vllm_70b.log &
  echo "Larger-model server starting on :8001 (log: /workspace/vllm_70b.log)"
  echo "Set VLLM_70B_URL=http://localhost:8001/v1 for the router."
fi

echo
echo "Wait for 'Application startup complete' in the logs, then verify:"
echo "  curl -s localhost:8000/v1/models | python3 -m json.tool"
wait
