#!/usr/bin/env bash
# Publish Laguna M.1 runtime to GHCR (separate package from vllm-dsv4-flash-gb10).
# Does NOT modify the DSV4 image — retags the same SM121 vLLM digest to this repo's package name.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SOURCE_IMAGE="${SOURCE_IMAGE:-ghcr.io/r0b0tlab/vllm-dsv4-flash-gb10:cu130-sm121-arm64-dda4668b}"
TAG="${TAG:-cu130-sm121-arm64-dda4668b}"
PACKAGE="${PACKAGE:-ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121}"
TARGET_IMAGE="${TARGET_IMAGE:-${PACKAGE}:${TAG}}"
TARGET_LATEST="${TARGET_LATEST:-${PACKAGE}:latest}"
LOG="${LOG:-$ROOT/evidence/ghcr_publish_laguna.log}"

exec > >(tee -a "$LOG") 2>&1
echo "=== Laguna GHCR publish $(date -Is) ==="
echo "SOURCE=$SOURCE_IMAGE"
echo "TARGET=$TARGET_IMAGE"
echo "LATEST=$TARGET_LATEST"

docker pull "$SOURCE_IMAGE"
SRC_DIGEST="$(docker image inspect "$SOURCE_IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null || true)"
echo "Source digest: ${SRC_DIGEST:-unknown}"

docker tag "$SOURCE_IMAGE" "$TARGET_IMAGE"
docker tag "$SOURCE_IMAGE" "$TARGET_LATEST"

docker push "$TARGET_IMAGE"
docker push "$TARGET_LATEST"

PUSHED_DIGEST="$(docker inspect "$TARGET_IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null || true)"
echo "Pushed: $PUSHED_DIGEST"
echo "Package page: https://github.com/r0b0tlab/laguna-m1-nvfp4-sm121-vllm/pkgs/container/vllm-laguna-m1-nvfp4-sm121"
echo "=== done $(date -Is) ==="