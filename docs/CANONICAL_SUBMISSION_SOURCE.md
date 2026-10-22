# Canonical Submission Source

`submission/` contains the four files packaged for the current Budget-Aware V2 candidate: `agent.yaml`, `eval_config.yaml`, `configs/sampling.yaml`, and `prompts/system.md`. Only edit this source tree for new candidates. Research, logs, and documentation stay outside `submission/`.

`python tools/build_submission.py` uses a fixed member order, fixed ZIP timestamps, and fixed compression so an unchanged source reproduces the same archive bytes. The current candidate's archived ZIP is `submissions/archive/2026-10-22__gemma-budget-aware-v2.zip`, SHA-256 `093531a857497faa04e15b618b708c0459ad813e9783df39a38654a3d70705e8`. The local builder was verified to reproduce this exact hash.

This is a reproducibility claim for the local archive only. It does not establish current Kaggle compiler compatibility, runtime success, score, or whether that archive produced any particular screenshot row.
