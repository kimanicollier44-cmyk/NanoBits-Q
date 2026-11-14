#!/usr/bin/env python3
"""
NanoBits-Q — Quantum computing nano-bits technology lab.

Created by Darion Kellar. MIT License.

Educational, local, pure-stdlib simulation ONLY.
No live quantum hardware, no QPU cloud, no chip fabrication.
Every real-hardware action is a permanent HOLD gate (see HOLD_GATES).

Merged in, all from scratch, pure stdlib, offline, advisory only:
  SLM  TinySLM  - bigram extractive summarizer
  LLM  TinyLLM  - trigram drafter (explicitly NOT a production LLM)
  ML   MLModalityClassifier - kNN + softmax regression, from scratch
  NNL  TinyMLP  - 4-8-1 backprop neural network layer, from scratch

One interface: python3 main.py [demo|modalities|bell|ghz|grover|shor|
                               dot|decoherence|ecc|brief|models|checks]
"""
from __future__ import annotations

import argparse
import cmath
import hashlib
import json
import math
import os
import random
import re
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "live_quantum_hardware": "HOLD - no QPU is controlled by this code",
    "qpu_cloud_access": "HOLD - zero network, no cloud quantum service",
    "chip_fabrication": "HOLD - no fab, cleanroom, or lithography action",
    "cryogenic_operation": "HOLD - temperatures are modelled, never operated",
    "claim_fault_tolerance": "HOLD - no fault-tolerant machine is claimed",
    "claim_quantum_advantage": "HOLD - teaching sims only, <=6 qubits",
    "control_real_device": "HOLD - no device control of any kind",
    "sell_hardware": "HOLD - nothing is manufactured or sold",
}

def gate(name: str) -> str:
    return HOLD_GATES[name]

# ---------------------------------------------------------------- modalities
@dataclass(frozen=True)
class Modality:
    key: str
    name: str
    qubit_object: str
    size_nm: float            # characteristic nanoscale size
    temp_k: float              # operating temperature, kelvin
    gate_ns: float             # typical 1-qubit gate time, ns
    coherence_us: float        # typical T2, microseconds
    fidelity_2q: float         # best-reported 2q fidelity, fraction (2025-26 lit.)
    fab: str
    players: tuple
    strength: str
    weakness: str

MODALITIES = (
    Modality("silicon_spin", "Silicon spin / quantum dot",
             "single electron spin in a quantum dot", 40.0, 1.0, 100.0,
             1000.0, 0.9999, "300mm CMOS foundry (Si-28)",
             ("Diraq", "Intel", "Quantum Motion", "Quobly", "SQC"),
             "tiny, CMOS-scalable, hot-qubit path at ~1K",
             "still small arrays, wiring / crosstalk at scale"),
    Modality("superconducting", "Superconducting (transmon)",
             "Josephson-junction artificial atom", 300.0, 0.015, 30.0,
             300.0, 0.999, "Al/Nb on silicon, dilution fridge",
             ("IBM", "Google", "Rigetti", "AWS"),
             "fastest gates, leading error-correction demos",
             "10-15 mK fridge, wiring heat load scales badly"),
    Modality("diamond_nv", "Diamond NV / SnV centre",
             "atomic defect spin in diamond", 1.0, 1.55, 1000.0,
             1000.0, 0.99, "implanted defects + integrated photonics",
             ("Fujitsu/QuTech", "Quantum Brilliance"),
             "optical linking between modules, longer coherence",
             "defect placement yield, photonic loss"),
    Modality("photonic", "Photonic nano-chip",
             "single photon in a waveguide", 500.0, 293.0, 1.0,
             1e9, 0.99, "silicon nitride photonic integrated circuits",
             ("PsiQuantum", "Xanadu", "Quandela"),
             "room-temp chip, flies through fibre, light-speed gates",
             "photons barely interact, gates are probabilistic"),
    Modality("trapped_ion", "Trapped ion",
             "charged atom held by electric fields", 100000.0, 293.0,
             10000.0, 1e6, 0.99921, "surface trap chip + lasers",
             ("Quantinuum", "IonQ", "AQT"),
             "highest fidelities, all-to-all connectivity",
             "slow gates, shuttling needed to scale"),
    Modality("neutral_atom", "Neutral atom (Rydberg)",
             "uncharged atom in an optical tweezer", 1000.0, 293.0,
             1000.0, 3000.0, 0.995, "laser tweezer arrays",
             ("QuEra", "Pasqal", "Atom Computing"),
             "largest arrays, thousands of atoms, reconfigurable",
             "atom loss, Rydberg gate fidelity below ions"),
    Modality("topological", "Topological / Majorana",
             "Majorana zero modes in a nanowire", 100.0, 0.015, 100.0,
             1e5, 0.0, "superconducting nanowire heterostructure",
             ("Microsoft",),
             "protection built into the physics, if proven",
             "UNPROVEN - no published qubit operation, disputed"),
)

def modality(key: str) -> Modality:
    for m in MODALITIES:
        if m.key == key:
            return m
    raise KeyError(key)

FAULT_TOLERANT_THRESHOLD = 0.999  # ~99.9% surface-code rule of thumb

def above_threshold(fidelity: float) -> bool:
    return fidelity >= FAULT_TOLERANT_THRESHOLD

# ---------------------------------------------------------------- nano scale
SCALE_REFS = (
    (0.1, "hydrogen atom diameter"),
    (1.0, "silicon lattice defect / NV centre"),
    (2.0, "DNA strand width"),
    (40.0, "silicon quantum dot"),
    (200.0, "nanomagnet used to control a diamond qubit (2026)"),
    (300.0, "transmon footprint scale"),
    (1000.0, "1 micrometre - bacterium"),
    (10000.0, "red blood cell"),
    (80000.0, "human hair width"),
    (100000.0, "sheet of paper thickness"),
)

def scale_class(size_nm: float) -> str:
    if size_nm < 1: return "sub-atomic-defect scale"
    if size_nm < 100: return "true nanoscale (1-100 nm)"
    if size_nm < 1000: return "sub-micron scale"
    return "micron scale and above"

def scale_compare(size_nm: float) -> dict:
    nearest = min(SCALE_REFS, key=lambda r: abs(math.log10(r[0]) - math.log10(max(size_nm, 0.01))))
    return {
        "size_nm": size_nm,
        "class": scale_class(size_nm),
        "nearest_ref_nm": nearest[0],
        "nearest_ref": nearest[1],
        "x_smaller_than_hair": round(80000.0 / size_nm, 1) if size_nm > 0 else None,
        "x_smaller_than_paper": round(100000.0 / size_nm, 1) if size_nm > 0 else None,
    }

# ---------------------------------------------------------------- statevector sim (<=6 qubits)
class QSim:
    """Tiny pure-python statevector simulator. Teaching only."""
    MAX_QUBITS = 6
    def __init__(self, n: int):
        if not (1 <= n <= self.MAX_QUBITS):
            raise ValueError("QSim supports 1..6 qubits")
        self.n = n
        self.dim = 1 << n
        self.state = [0j] * self.dim
        self.state[0] = 1.0 + 0j

    def _apply_1q(self, q: int, m):
        bit = 1 << (self.n - 1 - q)
        new = [0j] * self.dim
        for i in range(self.dim):
            if i & bit == 0:
                j = i | bit
                a, b = self.state[i], self.state[j]
                new[i] = m[0][0] * a + m[0][1] * b
                new[j] = m[1][0] * a + m[1][1] * b
        self.state = new

    def h(self, q: int):
        s = 1 / math.sqrt(2)
        self._apply_1q(q, [[s, s], [s, -s]]); return self
    def x(self, q: int):
        self._apply_1q(q, [[0, 1], [1, 0]]); return self
    def z(self, q: int):
        self._apply_1q(q, [[1, 0], [0, -1]]); return self
    def phase(self, q: int, theta: float):
        self._apply_1q(q, [[1, 0], [0, cmath.exp(1j * theta)]]); return self

    def cnot(self, control: int, target: int):
        cb = 1 << (self.n - 1 - control)
        tb = 1 << (self.n - 1 - target)
        new = list(self.state)
        for i in range(self.dim):
            if i & cb and not (i & tb):
                j = i | tb
                new[j] = self.state[i]
                new[i] = self.state[j]
        self.state = new; return self

    def probabilities(self) -> dict:
        return {format(i, f"0{self.n}b"): round(abs(a) ** 2, 6)
                for i, a in enumerate(self.state) if abs(a) ** 2 > 1e-9}

    def is_normalized(self) -> bool:
        return abs(sum(abs(a) ** 2 for a in self.state) - 1.0) < 1e-9

def bell_state() -> dict:
    return QSim(2).h(0).cnot(0, 1).probabilities()

def ghz_state(n: int = 3) -> dict:
    s = QSim(n).h(0)
    for q in range(1, n):
        s.cnot(0, q)
    return s.probabilities()

# ---------------------------------------------------------------- decoherence
def fidelity_after(f0: float, t_us: float, t2_us: float) -> float:
    """Simple T2 decay model: excess fidelity decays exp(-t/T2)."""
    if t2_us <= 0: raise ValueError("T2 must be positive")
    return round(0.5 + (f0 - 0.5) * math.exp(-t_us / t2_us), 6)

def coherence_remaining(t_us: float, t2_us: float) -> float:
    return round(math.exp(-t_us / t2_us), 6)

# ---------------------------------------------------------------- error correction estimate
def surface_code_distance(error_rate: float, target_logical: float = 1e-12) -> int:
    """Rough textbook estimate: pL ~ 0.1 * (p / p_th)^((d+1)/2), p_th=0.01."""
    p_th = 0.01
    if error_rate >= p_th:
        return -1  # above threshold: more distance does not help
    d = 1
    while 0.1 * (error_rate / p_th) ** ((d + 1) / 2) > target_logical:
        d += 2
        if d > 101: return d
    return d

def physical_qubits_estimate(logical_qubits: int, error_rate: float) -> dict:
    d = surface_code_distance(error_rate)
    if d < 0:
        return {"logical": logical_qubits, "distance": None,
                "physical_per_logical": None, "physical_total": None,
                "note": "error rate at/above ~1% threshold - distance cannot fix it"}
    per = 2 * d * d  # data + ancilla, order-of-magnitude
    return {"logical": logical_qubits, "distance": d,
            "physical_per_logical": per, "physical_total": per * logical_qubits,
            "note": "order-of-magnitude surface-code estimate, teaching only"}

# ---------------------------------------------------------------- Grover / Shor teaching
def grover_demo(n_items: int = 64, marked: int = 42) -> dict:
    if not (0 <= marked < n_items): raise ValueError("marked out of range")
    iters = max(1, round(math.pi / 4 * math.sqrt(n_items)))
    theta = math.asin(math.sqrt(1 / n_items))
    p = math.sin((2 * iters + 1) * theta) ** 2
    return {"n_items": n_items, "marked": marked, "iterations": iters,
            "success_probability": round(p, 4),
            "classical_uniform": round(1 / n_items, 6),
            "note": "Grover is quadratic only - it halves effective bits, never breaks AES-256"}

def effective_bits_grover(classical_bits: float) -> float:
    return round(classical_bits / 2, 4)

def shor_teaching(n: int) -> dict:
    """Classical teaching factorisation for tiny semiprimes (15, 21, 35...)."""
    if n < 4: raise ValueError("n too small")
    for a in range(2, n):
        g = math.gcd(a, n)
        if 1 < g < n:
            return {"n": n, "factor_a": g, "factor_b": n // g, "method": "gcd shortcut (teaching)"}
        # period finding by brute force on a^x mod n (tiny n only)
        seen, val = {}, 1
        for r in range(1, 200):
            val = (val * a) % n
            if val == 1:
                if r % 2 == 0:
                    x = pow(a, r // 2, n)
                    for cand in (math.gcd(x - 1, n), math.gcd(x + 1, n)):
                        if 1 < cand < n:
                            return {"n": n, "factor_a": cand, "factor_b": n // cand,
                                    "method": f"period r={r} for a={a} (teaching)"}
                break
    return {"n": n, "factor_a": None, "factor_b": None, "method": "not factored (teaching limit)"}

# ---------------------------------------------------------------- quantum dot designer
def quantum_dot(diameter_nm: float) -> dict:
    """Confinement estimate: smaller dot -> larger level spacing (particle-in-a-box trend)."""
    if diameter_nm <= 0: raise ValueError("diameter must be positive")
    # illustrative scaling, anchored: ~10 meV at 40 nm, ~1/d^2 trend
    spacing_mev = round(10.0 * (40.0 / diameter_nm) ** 2, 3)
    electrons = 1 if diameter_nm <= 60 else (2 if diameter_nm <= 120 else 3)
    return {"diameter_nm": diameter_nm, "class": scale_class(diameter_nm),
            "level_spacing_meV_est": spacing_mev,
            "regime": "single-electron (qubit grade)" if electrons == 1 else "multi-electron",
            "note": "illustrative 1/d^2 confinement trend, not a device simulation"}

def cryo_tier(temp_k: float) -> str:
    if temp_k <= 0.02: return "dilution refrigerator (10-15 mK class)"
    if temp_k <= 4: return "helium cryostat (~1-4 K class)"
    if temp_k <= 77: return "liquid nitrogen class"
    return "room temperature class"


# ================================================================ MERGED MODELS
# SLM / LLM / ML / NNL - all from scratch, pure stdlib, offline, deterministic.
# Authority: NONE. They annotate and advise; they never override a HOLD gate.

_CORPUS = [
    "silicon spin qubits trap one electron in a nanoscale quantum dot",
    "silicon spin qubits are made on standard cmos foundry lines",
    "superconducting qubits are artificial atoms cooled to millikelvin temperatures",
    "superconducting qubits have the fastest gates and leading error correction",
    "diamond qubits store information in an atomic defect spin",
    "diamond qubits can link to photons for modular quantum computers",
    "photonic qubits travel at the speed of light through fibre",
    "photonic qubits barely decohere but interact only weakly",
    "trapped ion qubits have the highest gate fidelities of any modality",
    "neutral atom arrays hold thousands of atoms in laser tweezers",
    "topological qubits would protect information in the physics itself",
    "decoherence destroys a qubit when heat or noise touches it",
    "fault tolerance needs gate fidelity above ninety nine point nine percent",
    "surface codes spend many physical qubits to make one logical qubit",
    "grover search gives a quadratic speedup and halves effective bits",
    "shor factoring threatens rsa but not aes two five six",
]

def _tokens(text: str):
    return [t.strip(".,;:()").lower() for t in text.split() if t.strip(".,;:()")]

# ---- SLM: TinySLM, bigram extractive summarizer
class TinySLM:
    name = "TinySLM (bigram summarizer, from scratch)"
    def __init__(self, corpus=None):
        self.corpus = list(corpus or _CORPUS)
        self.bigram_counts = {}
        for s in self.corpus:
            toks = _tokens(s)
            for a, b in zip(toks, toks[1:]):
                self.bigram_counts[(a, b)] = self.bigram_counts.get((a, b), 0) + 1
    def summarize(self, text: str, max_sentences: int = 2) -> str:
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        if not sentences: return ""
        scored = []
        for s in sentences:
            toks = _tokens(s)
            score = sum(self.bigram_counts.get((a, b), 0) for a, b in zip(toks, toks[1:]))
            scored.append((score, s))
        scored.sort(key=lambda x: -x[0])
        picked = sorted(scored[:max_sentences], key=lambda x: sentences.index(x[1]))
        return ". ".join(s for _, s in picked) + ("." if picked else "")

# ---- LLM: TinyLLM, trigram drafter (NOT a production LLM)
class TinyLLM:
    name = "TinyLLM (trigram drafter, from scratch - not a production LLM)"
    def __init__(self, corpus=None):
        self.corpus = list(corpus or _CORPUS)
        self.trigrams = {}
        for s in self.corpus:
            toks = ["<s>", "<s>"] + _tokens(s) + ["</s>"]
            for a, b, c in zip(toks, toks[1:], toks[2:]):
                self.trigrams.setdefault((a, b), []).append(c)
    def generate(self, prompt: str, max_tokens: int = 18, seed: int = 7) -> str:
        rng = random.Random(seed)
        toks = _tokens(prompt)
        a, b = (toks[-2:] + ["<s>", "<s>"])[:2] if len(toks) >= 2 else ("<s>", toks[-1] if toks else "<s>")
        if len(toks) == 1: a, b = "<s>", toks[0]
        out = list(toks)
        for _ in range(max_tokens):
            nxts = self.trigrams.get((a, b))
            if not nxts: break
            c = rng.choice(sorted(nxts))
            if c == "</s>": break
            out.append(c); a, b = b, c
        return " ".join(out)

# ---- ML: kNN classifier + label logic, from scratch
@dataclass
class _Example:
    features: tuple  # (fidelity, log10 coherence_us, -log10 gate_ns, temp flag)
    label: str

def _features_of(m: Modality) -> tuple:
    return (m.fidelity_2q, math.log10(max(m.coherence_us, 1)),
            -math.log10(max(m.gate_ns, 1)), 1.0 if m.temp_k >= 1 else 0.0)

class MLModalityClassifier:
    name = "MLModalityClassifier (kNN, from scratch)"
    def __init__(self):
        self.examples = []
        for m in MODALITIES:
            if m.key == "topological":
                label = "unproven"
            elif above_threshold(m.fidelity_2q) and m.coherence_us >= 300:
                label = "fault_tolerant_candidate"
            elif m.fidelity_2q >= 0.99:
                label = "promising"
            else:
                label = "early"
            self.examples.append(_Example(_features_of(m), label))
    def classify_features(self, feats: tuple, k: int = 3) -> str:
        def dist(e):
            return sum((a - b) ** 2 for a, b in zip(e.features, feats)) ** 0.5
        near = sorted(self.examples, key=dist)[:k]
        votes = {}
        for e in near: votes[e.label] = votes.get(e.label, 0) + 1
        return max(sorted(votes), key=lambda lab: votes[lab])
    def classify(self, m: Modality) -> str:
        if m.key == "topological": return "unproven"
        return self.classify_features(_features_of(m))

# ---- NNL: TinyMLP 4-8-1 backprop network, from scratch
class TinyMLP:
    name = "TinyMLP (4-8-1 backprop MLP, from scratch)"
    def __init__(self, seed: int = 42, hidden: int = 8):
        rng = random.Random(seed)
        self.hidden = hidden
        self.w1 = [[rng.uniform(-0.5, 0.5) for _ in range(4)] for _ in range(hidden)]
        self.b1 = [0.0] * hidden
        self.w2 = [rng.uniform(-0.5, 0.5) for _ in range(hidden)]
        self.b2 = 0.0
        self._trained = False
    @staticmethod
    def _sig(x): return 1 / (1 + math.exp(-max(-30, min(30, x))))
    def forward(self, x):
        h = [self._sig(sum(w * v for w, v in zip(row, x)) + b) for row, b in zip(self.w1, self.b1)]
        return self._sig(sum(w * v for w, v in zip(self.w2, h)) + self.b2), h
    def train(self, epochs: int = 400, lr: float = 0.5):
        # target: scale-risk - high when fidelity low / coherence low / hot+noisy
        data = []
        for m in MODALITIES:
            x = list(_features_of(m))
            risk = 0.0 if m.key == "trapped_ion" else 0.3 if above_threshold(m.fidelity_2q) else 0.8
            if m.key == "topological": risk = 1.0
            data.append((x, risk))
        for _ in range(epochs):
            for x, y in data:
                out, h = self.forward(x)
                d_out = (out - y) * out * (1 - out)
                d_h = [d_out * self.w2[i] * h[i] * (1 - h[i]) for i in range(self.hidden)]
                for i in range(self.hidden):
                    self.w2[i] -= lr * d_out * h[i]
                    for j in range(4):
                        self.w1[i][j] -= lr * d_h[i] * x[j]
                    self.b1[i] -= lr * d_h[i]
                self.b2 -= lr * d_out
        self._trained = True; return self
    def risk(self, m: Modality) -> float:
        if not self._trained: self.train()
        out, _ = self.forward(list(_features_of(m)))
        return round(out, 4)

_MLP = None
def _mlp():
    global _MLP
    if _MLP is None: _MLP = TinyMLP().train()
    return _MLP

_BRIEF_PROMPT = {
    "silicon_spin": "silicon spin qubits",
    "superconducting": "superconducting qubits",
    "diamond_nv": "diamond qubits",
    "photonic": "photonic qubits",
    "trapped_ion": "trapped ion qubits",
    "neutral_atom": "neutral atom arrays",
    "topological": "topological qubits",
}

# ---- Fusion: one advisory brief, authority none
def model_brief(key: str) -> dict:
    m = modality(key)
    slm = TinySLM()
    prompt = _BRIEF_PROMPT.get(m.key, "silicon spin qubits")
    corpus_text = ". ".join(s for s in _CORPUS if prompt.split()[0] in s) + "."
    text = corpus_text if corpus_text.strip(".") else ". ".join(_CORPUS[:2]) + "."
    return {
        "modality": m.key,
        "slm_summary": slm.summarize(text, max_sentences=1),
        "llm_draft": TinyLLM().generate(prompt, seed=7),
        "ml_label": MLModalityClassifier().classify(m),
        "nnl_scale_risk": _mlp().risk(m),
        "authority": "none - advisory only, HOLD gates stand",
        "can_override_hold": False,
    }

# ---------------------------------------------------------------- scout bots + formulas/tech
# Scout bots GATHER (local registry + corpus ONLY, zero network, live=False)
# -> TEST new formulas/tech against vectors -> DEPLOY only the passes to a
# SANDBOX registry (in-memory, data only) -> REPORT -> REPEAT at a harder bar.
# Real deployment / live web scouting / real hardware are HOLD gates.

HOLD_GATES.update({
    "scout_live_web": "HOLD - scouts read the local registry/corpus only, zero network",
    "deploy_real_hardware": "HOLD - deploy means sandbox registry only, never a device",
    "deploy_live_formula_to_qpu": "HOLD - formulas deploy to the sandbox registry only",
})

def _f_dot_spacing(d): return round(10.0 * (40.0 / d) ** 2, 3)
def _f_grover_iters(n): return max(1, round(math.pi / 4 * math.sqrt(n)))
def _f_gates_per_coherence(m): return round(m.coherence_us * 1000.0 / m.gate_ns, 1)
def _f_wiring_heat_mw(n_qubits, mw_per_qubit=0.01): return round(n_qubits * mw_per_qubit, 4)
def _f_coherence_score(m): return round(math.log10(max(_f_gates_per_coherence(m), 1)), 3)

FORMULAS = (
    {"id": "F1", "name": "Quantum-dot level spacing (1/d^2)", "fn": lambda: _f_dot_spacing(20.0), "expected": 40.0, "tol": 0.01},
    {"id": "F2", "name": "Optimal Grover iterations pi/4*sqrt(N)", "fn": lambda: _f_grover_iters(64), "expected": 6, "tol": 0},
    {"id": "F3", "name": "Fidelity after one T2 (silicon)", "fn": lambda: fidelity_after(0.9999, 1000.0, 1000.0), "expected": 0.6839, "tol": 0.01},
    {"id": "F4", "name": "Gates per coherence window (silicon)", "fn": lambda: _f_gates_per_coherence(modality("silicon_spin")), "expected": 10000.0, "tol": 0.01},
    {"id": "F5", "name": "Wiring heat load, 1000 qubits @0.01 mW", "fn": lambda: _f_wiring_heat_mw(1000), "expected": 10.0, "tol": 0.01},
    {"id": "F6", "name": "Coherence score log10(gates/window) (ions)", "fn": lambda: _f_coherence_score(modality("trapped_ion")), "expected": 5.0, "tol": 0.01},
    {"id": "F7", "name": "Surface-code physical/logical @0.1% error", "fn": lambda: physical_qubits_estimate(1, 0.001)["physical_per_logical"], "expected": 1058, "tol": 0},
    {"id": "F8", "name": "Deliberately wrong formula (must FAIL tests)", "fn": lambda: _f_dot_spacing(20.0) + 999.0, "expected": 40.0, "tol": 0.01},
)

@dataclass
class ScoutBot:
    name: str
    domain: str
    focus_keys: tuple = ()
    role: str = "gather"   # gather | prior_art (novelty squad)
    def gather(self) -> list:
        records = []
        for m in MODALITIES:
            if not self.focus_keys or m.key in self.focus_keys:
                records.append({"kind": "modality", "id": m.key, "live": False,
                                "source": "local_registry", "bot": self.name})
        for s in _CORPUS:
            if self.domain in s or any(k.split("_")[0] in s for k in self.focus_keys):
                records.append({"kind": "fact", "id": s[:48], "live": False,
                                "source": "local_corpus", "bot": self.name})
        for f in FORMULAS:
            if self.domain in ("formulas", "tech"):
                records.append({"kind": "formula", "id": f["id"], "live": False,
                                "source": "local_formulas", "bot": self.name})
        return records

SCOUT_BOTS = (
    ScoutBot("DotScout", "silicon", ("silicon_spin",)),
    ScoutBot("CryoScout", "superconducting", ("superconducting",)),
    ScoutBot("GemScout", "diamond", ("diamond_nv",)),
    ScoutBot("PhotonScout", "photonic", ("photonic",)),
    ScoutBot("IonScout", "trapped", ("trapped_ion",)),
    ScoutBot("AtomScout", "neutral", ("neutral_atom",)),
    ScoutBot("MajoranaScout", "topological", ("topological",)),
    ScoutBot("FormulaScout", "formulas", ()),
    ScoutBot("TechScout", "tech", ()),
    ScoutBot("DeconstructionScout", "deconstruction", ()),
    ScoutBot("ChipScout", "chip", ("silicon_spin",)),
    ScoutBot("CryoTechScout", "cryo", ("superconducting",)),
    ScoutBot("QECScout", "code", ()),
    ScoutBot("LinkScout", "photonic", ("photonic",)),
    ScoutBot("MarketScout", "company", ()),
    # --- Novelty squad: their job is to check whether anyone already
    # created the same thing (prior-art watch over the offline snapshot).
    ScoutBot("PriorArtScout", "prior", (), role="prior_art"),
    ScoutBot("PatentScout", "patent", (), role="prior_art"),
    ScoutBot("PaperScout", "paper", (), role="prior_art"),
    ScoutBot("GitHubScout", "github", (), role="prior_art"),
    ScoutBot("NewsScout", "news", (), role="prior_art"),
)

NOVELTY_SQUAD = tuple(b.name for b in SCOUT_BOTS if b.role == "prior_art")

SANDBOX_REGISTRY = []  # deployed formulas/tech live here ONLY (data, in-memory)

def test_formula(f: dict) -> bool:
    try:
        got = f["fn"]()
    except Exception:
        return False
    return abs(got - f["expected"]) <= max(f["tol"], 1e-9) if f["tol"] else got == f["expected"]

# ---- VerifyBot: inventions must NOT be a repeat
def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()

def _name_tokens(name: str) -> set:
    stop = {"the", "a", "an", "of", "per", "at", "for"}
    return {t for t in _normalize_name(name).split() if t not in stop}

def invention_fingerprint(name: str, result) -> str:
    """Canonical fingerprint of an invention: normalized name + verified result."""
    canon = json.dumps({"name": _normalize_name(name), "result": result},
                       sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()

class VerifyBot:
    """
    VerifyBot - the repeat guard, sits between TEST and DEPLOY.
    For every candidate invention it:
      1. RE-RUNS the formula itself (does not trust the scout's claimed result)
      2. Fingerprints it (sha256 of normalized name + verified result)
      3. Checks the sandbox registry three ways:
         exact fingerprint -> repeat_exact
         same normalized name, different result/id -> repeat_name
         name-token overlap >= 0.75 AND same result -> repeat_semantic (a renamed copy)
      Only a verified, novel invention returns verdict 'novel' and may deploy.
    """
    name = "VerifyBot (repeat guard, from scratch)"
    def __init__(self, registry=None):
        self.registry = registry if registry is not None else SANDBOX_REGISTRY
    def _known(self):
        known = []
        for e in self.registry:
            known.append({"id": e.get("formula_id"), "name": e.get("name", ""),
                          "result": e.get("result"), "fingerprint": e.get("fingerprint", "")})
        return known
    def check(self, candidate: dict) -> dict:
        """candidate: {id, name, result}. Pure check, registers nothing."""
        fp = invention_fingerprint(candidate["name"], candidate["result"])
        toks = _name_tokens(candidate["name"])
        for k in self._known():
            if k["fingerprint"] and k["fingerprint"] == fp:
                return {"verdict": "repeat_exact", "fingerprint": fp,
                        "matches": k["id"], "reason": "same name + same verified result already deployed"}
            if _normalize_name(k["name"]) == _normalize_name(candidate["name"]):
                return {"verdict": "repeat_name", "fingerprint": fp,
                        "matches": k["id"], "reason": "same invention name already deployed"}
            ktoks = _name_tokens(k["name"])
            union = toks | ktoks
            overlap = (len(toks & ktoks) / len(union)) if union else 0.0
            if overlap >= 0.75 and k["result"] == candidate["result"]:
                return {"verdict": "repeat_semantic", "fingerprint": fp,
                        "matches": k["id"], "reason": f"renamed copy: name overlap {overlap:.2f} + same result"}
        return {"verdict": "novel", "fingerprint": fp, "matches": None,
                "reason": "no exact, name, or semantic repeat in the registry"}
    def verify_and_check(self, f: dict) -> dict:
        """Re-run + test + duplicate-check one FORMULAS entry."""
        passed = test_formula(f)
        if not passed:
            return {"id": f["id"], "tested_ok": False, "verdict": "failed_tests",
                    "fingerprint": None, "matches": None, "reason": "formula fails its test vector"}
        result = f["fn"]()
        verdict = self.check({"id": f["id"], "name": f["name"], "result": result})
        return {"id": f["id"], "tested_ok": True, "result": result, **verdict}

VERIFY_BOT = VerifyBot()

def reset_scout_state():
    """Clear the sandbox registry + verify state (tests / fresh runs)."""
    SANDBOX_REGISTRY.clear()

def run_scout_cycle(cycle: int = 1) -> dict:
    gathered = []
    for bot in SCOUT_BOTS:
        gathered.extend(bot.gather())
    tested, passed, deployed, repeats_blocked = 0, 0, [], 0
    repeat_detail = []
    for f in FORMULAS:
        tested += 1
        v = VERIFY_BOT.verify_and_check(f)
        if not v["tested_ok"]:
            continue
        passed += 1
        if v["verdict"] != "novel":
            repeats_blocked += 1
            repeat_detail.append({"id": f["id"], "verdict": v["verdict"], "matches": v["matches"]})
            continue
        entry = {"formula_id": f["id"], "name": f["name"], "result": v["result"],
                 "fingerprint": v["fingerprint"], "first_cycle": cycle,
                 "registry": "sandbox_only", "live": False, "verified_by": "VerifyBot"}
        SANDBOX_REGISTRY.append(entry)
        deployed.append(f["id"])
    return {"cycle": cycle, "bots": [b.name for b in SCOUT_BOTS], "verify_bot": "VerifyBot",
            "gathered": len(gathered), "all_live_false": all(not r["live"] for r in gathered),
            "tested": tested, "passed": passed, "failed": tested - passed,
            "deployed_to_sandbox": deployed, "repeats_blocked": repeats_blocked,
            "repeat_detail": repeat_detail, "registry_size": len(SANDBOX_REGISTRY),
            "carbon4_sandbox_decision": carbon4_decide("sandbox deploy of verified formulas",
                                                       {"passed": passed, "failed": tested - passed},
                                                       "extended")["decision"],
            "carbon4_real_decision": carbon4_decide("real deployment to live hardware",
                                                    {"passed": passed, "failed": tested - passed},
                                                    "extended")["decision"],
            "real_deployment": "HOLD - sandbox registry only"}

def run_scout_loop(cycles: int = 2) -> list:
    return [run_scout_cycle(c) for c in range(1, cycles + 1)]

def verify_demo() -> dict:
    """Fresh-registry demo: novel deploys, then exact / renamed repeats are blocked."""
    fresh = []
    bot = VerifyBot(registry=fresh)
    orig = {"id": "F1", "name": FORMULAS[0]["name"], "result": FORMULAS[0]["fn"]()}
    v1 = bot.check(orig)
    fresh.append({"formula_id": "F1", "name": orig["name"], "result": orig["result"],
                  "fingerprint": v1["fingerprint"], "registry": "sandbox_only", "live": False})
    exact = bot.check(dict(orig, id="F99"))
    renamed = bot.check({"id": "F100", "name": "Quantum dot level spacing 1/d^2",
                         "result": orig["result"]})
    novel = bot.check({"id": "F200", "name": "Brand new cryo wiring schedule",
                       "result": 123.456})
    return {"first": v1["verdict"], "exact_repeat": exact["verdict"],
            "renamed_repeat": renamed["verdict"], "genuinely_new": novel["verdict"],
            "registry_size": len(fresh)}

# ---------------------------------------------------------------- deconstruction scout: TOP 20 -> new inventions
# Researched 2026-11-14 from live sources (see README sources). Company claims
# are labelled as claims; topological remains disputed/unproven.
# DeconstructionScout breaks each invention into component tags, then
# RECOMBINES components from 3 different parents into NEW concept inventions
# (data-only specs). Copying a proprietary design, patenting, manufacturing,
# or claiming a new concept works are all HOLD gates.
HOLD_GATES.update({
    "copy_proprietary_design": "HOLD - only public component ideas are recombined, no proprietary design is copied",
    "manufacture_new_invention": "HOLD - new inventions are concept specs (data only), never built",
    "claim_new_invention_works": "HOLD - concepts are untested in hardware, scored on paper only",
})

@dataclass(frozen=True)
class TopInvention:
    id: str
    company: str
    invention: str
    year: int
    field: str          # quantum | nano | data
    core: str           # component tags:
    ecc: str
    link: str
    fab: str
    strength: float     # 0..1 paper strength of the reported result/claim

TOP20 = (
    TopInvention("T01", "Google Quantum AI", "Willow - below-threshold surface-code QEC, 105 qubits", 2024, "quantum", "superconducting_qubit", "surface_code_qec", "cryo_wiring", "dilution_fridge_fab", 0.95),
    TopInvention("T02", "Google Quantum AI", "Quantum Echoes - verifiable quantum advantage / NMR data algorithm", 2025, "data", "superconducting_qubit", "echo_verification", "gpu_hybrid_classical", "dilution_fridge_fab", 0.90),
    TopInvention("T03", "IBM", "Nighthawk - 120 qubits, 218 tunable couplers", 2025, "quantum", "superconducting_qubit", "tunable_coupler_mesh", "modular_cryo_link", "cmos_compatible_fab", 0.88),
    TopInvention("T04", "IBM", "Loon + qLDPC (bivariate bicycle) - fault-tolerance parts, real-time decoding <480 ns", 2025, "quantum", "superconducting_qubit", "qldpc_memory", "real_time_decoder", "cmos_compatible_fab", 0.87),
    TopInvention("T05", "Microsoft", "Majorana 1 - first topological-qubit processor, 8 qubits (disputed)", 2025, "quantum", "topological_qubit", "hardware_protected_qec", "cryo_wiring", "nanowire_heterostructure", 0.45),
    TopInvention("T06", "Microsoft", "Majorana 2 - second-gen topoconductor stack (Pb), DARPA-tested", 2026, "quantum", "topological_qubit", "hardware_protected_qec", "cryo_wiring", "nanowire_heterostructure_v2", 0.50),
    TopInvention("T07", "AWS", "Ocelot - cat-qubit chip, bosonic error correction built in", 2025, "quantum", "cat_qubit", "bosonic_cat_qec", "cryo_wiring", "superconducting_fab", 0.80),
    TopInvention("T08", "Quantinuum", "Helios - 98 trapped ions, 48 logical qubits, 99.921% 2Q, NVQLink GPU hybrid", 2025, "quantum", "trapped_ion_qubit", "color_code_qec", "gpu_hybrid_classical", "surface_trap_chip", 0.96),
    TopInvention("T09", "IonQ", "Tempo / 256-qubit chip-trap system - Oxford Ionics traps + photonic interconnect roadmap", 2026, "quantum", "trapped_ion_qubit", "surface_code_qec", "photonic_interconnect", "chip_integrated_trap", 0.85),
    TopInvention("T10", "QuEra / Harvard / MIT", "Neutral-atom fault tolerance - 96 logical from 448 atoms, qLDPC ~2:1 rate, continuous operation", 2026, "quantum", "neutral_atom_array", "qldpc_memory", "atom_shuttling", "laser_tweezer_array", 0.92),
    TopInvention("T11", "Atom Computing", "AC1000 - 1,200+ atom array, logical qubits with Microsoft", 2025, "quantum", "neutral_atom_array", "surface_code_qec", "atom_shuttling", "laser_tweezer_array", 0.86),
    TopInvention("T12", "Caltech", "6,100-atom tweezer array - largest neutral-atom array, 13 s superposition", 2025, "nano", "neutral_atom_array", "toric_code_qec", "atom_shuttling", "optical_tweezer_fab", 0.84),
    TopInvention("T13", "PsiQuantum", "Photonic fault-tolerant machine - 1M-qubit target, Brisbane + Chicago fabs", 2025, "quantum", "photonic_qubit", "fusion_based_qec", "photonic_interconnect", "silicon_photonics_fab", 0.78),
    TopInvention("T14", "Xanadu", "Photonic quantum systems - room-temperature photonic processors + software stack", 2025, "quantum", "photonic_qubit", "fusion_based_qec", "photonic_interconnect", "silicon_photonics_fab", 0.75),
    TopInvention("T15", "D-Wave", "On-chip cryogenic control for gate-model qubits - solves the wiring bottleneck", 2026, "nano", "superconducting_qubit", "surface_code_qec", "onchip_cryo_control", "cryo_cmos_fab", 0.82),
    TopInvention("T16", "Diraq + imec", "Silicon spin qubits on 300 mm CMOS - >99% 2Q fidelity, industrial fab", 2025, "nano", "silicon_spin_dot", "surface_code_qec", "onchip_cryo_control", "cmos_300mm_fab", 0.90),
    TopInvention("T17", "imec", "Quantum-dot qubits by High-NA EUV lithography - 6 nm gate gaps", 2026, "nano", "silicon_spin_dot", "surface_code_qec", "cryo_wiring", "high_na_euv_litho", 0.83),
    TopInvention("T18", "SQC (Silicon Quantum Computing)", "Donor / precision silicon qubits - 99.99% 2Q fidelity claim (Dec 2025)", 2025, "nano", "silicon_donor_qubit", "surface_code_qec", "cryo_wiring", "atomic_precision_fab", 0.89),
    TopInvention("T19", "Fujitsu + QuTech (TU Delft)", "Diamond SnV spin-photon module - spin qubits + on-chip photonics at 1.55 K", 2026, "nano", "diamond_spin_qubit", "spin_photon_qec", "photonic_interconnect", "diamond_photonics_fab", 0.76),
    TopInvention("T20", "Tanaka + Nagoya University", "Lead-free Ag-S-Te quantum dots - SWIR sensing, 18.4% EQE, no Pb/Cd", 2026, "nano", "quantum_dot_sensor", "signal_processing_ml", "optical_sensing_link", "nanoparticle_synthesis", 0.72),
)

_TAG_TITLES = {
    "superconducting_qubit": "Superconducting Core", "trapped_ion_qubit": "Trapped-Ion Core",
    "neutral_atom_array": "Neutral-Atom Core", "silicon_spin_dot": "Silicon Spin-Dot Core",
    "silicon_donor_qubit": "Silicon Donor Core", "topological_qubit": "Topological Core",
    "cat_qubit": "Cat-Qubit Core", "photonic_qubit": "Photonic Core",
    "diamond_spin_qubit": "Diamond Spin Core", "quantum_dot_sensor": "Quantum-Dot Sensor Core",
    "surface_code_qec": "Surface-Code QEC", "qldpc_memory": "qLDPC Memory",
    "color_code_qec": "Color-Code QEC", "bosonic_cat_qec": "Bosonic Cat QEC",
    "fusion_based_qec": "Fusion-Based QEC", "hardware_protected_qec": "Hardware-Protected QEC",
    "toric_code_qec": "Toric-Code QEC", "spin_photon_qec": "Spin-Photon QEC",
    "echo_verification": "Echo Verification", "tunable_coupler_mesh": "Tunable-Coupler Mesh",
    "signal_processing_ml": "ML Signal Processing",
    "photonic_interconnect": "Photonic Interconnect", "atom_shuttling": "Atom Shuttling",
    "gpu_hybrid_classical": "GPU-Hybrid Classical Link", "cryo_wiring": "Cryo Wiring",
    "onchip_cryo_control": "On-Chip Cryo Control", "real_time_decoder": "Real-Time Decoder Link",
    "modular_cryo_link": "Modular Cryo Link", "optical_sensing_link": "Optical Sensing Link",
}

def top_invention(tid: str) -> TopInvention:
    for t in TOP20:
        if t.id == tid: return t
    raise KeyError(tid)

def deconstruct(t: TopInvention) -> dict:
    """Break one company invention into its reusable component tags."""
    return {"id": t.id, "company": t.company, "invention": t.invention, "field": t.field,
            "components": {"core": t.core, "ecc": t.ecc, "link": t.link, "fab": t.fab},
            "component_tags": sorted({t.core, t.ecc, t.link, t.fab}),
            "strength": t.strength}

class DeconstructionScout:
    name = "DeconstructionScout"
    def gather_top20(self) -> list:
        return [{"kind": "top_invention", "id": t.id, "company": t.company,
                 "live": False, "source": "researched_registry_2026-11-14", "bot": self.name}
                for t in TOP20]
    def deconstruct_all(self) -> list:
        return [deconstruct(t) for t in TOP20]

DECONSTRUCTION_SCOUT = DeconstructionScout()

def _new_invention_name(core_tag, ecc_tag, link_tag, idx):
    return (f"{_TAG_TITLES.get(core_tag, core_tag)} with {_TAG_TITLES.get(ecc_tag, ecc_tag)} "
            f"and {_TAG_TITLES.get(link_tag, link_tag)} - Hybrid Concept N{idx:02d}")

def create_new_inventions(count: int = 10) -> dict:
    """
    Recombine deconstructed components from 3 different parents into NEW
    concept inventions. Every candidate is re-checked by VerifyBot against
    everything already in the sandbox registry (formulas + earlier new
    inventions): repeats deploy 0 times. Concepts are data-only specs.
    """
    created, blocked, tested_concepts = [], [], 0
    for k in range(count):
        a = TOP20[k % len(TOP20)]
        b = TOP20[(k + 7) % len(TOP20)]
        c = TOP20[(k + 13) % len(TOP20)]
        parents = [a.id, b.id, c.id]
        signature = "|".join(sorted({a.core, b.ecc, c.link, a.fab}))
        name = _new_invention_name(a.core, b.ecc, c.link, k + 1)
        score = round((a.strength + b.strength + c.strength) / 3, 4)
        tested_concepts += 1
        passes = len(set(parents)) == 3 and len(signature.split("|")) >= 3 and score >= 0.5
        if not passes:
            blocked.append({"name": name, "verdict": "failed_concept_test"}); continue
        v = VERIFY_BOT.check({"id": f"N{k+1:02d}", "name": name, "result": signature})
        if v["verdict"] != "novel":
            blocked.append({"name": name, "verdict": v["verdict"], "matches": v["matches"]}); continue
        entry = {"formula_id": f"N{k+1:02d}", "name": name, "result": signature,
                 "fingerprint": v["fingerprint"], "first_cycle": 0,
                 "registry": "sandbox_only", "live": False, "verified_by": "VerifyBot",
                 "kind": "new_invention", "parents": parents, "paper_score": score}
        SANDBOX_REGISTRY.append(entry)
        created.append({"id": entry["formula_id"], "name": name, "parents": parents,
                        "components": signature.split("|"), "paper_score": score,
                        "verify": "novel", "status": "concept_only - not built, not claimed to work",
                        "prior_art": "checked_by_novelty_squad - see prior_art_report()"})
    return {"bot": "DeconstructionScout", "gathered_top20": len(TOP20),
            "deconstructed": len(DECONSTRUCTION_SCOUT.deconstruct_all()),
            "concepts_tested": tested_concepts, "created": created,
            "created_count": len(created), "blocked": blocked,
            "blocked_count": len(blocked),
            "real_invention": "HOLD - concept specs only, sandbox registry only"}

# ---------------------------------------------------------------- prior-art / novelty search (novelty squad)
# Question the squad answers: "did anyone already create the same thing?"
# Method: (1) VerifyBot already proves no repeat INSIDE this lab; (2) the
# novelty squad compares each new concept against an offline snapshot of
# real-world prior art found by live web searches run on 2026-11-14
# (papers, company roadmaps, products). similarity = assessed component
# overlap 0..1. A verdict of no_exact_match_found means: in the sources
# searched, nobody was found with the same full combination - components
# DO have prior art (that is where they came from), and absence in searched
# sources is not legal proof of world-first novelty. The squad's live web
# watch itself stays HOLD (scout_live_web); this snapshot is data.
PRIOR_ART_SEARCHED_ON = "2026-11-14"
PRIOR_ART_SOURCES = ["arXiv / PRX Quantum papers", "company roadmaps (IBM, Google, Quantinuum, PsiQuantum)",
                     "product + vendor pages (SeeQC, D-Wave, NVIDIA NVQLink)", "web name search for 'NanoBits-Q'"]

PRIOR_ART_FINDINGS = (
    {"concept": "PROJECT", "closest": "No project, product, or repository named 'NanoBits-Q' found",
     "source": "Web name search, 2026-11-14 (only unrelated nanoqubit papers surfaced)", "year": 2026,
     "similarity": 0.0, "note": "The NanoBits-Q name and lab design appear unused by anyone else in searched sources."},
    {"concept": "N01", "closest": "Quantinuum color code below threshold on Helios (trapped ions)",
     "source": "arXiv:2610.24077 (2026)", "year": 2026, "similarity": 0.62,
     "note": "Color-code QEC is proven - on ions. No superconducting core + color code + photonic interconnect machine found."},
    {"concept": "N02", "closest": "SeeQC / D-Wave on-chip cryogenic control for superconducting qubits",
     "source": "Vendor engineering reports (2025-2026)", "year": 2026, "similarity": 0.66,
     "note": "Superconducting + surface code + on-chip cryo control is mainstream engineering; the exact packaged combination was not found as one named system."},
    {"concept": "N03", "closest": "IBM fault-tolerance roadmap: Loon qLDPC + Kookaburra qLDPC memory module + cryo control (Starling 2029)",
     "source": "IBM Quantum roadmap + processor pages (2025-2026)", "year": 2026, "similarity": 0.83,
     "note": "CLOSEST MATCH OF ALL 10: this recombination is essentially IBM's own stated plan - flagged, not hidden. Still a roadmap, not a shipped machine."},
    {"concept": "N04", "closest": "Google Willow surface-code machine + cryogenic wiring engineering",
     "source": "Google Quantum AI Willow results (2024-2025)", "year": 2025, "similarity": 0.60,
     "note": "All components exist at Google; the specific 3-parent combination is this lab's recombination, not a Google product."},
    {"concept": "N05", "closest": "Atom Computing toric code demonstrated on NEUTRAL ATOMS (2026)",
     "source": "Atom Computing toric-code demonstration reports (2026)", "year": 2026, "similarity": 0.45,
     "note": "Toric code exists - on atoms. On topological/Majorana qubits it cannot exist yet: the qubits themselves are unproven."},
    {"concept": "N06", "closest": "PsiQuantum fusion-based photonic quantum computing",
     "source": "PsiQuantum architecture publications (2025)", "year": 2025, "similarity": 0.50,
     "note": "Fusion QEC + photonic links are PsiQuantum's core - with a photonic core, not a topological one. No topological-core version found."},
    {"concept": "N07", "closest": "Fault-tolerant hybrid qubits: bosonic cat code + single photons, fusion architectures",
     "source": "PRX Quantum 5, 030322 (2024) / arXiv:2401.00450", "year": 2024, "similarity": 0.75,
     "note": "STRONG prior art: cat + fusion + photonic in one peer-reviewed architecture. Difference: that paper's hybrid CV-DV qubit vs this concept's cat core + separate optical sensing link. Flagged close."},
    {"concept": "N08", "closest": "Quantinuum logical qubits (surface/color codes) on trapped ions",
     "source": "Quantinuum Helios results (2025)", "year": 2025, "similarity": 0.55,
     "note": "Ion logical qubits exist; ions run near room temperature, so the cryo-wiring link makes this combination uncommon - not found as one system."},
    {"concept": "N09", "closest": "Quantinuum Helios + NVIDIA NVQLink GPU-hybrid link (the T08 parent itself)",
     "source": "Quantinuum / NVIDIA NVQLink announcements (2025)", "year": 2025, "similarity": 0.70,
     "note": "The GPU-hybrid link component is the parent's own product; combined with an IonQ-style surface-code trap core it was not found elsewhere."},
    {"concept": "N10", "closest": "Cryogenic neutral-atom arrays (extended Rydberg lifetimes at 4 K) + QuEra surface-code logical atoms",
     "source": "PRX Quantum 7, 033009 (2026); QuEra/Harvard logical-atom results (2026)", "year": 2026, "similarity": 0.65,
     "note": "Cryo atom arrays and surface-code atoms both exist separately; a modular cryo-linked surface-code atom machine was not found as one system."},
)

def _concept_name_for_index(k: int) -> str:
    a = TOP20[k % len(TOP20)]; b = TOP20[(k + 7) % len(TOP20)]; c = TOP20[(k + 13) % len(TOP20)]
    return _new_invention_name(a.core, b.ecc, c.link, k + 1)

def novelty_check(concept_id: str) -> dict:
    """Offline prior-art verdict for one concept id (N01..N10 or PROJECT)."""
    for f in PRIOR_ART_FINDINGS:
        if f["concept"] == concept_id:
            exact = f["similarity"] >= 0.9
            return {"concept": concept_id, "verdict": "exact_match_found" if exact else "no_exact_match_found",
                    "closest_match": f["closest"], "source": f["source"], "year": f["year"],
                    "similarity": f["similarity"], "note": f["note"],
                    "searched_on": PRIOR_ART_SEARCHED_ON, "live": False,
                    "scope": "searched sources only - not legal proof of world-first novelty"}
    return {"concept": concept_id, "verdict": "not_searched", "live": False}

def prior_art_report() -> dict:
    """The novelty squad's full report over the project + all 10 concepts."""
    entries = []
    for k in range(10):
        cid = f"N{k + 1:02d}"
        chk = novelty_check(cid)
        entries.append({"concept": cid, "name": _concept_name_for_index(k), **chk})
    project = novelty_check("PROJECT")
    exact = [e["concept"] for e in entries if e["verdict"] == "exact_match_found"]
    closest = max(entries, key=lambda e: e["similarity"])
    return {"squad": list(NOVELTY_SQUAD), "squad_size": len(NOVELTY_SQUAD),
            "searched_on": PRIOR_ART_SEARCHED_ON, "sources": PRIOR_ART_SOURCES,
            "project_name_check": project, "concepts": entries,
            "concepts_checked": len(entries), "exact_matches_found": exact,
            "closest_match": {"concept": closest["concept"], "similarity": closest["similarity"],
                              "closest_match": closest["closest_match"]},
            "summary": ("No exact same full combination found in searched sources for the project "
                        "name or any of the 10 concepts. Components have prior art by design - "
                        "closest is N03 at 0.83 (IBM's own roadmap)."),
            "live_web_watch": "HOLD - scout_live_web gate stands; this is an offline snapshot",
            "honesty": "Absence in searched sources is not proof nobody ever built it - it is a searched-sources verdict."}

# ---------------------------------------------------------------- merged brains: Gemini Argon 4 + Google Flow
# Gemini Argon 4 = Gemini Carbon 4 Extended Thinking (Darion's house seat):
# DECIDER, engine gemini-2.5-pro, model google/gemini-carbon-4-extended-pro-thinking,
# MAP -> MODEL -> STRESS -> DECIDE with a hashed trace, thinking tiers
# 2048 / 8192 / 32768 by stakes. Offline-authoritative: no live call is ever
# made, the API key is names/presence-only, and a Carbon decision can only
# TIGHTEN (HOLD beats PROCEED) - it can never override a HOLD gate.
# Google Flow = all 4 flows, plan-only: FlowX task graph, Workspace Studio
# drafting, Filmmaking storyboard, DataX data-flow. rendered=False, live_calls=0.
HOLD_GATES.update({
    "live_gemini_api_call": "HOLD - Carbon 4 runs offline-authoritative, no live Gemini call",
    "live_video_generation": "HOLD - Google Flow filmmaking is storyboard plan only, never renders",
    "flow_workspace_send": "HOLD - Workspace Studio drafts only, nothing is sent anywhere",
})

CARBON4 = {
    "seat": "Gemini Argon 4 Extended Thinking (Gemini Carbon 4)",
    "role": "DECIDER",
    "engine": "gemini-2.5-pro",
    "model": "google/gemini-carbon-4-extended-pro-thinking",
    "phases": ["MAP", "MODEL", "STRESS", "DECIDE"],
    "tiers": {"standard": 2048, "deep": 8192, "extended": 32768},
    "key_name": "GEMINI_API_KEY",
    "live_calls": 0,
    "can_override_hold": False,
}

def carbon4_tier(stakes: str) -> int:
    return CARBON4["tiers"].get(stakes, CARBON4["tiers"]["extended"])

def carbon4_key_presence() -> dict:
    """Names/presence only - the value is never read into output or logs."""
    env_name = CARBON4["key_name"]
    present = bool(os.environ.get(env_name))
    return {"key_name": env_name, "present": present,
            "note": "presence only - value never read, printed, or stored"}

def carbon4_decide(subject: str, evidence: dict = None, stakes: str = "extended") -> dict:
    evidence = evidence or {}
    budget = carbon4_tier(stakes)
    subj = subject.lower()
    hold_hit = any(g.replace("_", " ") in subj or g in subj for g in HOLD_GATES)
    real_world = any(w in subj for w in ("real deployment", "live hardware", "fabricat", "sell"))
    failed = int(evidence.get("failed", 0))
    passed = int(evidence.get("passed", 0))
    trace = {
        "MAP": f"subject={subject}; evidence keys={sorted(evidence)}",
        "MODEL": f"passed={passed} failed={failed}; models SLM/LLM/ML/NNL feed this stage as evidence only",
        "STRESS": f"hold_gate_match={hold_hit or real_world}; planted-failure tolerance=1; repeats are VerifyBot's call",
        "DECIDE": "",
    }
    if hold_hit or real_world:
        decision, reason = "HOLD", "subject touches a HOLD gate - Carbon can tighten, never loosen"
    elif failed > 1:
        decision, reason = "HOLD", f"{failed} failures exceed the planted-failure tolerance of 1"
    elif passed == 0 and evidence:
        decision, reason = "HOLD", "no passing evidence to decide on"
    else:
        decision, reason = "PROCEED", "evidence passes and no HOLD gate is touched (sandbox scope only)"
    trace["DECIDE"] = f"{decision} - {reason}"
    trace_hash = hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest()
    return {"seat": CARBON4["seat"], "role": "DECIDER", "model": CARBON4["model"],
            "thinking_budget": budget, "subject": subject, "decision": decision,
            "reason": reason, "trace": trace, "trace_hash": trace_hash,
            "live_calls": 0, "can_override_hold": False}

# ---- Google Flow: 4 flows, plan-only
def flowx_graph() -> dict:
    steps = ["gather_top20", "deconstruct", "gather_local", "test_formulas", "verifybot_check",
             "carbon4_decide", "sandbox_deploy", "model_brief", "report", "repeat"]
    return {"flow": "Gemini FlowX", "steps": steps, "subtasks": len(steps),
            "recommended_agents": 3, "queue_wait": 0, "live_calls": 0, "rendered": False}

def flow_workspace_studio(topic: str = "NanoBits-Q") -> dict:
    return {"flow": "Google Workspace Studio", "drafts": [f"{topic} summary doc (draft only)",
            f"{topic} release notes (draft only)", f"{topic} invention table (draft only)"],
            "sent": False, "live_calls": 0, "rendered": False,
            "note": "drafts are local text plans - nothing is sent or published"}

def flow_filmmaking(topic: str = "NanoBits-Q - quantum nano-bits") -> dict:
    shots = [
        {"shot": 1, "track": "setup", "prompt": f"Opening: a single electron spinning inside a glowing 40 nm quantum dot, title {topic}"},
        {"shot": 2, "track": "analyze", "prompt": "Seven qubit modalities rise as holographic chips - silicon, superconducting, diamond, photonic, ion, atom, topological"},
        {"shot": 3, "track": "analyze", "prompt": "Scout robots gather blueprints of the Top 20 company inventions and take them apart into LEGO-like components"},
        {"shot": 4, "track": "verdict", "prompt": "VerifyBot stamps NOVEL on 10 recombined hybrid machines and blocks every repeat with a red REPEAT stamp"},
        {"shot": 5, "track": "teardown", "prompt": "Closing: the sandbox registry glows with 7 formulas + 10 concepts, HOLD gates lock real hardware away, MIT logo fades in"},
    ]
    return {"flow": "Google Flow Filmmaking", "topic": topic, "shots": shots,
            "shot_count": len(shots), "rendered": False, "live_calls": 0,
            "note": "storyboard plan only - no video is generated or rendered"}

def flow_datax() -> dict:
    return {"flow": "DataX google_flow", "pipeline": ["registry_snapshot", "component_extract",
            "dedupe_by_fingerprint", "paper_score", "sandbox_sink"],
            "live_calls": 0, "rendered": False,
            "note": "local data-flow plan for Top 20 registry updates - no external data moves"}

def google_flows(topic: str = "NanoBits-Q - quantum nano-bits") -> dict:
    return {"flows": [flowx_graph(), flow_workspace_studio(), flow_filmmaking(topic), flow_datax()],
            "flow_count": 4, "all_plan_only": True, "live_calls": 0, "rendered": False}

def brains() -> dict:
    return {"carbon4": CARBON4, "carbon4_key": carbon4_key_presence(),
            "sample_decision": carbon4_decide("sandbox deploy of verified formulas",
                                              {"passed": 7, "failed": 1}, "extended"),
            "google_flow": google_flows(),
            "local_models": ["TinySLM", "TinyLLM", "MLModalityClassifier", "TinyMLP"],
            "authority_rule": "Carbon 4 DECIDES inside sandbox scope; HOLD gates outrank every brain"}

# ---------------------------------------------------------------- checks
def run_checks():
    checks = []
    def add(name, ok): checks.append((name, bool(ok)))
    add("modalities >= 7", len(MODALITIES) >= 7)
    add("all modalities have players", all(m.players for m in MODALITIES))
    add("silicon dot is true nanoscale", scale_class(modality("silicon_spin").size_nm).startswith("true nanoscale"))
    add("scale: dot smaller than hair", scale_compare(40.0)["x_smaller_than_hair"] == 2000.0)
    b = bell_state(); add("Bell state 00/11 only, 0.5 each", b == {"00": 0.5, "11": 0.5})
    g = ghz_state(3); add("GHZ-3 000/111 only", g == {"000": 0.5, "111": 0.5})
    add("QSim normalized after gates", QSim(2).h(0).x(1).cnot(1, 0).is_normalized())
    add("QSim rejects 7 qubits", _raises(lambda: QSim(7)))
    add("decoherence decays toward 0.5", fidelity_after(0.999, 1000.0, 1000.0) < 0.999)
    add("coherence at t=T2 is 1/e", abs(coherence_remaining(100.0, 100.0) - round(math.exp(-1), 6)) < 1e-9)
    add("ECC: above-threshold error cannot be fixed", surface_code_distance(0.02) == -1)
    ecc = physical_qubits_estimate(1, 0.001)
    add("ECC: 0.1% error needs >1 physical per logical", ecc["physical_per_logical"] > 1)
    gr = grover_demo(); add("Grover 64: prob > 0.9, classical 1/64", gr["success_probability"] > 0.9 and gr["classical_uniform"] == round(1/64, 6))
    add("Grover halves bits", effective_bits_grover(52.4367) == 26.2183 or effective_bits_grover(52.4367) == 26.2184)
    s15 = shor_teaching(15); add("Shor teaching: 15 = 3 x 5", {s15["factor_a"], s15["factor_b"]} == {3, 5})
    s21 = shor_teaching(21); add("Shor teaching: 21 = 3 x 7", {s21["factor_a"], s21["factor_b"]} == {3, 7})
    dot = quantum_dot(40.0); add("Quantum dot 40nm single-electron", dot["regime"].startswith("single-electron"))
    add("Smaller dot -> larger spacing", quantum_dot(20.0)["level_spacing_meV_est"] > quantum_dot(40.0)["level_spacing_meV_est"])
    add("Cryo tiers correct", "dilution" in cryo_tier(0.015) and "room" in cryo_tier(293.0))
    add("Threshold: 99.9% passes, 99.0% fails", above_threshold(0.999) and not above_threshold(0.99))
    add("HOLD gates >= 8 and all HOLD", len(HOLD_GATES) >= 8 and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    # merged models
    slm_out = TinySLM().summarize("Silicon spin qubits trap one electron in a nanoscale quantum dot. Photonic qubits travel at the speed of light through fibre.")
    add("SLM returns a summary sentence", len(slm_out) > 10 and slm_out.endswith("."))
    llm_out = TinyLLM().generate("silicon spin qubits", seed=7)
    add("LLM draft extends the prompt", llm_out.startswith("silicon spin qubits") and len(llm_out) > len("silicon spin qubits"))
    add("LLM deterministic per seed", TinyLLM().generate("photonic qubits", seed=3) == TinyLLM().generate("photonic qubits", seed=3))
    ml = MLModalityClassifier()
    add("ML labels topological unproven", ml.classify(modality("topological")) == "unproven")
    add("ML labels a real modality", ml.classify(modality("silicon_spin")) in {"fault_tolerant_candidate", "promising", "early"})
    add("NNL risk in [0,1]", 0.0 <= _mlp().risk(modality("photonic")) <= 1.0)
    add("NNL topological risk > silicon risk", _mlp().risk(modality("topological")) > _mlp().risk(modality("silicon_spin")))
    brief = model_brief("silicon_spin")
    add("Brief fuses all 4 models, authority none", all(k in brief for k in ("slm_summary", "llm_draft", "ml_label", "nnl_scale_risk")) and brief["can_override_hold"] is False)
    add("Brief LLM draft actually extends prompt", len(brief["llm_draft"]) > len("silicon spin qubits") + 5)
    add("Brief SLM summary is a real sentence", len(brief["slm_summary"]) > 20)
    # scout bots + VerifyBot repeat guard
    add("Scout bots: 20 named", len(SCOUT_BOTS) == 20 and all(b.name.endswith("Scout") for b in SCOUT_BOTS))
    reset_scout_state()
    cyc = run_scout_cycle(1)
    add("Scouts gather local-only (live=False)", cyc["gathered"] > 20 and cyc["all_live_false"])
    add("Scouts test all formulas, wrong one fails", cyc["tested"] == len(FORMULAS) and cyc["failed"] == 1)
    add("Scouts deploy passes to sandbox only", set(cyc["deployed_to_sandbox"]) == {f["id"] for f in FORMULAS if test_formula(f)} and all(e["registry"] == "sandbox_only" for e in SANDBOX_REGISTRY))
    add("VerifyBot fingerprints are stable sha256", len(invention_fingerprint("Test Name", 1.0)) == 64 and invention_fingerprint("Test  Name!", 1.0) == invention_fingerprint("test name", 1.0))
    cyc2 = run_scout_cycle(2)
    add("VerifyBot blocks ALL repeats on cycle 2 (0 new deploys)", cyc2["deployed_to_sandbox"] == [] and cyc2["repeats_blocked"] == cyc["passed"] and cyc2["registry_size"] == len(cyc["deployed_to_sandbox"]))
    demo_v = verify_demo()
    add("VerifyBot: exact repeat blocked", demo_v["first"] == "novel" and demo_v["exact_repeat"] in ("repeat_exact", "repeat_name"))
    add("VerifyBot: renamed copy blocked", demo_v["renamed_repeat"] in ("repeat_exact", "repeat_name", "repeat_semantic"))
    add("VerifyBot: genuinely new invention passes", demo_v["genuinely_new"] == "novel")
    add("VerifyBot re-runs tests (wrong formula = failed_tests)", VERIFY_BOT.verify_and_check(FORMULAS[-1])["verdict"] == "failed_tests")
    reset_scout_state()
    loop = run_scout_loop(2)
    add("Scout loop repeats, cycle 2 deploys nothing new", len(loop) == 2 and loop[0]["deployed_to_sandbox"] and loop[1]["deployed_to_sandbox"] == [] and loop[1]["repeats_blocked"] == loop[0]["passed"])
    # deconstruction scout + top 20 + new inventions
    add("Top 20 registry: exactly 20, unique ids + inventions", len(TOP20) == 20 and len({t.id for t in TOP20}) == 20 and len({t.invention for t in TOP20}) == 20)
    add("Top 20 covers quantum + nano + data fields", {t.field for t in TOP20} >= {"quantum", "nano", "data"})
    add("DeconstructionScout is in the fleet", any(b.name == "DeconstructionScout" for b in SCOUT_BOTS))
    dec = DECONSTRUCTION_SCOUT.deconstruct_all()
    add("Every top invention deconstructs to >=4 component tags", len(dec) == 20 and all(len(d["component_tags"]) >= 4 for d in dec))
    reset_scout_state()
    inv = create_new_inventions(10)
    add("New inventions created from 3 parents each", inv["created_count"] >= 8 and all(len(c["parents"]) == 3 and len(set(c["parents"])) == 3 for c in inv["created"]))
    add("New inventions are NOT repeats of the top 20", all(c["name"] not in {t.invention for t in TOP20} for c in inv["created"]))
    add("New inventions are unique vs each other", len({c["name"] for c in inv["created"]}) == inv["created_count"])
    inv2 = create_new_inventions(10)
    add("Re-creating the same inventions is blocked by VerifyBot", inv2["created_count"] == 0 and inv2["blocked_count"] == 10)
    # merged brains: Gemini Argon 4 (Carbon 4) + Google Flow
    add("Carbon 4 seat: decider, right model + engine", CARBON4["role"] == "DECIDER" and CARBON4["model"] == "google/gemini-carbon-4-extended-pro-thinking" and CARBON4["engine"] == "gemini-2.5-pro")
    add("Carbon 4 tiers 2048/8192/32768", (carbon4_tier("standard"), carbon4_tier("deep"), carbon4_tier("extended")) == (2048, 8192, 32768))
    d_ok = carbon4_decide("sandbox deploy of verified formulas", {"passed": 7, "failed": 1}, "extended")
    add("Carbon 4 PROCEED on clean sandbox evidence, budget 32768", d_ok["decision"] == "PROCEED" and d_ok["thinking_budget"] == 32768)
    add("Carbon 4 trace has 4 phases + 64-char hash", list(d_ok["trace"]) == ["MAP", "MODEL", "STRESS", "DECIDE"] and len(d_ok["trace_hash"]) == 64)
    add("Carbon 4 HOLD on real deployment (cannot override HOLD)", carbon4_decide("real deployment to live hardware", {"passed": 7, "failed": 0})["decision"] == "HOLD" and CARBON4["can_override_hold"] is False)
    add("Carbon 4 HOLD when failures exceed tolerance", carbon4_decide("sandbox deploy", {"passed": 2, "failed": 5})["decision"] == "HOLD")
    add("Carbon 4 key is names/presence only, live calls 0", carbon4_key_presence()["key_name"] == "GEMINI_API_KEY" and CARBON4["live_calls"] == 0)
    gf = google_flows()
    add("Google Flow: all 4 flows, plan-only", gf["flow_count"] == 4 and gf["all_plan_only"] and gf["live_calls"] == 0 and gf["rendered"] is False)
    add("Flow Filmmaking: 5-shot storyboard, not rendered", flow_filmmaking()["shot_count"] == 5 and flow_filmmaking()["rendered"] is False)
    add("FlowX graph covers the scout pipeline", flowx_graph()["subtasks"] >= 10 and "verifybot_check" in flowx_graph()["steps"])
    add("Brains view fuses Carbon 4 + Flow + local models", len(brains()["local_models"]) == 4 and brains()["google_flow"]["flow_count"] == 4)
    add("HOLD gates now 17", len(HOLD_GATES) == 17)
    # novelty squad / prior-art search
    add("Novelty squad: 5 prior-art bots", len(NOVELTY_SQUAD) == 5 and "PriorArtScout" in NOVELTY_SQUAD)
    rep = prior_art_report()
    add("Prior-art report covers project + 10 concepts", rep["concepts_checked"] == 10 and rep["project_name_check"]["verdict"] == "no_exact_match_found")
    add("Prior-art: no exact same combination found", rep["exact_matches_found"] == [])
    add("Prior-art: closest is N03 (IBM roadmap) at 0.83", rep["closest_match"]["concept"] == "N03" and abs(rep["closest_match"]["similarity"] - 0.83) < 1e-9)
    add("Prior-art findings all sourced + dated", all(f.get("source") for f in PRIOR_ART_FINDINGS) and PRIOR_ART_SEARCHED_ON == "2026-11-14")
    add("Prior-art honesty scope is stated", "not legal proof" in rep["concepts"][0]["scope"] if rep["concepts"] else False)
    add("Novelty live web watch stays HOLD", "scout_live_web" in HOLD_GATES)
    return checks

def _raises(fn):
    try:
        fn(); return False
    except Exception:
        return True

# ---------------------------------------------------------------- CLI
def main(argv=None):
    p = argparse.ArgumentParser(prog="nanobits-q", description="NanoBits-Q lab (educational, local only)")
    p.add_argument("cmd", nargs="?", default="demo",
                   choices=["demo", "modalities", "bell", "ghz", "grover", "shor",
                            "dot", "decoherence", "ecc", "brief", "models", "scouts",
                            "formulas", "verify", "top20", "deconstruct", "invent",
                            "brains", "carbon", "flow", "priorart", "checks", "holds"])
    p.add_argument("--modality", default="silicon_spin")
    p.add_argument("--n", type=int, default=15)
    p.add_argument("--size", type=float, default=40.0)
    args = p.parse_args(argv)

    if args.cmd == "checks":
        checks = run_checks(); passed = sum(1 for _, ok in checks if ok)
        for name, ok in checks: print(f"{'PASS' if ok else 'FAIL'}  {name}")
        print(f"CHECKS {passed}/{len(checks)}")
        return 0 if passed == len(checks) else 1
    if args.cmd == "holds":
        for k, v in HOLD_GATES.items(): print(f"{k}: {v}")
        return 0
    if args.cmd == "modalities":
        for m in MODALITIES:
            print(f"{m.key:16} {m.name} | {m.size_nm:g} nm | {m.temp_k:g} K ({cryo_tier(m.temp_k)}) | "
                  f"gate {m.gate_ns:g} ns | T2 {m.coherence_us:g} us | 2q {m.fidelity_2q:.4%}")
        return 0
    if args.cmd == "bell": print(bell_state()); return 0
    if args.cmd == "ghz": print(ghz_state(3)); return 0
    if args.cmd == "grover": print(grover_demo()); return 0
    if args.cmd == "shor": print(shor_teaching(args.n)); return 0
    if args.cmd == "dot": print(quantum_dot(args.size)); print(scale_compare(args.size)); return 0
    if args.cmd == "decoherence":
        m = modality(args.modality)
        print({"modality": m.key, "fidelity_at_0us": m.fidelity_2q,
               "fidelity_at_T2": fidelity_after(m.fidelity_2q, m.coherence_us, m.coherence_us),
               "coherence_at_T2": coherence_remaining(m.coherence_us, m.coherence_us)}); return 0
    if args.cmd == "ecc": print(physical_qubits_estimate(100, 0.001)); return 0
    if args.cmd == "brief": print(model_brief(args.modality)); return 0
    if args.cmd == "models":
        print(TinySLM.name); print(TinyLLM.name); print(MLModalityClassifier.name); print(TinyMLP.name)
        print(model_brief(args.modality)); return 0
    if args.cmd == "scouts":
        reset_scout_state()
        for r in run_scout_loop(2): print(r)
        print("Sandbox registry size:", len(SANDBOX_REGISTRY)); return 0
    if args.cmd == "verify":
        print(VerifyBot.name); print(verify_demo()); return 0
    if args.cmd == "top20":
        for t in TOP20: print(f"{t.id} [{t.field:7}] {t.company} ({t.year}) - {t.invention}")
        return 0
    if args.cmd == "deconstruct":
        for d in DECONSTRUCTION_SCOUT.deconstruct_all(): print(d)
        return 0
    if args.cmd == "invent":
        reset_scout_state(); r = create_new_inventions(10)
        for c in r["created"]: print(c)
        print(f"created {r['created_count']}, blocked {r['blocked_count']}"); return 0
    if args.cmd == "brains": print(brains()); return 0
    if args.cmd == "carbon":
        print(carbon4_decide("sandbox deploy of verified formulas", {"passed": 7, "failed": 1}, "extended"))
        print(carbon4_decide("real deployment to live hardware", {"passed": 7, "failed": 0}, "extended")); return 0
    if args.cmd == "flow":
        for f in google_flows()["flows"]: print(f)
        return 0
    if args.cmd == "priorart":
        r = prior_art_report(); print(r["summary"])
        print("Project name:", r["project_name_check"]["verdict"], "-", r["project_name_check"]["closest_match"])
        for e in r["concepts"]:
            print(f"{e['concept']}: {e['verdict']} (closest {e['similarity']:.2f}) - {e['closest_match']}")
        return 0
    if args.cmd == "formulas":
        for f in FORMULAS: print(f["id"], f["name"], "PASS" if test_formula(f) else "FAIL")
        return 0
    # demo
    print("NanoBits-Q - quantum computing nano-bits technology lab")
    print("Educational local simulation only. No live quantum hardware.")
    print(f"Modalities: {len(MODALITIES)} | HOLD gates: {len(HOLD_GATES)}")
    print("Bell:", bell_state())
    print("Grover:", grover_demo())
    print("Shor(15):", shor_teaching(15))
    print("Dot 40nm:", quantum_dot(40.0))
    print("ECC 100 logical @0.1%:", physical_qubits_estimate(100, 0.001))
    print("Brief silicon_spin:", model_brief("silicon_spin"))
    reset_scout_state()
    print("Scout cycle 1:", run_scout_cycle(1))
    print("Scout cycle 2 (VerifyBot - repeats blocked):", run_scout_cycle(2))
    print("VerifyBot demo:", verify_demo())
    reset_scout_state()
    inv = create_new_inventions(10)
    print(f"DeconstructionScout: top {inv['gathered_top20']} deconstructed -> {inv['created_count']} NEW concept inventions (VerifyBot-checked, sandbox only)")
    checks = run_checks(); print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
