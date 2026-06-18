#!/bin/bash
# Laguna M.1 NVFP4 TP=2 on dual GB10 (SM121). launch-cluster.sh appends --nnodes/--node-rank/--master-*.
set -e

export CUDA_HOME=/usr/local/cuda
TORCH_LIB=$(python3 -c 'import os,torch;print(os.path.join(os.path.dirname(torch.__file__),"lib"))' 2>/dev/null)
export LD_LIBRARY_PATH="${TORCH_LIB}:/usr/local/lib/python3.12/dist-packages/torch/lib:${LD_LIBRARY_PATH}"
export TORCH_CUDA_ARCH_LIST=12.1a
export FLASHINFER_DISABLE_VERSION_CHECK=1
export VLLM_NVFP4_GEMM_BACKEND=flashinfer-cutlass
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

export NCCL_IB_DISABLE=0
export NCCL_SOCKET_IFNAME=enp1s0f0np0
export NCCL_IB_HCA=rocep1s0f0
export GLOO_SOCKET_IFNAME=enp1s0f0np0
export TP_SOCKET_IFNAME=enp1s0f0np0
export NCCL_IGNORE_CPU_AFFINITY=1
export NCCL_IB_GID_INDEX=3

MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-4}"
MAX_BATCHED="${MAX_BATCHED:-4096}"
GPU_UTIL="${GPU_UTIL:-0.82}"
KV_CACHE_DTYPE="${KV_CACHE_DTYPE:-fp8}"
ENFORCE_EAGER="${ENFORCE_EAGER:-1}"

EXTRA=()
if [[ "$ENFORCE_EAGER" == "1" ]]; then
  EXTRA+=(--enforce-eager)
fi

echo "$(date -Is) Laguna M.1 NVFP4 TP=2 len=$MAX_MODEL_LEN kv=$KV_CACHE_DTYPE util=$GPU_UTIL"

exec vllm serve /mnt/model \
  --served-model-name laguna-m1-nvfp4 \
  --host 0.0.0.0 --port 30100 \
  --trust-remote-code \
  --tensor-parallel-size 2 \
  --distributed-executor-backend mp \
  --disable-custom-all-reduce \
  --gpu-memory-utilization "$GPU_UTIL" \
  --max-model-len "$MAX_MODEL_LEN" \
  --max-num-seqs "$MAX_NUM_SEQS" \
  --max-num-batched-tokens "$MAX_BATCHED" \
  --kv-cache-dtype "$KV_CACHE_DTYPE" \
  --load-format fastsafetensors \
  "${EXTRA[@]}" \
  --enable-auto-tool-choice \
  --tool-call-parser poolside_v1 \
  --reasoning-parser poolside_v1 \
  --default-chat-template-kwargs '{"enable_thinking": true}'