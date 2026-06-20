# GHCR — `vllm-laguna-m1-nvfp4-sm121`

## Pull (works now)

```bash
docker pull ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121:cu130-sm121-arm64-dda4668b
# or
docker pull ghcr.io/r0b0tlab/vllm-laguna-m1-nvfp4-sm121:latest
```

Digest: `sha256:6e2dfa4c48ac73965890a864dc1510017f42981e743b3f2834b4b189ad7712a8`

## Why the repo URL 404s

This URL is **wrong** for org-owned GHCR packages (and shows 404 when the package is private):

`https://github.com/r0b0tlab/laguna-m1-nvfp4-sm121-vllm/pkgs/container/vllm-laguna-m1-nvfp4-sm121`

Use the **org package** page instead:

**https://github.com/orgs/r0b0tlab/packages/container/package/vllm-laguna-m1-nvfp4-sm121**

After you make the package **public** and **link** it to `laguna-m1-nvfp4-sm121-vllm`, the repo-scoped packages tab may also list it — but the org URL remains canonical.

## Fix visibility (one-time, GitHub UI)

1. Sign in as **r0b0tlab** org admin.
2. Open the org package page above (or **Packages** on the org profile).
3. **Package settings** → **Change visibility** → **Public**.
4. **Connect repository** → `r0b0tlab/laguna-m1-nvfp4-sm121-vllm`.

API alternative (needs `write:packages` + org admin): `PATCH /orgs/r0b0tlab/packages/container/vllm-laguna-m1-nvfp4-sm121` with `{"visibility":"public","repository_id":<repo_id>}`.

## Republish

```bash
bash scripts/publish_ghcr_laguna_runtime.sh
```

Does not modify `vllm-dsv4-flash-gb10` — retags the same SM121 vLLM digest to this package name.