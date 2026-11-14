# NanoBits-Q ⚛️

**Quantum computing nano-bits technology lab — 7 qubit modalities at nanoscale, a ≤6-qubit statevector simulator, decoherence + error-correction math, Grover & Shor teaching demos, merged SLM / LLM / ML / NNL models, and 9 scout bots that gather, test, and sandbox-deploy new formulas and tech.**

👨‍💻 By Darion Kellar · 📜 MIT License · 🐍 Pure Python stdlib, zero dependencies, zero network

> Educational local simulation only. No live quantum hardware, no QPU cloud, no chip fabrication — every real-hardware action is a permanent HOLD gate.

## What it does

1. **Modality registry** — silicon spin / quantum dot (40 nm), superconducting, diamond NV/SnV, photonic nano-chip, trapped ion, neutral atom, topological: size, temperature, gate time, coherence, 2025-26 fidelity, fab, players, strength / weakness for each.
2. **Statevector simulator** — H / X / Z / phase / CNOT on up to 6 qubits; Bell and GHZ states verified exactly (0.5 / 0.5).
3. **Nano scale** — classifies sizes (a 40 nm quantum dot is 2,000× smaller than a human hair) against atoms, DNA, viruses, paper.
4. **Decoherence** — T2 fidelity-decay model: `0.5 + (f0-0.5)·exp(-t/T2)`.
5. **Error correction** — surface-code distance + physical-qubit estimator (100 logical @ 0.1% error ≈ 105,800 physical, teaching estimate).
6. **Grover / Shor teaching** — Grover on 64 items: 0.9966 success vs 0.015625 classical; Shor teaching factors 15 = 3×5 and 21 = 3×7. Grover is quadratic only; Shor threatens RSA, not AES-256.
7. **Quantum-dot designer** — 1/d² confinement trend: smaller dot → larger level spacing → single-electron qubit regime.
8. **Merged models (from scratch, advisory only, authority none)**
   - **SLM** TinySLM — bigram extractive summarizer
   - **LLM** TinyLLM — trigram drafter (explicitly *not* a production LLM)
   - **ML** MLModalityClassifier — kNN classifier (fault-tolerant candidate / promising / early / unproven)
   - **NNL** TinyMLP — 4-8-1 backprop neural network, outputs a 0-1 scale-risk score
9. **Scout bots** — 9 named bots (DotScout, CryoScout, GemScout, PhotonScout, IonScout, AtomScout, MajoranaScout, FormulaScout, TechScout): **GATHER** local registry/corpus only (`live=False`, zero network) → **TEST** 8 formulas against expected values (the deliberately wrong F8 must fail) → **VERIFY** (VerifyBot, below) → **DEPLOY** passes to a sandbox registry only → **REPORT** → **REPEAT**.
10. **VerifyBot — the repeat guard.** Sits between TEST and DEPLOY so an invention is never deployed twice. It *re-runs* the formula itself (never trusts the scout's claimed result), fingerprints it (sha256 of normalized name + verified result), and checks the registry three ways: exact fingerprint → `repeat_exact`, same normalized name → `repeat_name`, name-token overlap ≥ 0.75 + same result → `repeat_semantic` (a renamed copy). Only `novel` deploys. Proof: cycle 1 deploys 7, cycle 2 deploys **0 new** and blocks all 7 as repeats — the registry stays at 7 unique inventions.
11. **DeconstructionScout + Top 20 → new inventions.** A researched registry (2026-11-14, live sources below) of the top 20 current company inventions across nano tech, quantum computing, and data science — Google Willow + Quantum Echoes, IBM Nighthawk + Loon/qLDPC, Microsoft Majorana 1 + 2, AWS Ocelot, Quantinuum Helios, IonQ Tempo/256, QuEra/Harvard/MIT neutral-atom FT, Atom Computing AC1000, Caltech 6,100-atom array, PsiQuantum, Xanadu, D-Wave cryo control, Diraq+imec silicon spin, imec High-NA EUV quantum dots, SQC, Fujitsu+QuTech diamond SnV, Tanaka+Nagoya lead-free quantum dots. DeconstructionScout breaks each into component tags (core / error-correction / link / fab), then **recombines components from 3 different parents into 10 NEW concept inventions** — each VerifyBot-checked as `novel` (not a repeat of the Top 20, not a repeat of each other; re-running creation blocks all 10). Concepts are **data-only specs**: not built, not patented, not claimed to work.

**Sources for the Top 20:** Quantum Computing in 2025–2026 (permutations.app, Feb 2026); Quantum Industry Map (amotoolkit.com); Frontier Milestones quantum tracker; imec High-NA EUV quantum-dot fabrication (embedded.com, May 2026); Tanaka/Nagoya lead-free Ag-S-Te quantum dots (Oct 2026). Company qubit/fidelity numbers are the companies' reported figures; Microsoft's topological claims remain disputed in the literature and are scored lowest (0.45-0.50) in the registry for exactly that reason.

## HOLD gates (14)

`live_quantum_hardware` · `qpu_cloud_access` · `chip_fabrication` · `cryogenic_operation` · `claim_fault_tolerance` · `claim_quantum_advantage` · `control_real_device` · `sell_hardware` · `scout_live_web` · `deploy_real_hardware` · `deploy_live_formula_to_qpu` · `copy_proprietary_design` · `manufacture_new_invention` · `claim_new_invention_works`

## Run it

```bash
python3 main.py demo        # full demo + checks
python3 main.py modalities  # the 7 nano-bit modalities
python3 main.py bell        # {'00': 0.5, '11': 0.5}
python3 main.py grover      # Grover teaching demo
python3 main.py shor --n 21 # Shor teaching demo
python3 main.py dot --size 20
python3 main.py ecc         # surface-code estimate
python3 main.py brief --modality silicon_spin   # SLM+LLM+ML+NNL brief
python3 main.py scouts      # gather -> test -> VerifyBot -> sandbox-deploy -> repeat
python3 main.py verify      # VerifyBot demo: exact + renamed repeats blocked, novel passes
python3 main.py top20       # the Top 20 company inventions registry
python3 main.py deconstruct # break all 20 into component tags
python3 main.py invent      # recombine -> 10 NEW concept inventions, VerifyBot-checked
python3 main.py formulas    # PASS/FAIL per formula
python3 main.py checks      # self-checks
pytest -q
```

## Project structure

```
nanobits-q/
├── main.py                        # ONE interface: sim, registry, models, scouts, checks, CLI
├── tests/test_main.py             # pytest suite
├── conftest.py                    # root path fix for bare pytest
├── Dockerfile                     # python:3.12-slim, CMD demo
└── .github/workflows/
    ├── ci.yml                     # pytest + checks
    └── docker-publish.yml         # -> credkellar/nanobits-q:latest (needs DOCKERHUB secrets)
```

## Why it's cool

- The purest nano-bit — a silicon quantum dot — is a normal transistor's cousin, made on the same 300 mm CMOS lines as phone chips.
- It teaches the real bottleneck honestly: fidelity, coherence, wiring heat, and the ~1,000:1 physical-to-logical price of error correction.
- The scout loop proves its own honesty: one planted wrong formula, and it *fails* — only verified formulas deploy, and only to a sandbox.
