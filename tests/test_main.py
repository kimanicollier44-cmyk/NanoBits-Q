import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main as nb

def test_modalities_count(): assert len(nb.MODALITIES) >= 7
def test_silicon_nanoscale(): assert nb.scale_class(40.0).startswith("true nanoscale")
def test_bell(): assert nb.bell_state() == {"00": 0.5, "11": 0.5}
def test_ghz(): assert nb.ghz_state(3) == {"000": 0.5, "111": 0.5}
def test_qsim_limit():
    try: nb.QSim(7); assert False
    except ValueError: pass
def test_decoherence(): assert nb.fidelity_after(0.999, 1000, 1000) < 0.999
def test_coherence(): assert abs(nb.coherence_remaining(100, 100) - round(math.exp(-1), 6)) < 1e-9
def test_ecc_above_threshold(): assert nb.surface_code_distance(0.02) == -1
def test_ecc_estimate(): assert nb.physical_qubits_estimate(10, 0.001)["physical_total"] > 10
def test_grover(): assert nb.grover_demo()["success_probability"] > 0.9
def test_grover_bits(): assert nb.effective_bits_grover(100) == 50.0
def test_shor15(): 
    r = nb.shor_teaching(15); assert {r["factor_a"], r["factor_b"]} == {3, 5}
def test_shor21():
    r = nb.shor_teaching(21); assert {r["factor_a"], r["factor_b"]} == {3, 7}
def test_dot(): assert nb.quantum_dot(40)["regime"].startswith("single-electron")
def test_dot_scaling(): assert nb.quantum_dot(20)["level_spacing_meV_est"] > nb.quantum_dot(40)["level_spacing_meV_est"]
def test_cryo(): assert "dilution" in nb.cryo_tier(0.015)
def test_threshold(): assert nb.above_threshold(0.999) and not nb.above_threshold(0.99)
def test_holds(): assert len(nb.HOLD_GATES) >= 8 and all(v.startswith("HOLD") for v in nb.HOLD_GATES.values())
def test_slm(): assert len(nb.TinySLM().summarize("Silicon spin qubits trap one electron in a nanoscale quantum dot. Photonic qubits travel at the speed of light through fibre.")) > 10
def test_llm_deterministic(): assert nb.TinyLLM().generate("photonic qubits", seed=3) == nb.TinyLLM().generate("photonic qubits", seed=3)
def test_llm_extends(): assert nb.TinyLLM().generate("silicon spin qubits", seed=7).startswith("silicon spin qubits")
def test_ml_topological(): assert nb.MLModalityClassifier().classify(nb.modality("topological")) == "unproven"
def test_ml_label_valid(): assert nb.MLModalityClassifier().classify(nb.modality("silicon_spin")) in {"fault_tolerant_candidate", "promising", "early"}
def test_nnl_risk_range(): assert 0.0 <= nb._mlp().risk(nb.modality("photonic")) <= 1.0
def test_nnl_ordering(): assert nb._mlp().risk(nb.modality("topological")) > nb._mlp().risk(nb.modality("silicon_spin"))
def test_brief(): 
    b = nb.model_brief("silicon_spin"); assert b["can_override_hold"] is False and b["authority"].startswith("none")
def test_checks_all_pass():
    checks = nb.run_checks(); assert all(ok for _, ok in checks), [n for n, ok in checks if not ok]
def test_scout_bots(): assert len(nb.SCOUT_BOTS) == 20
def test_novelty_squad(): assert len(nb.NOVELTY_SQUAD) == 5 and "PriorArtScout" in nb.NOVELTY_SQUAD
def test_prior_art_report():
    r = nb.prior_art_report(); assert r["concepts_checked"] == 10 and r["exact_matches_found"] == []
def test_prior_art_project_name(): assert nb.novelty_check("PROJECT")["verdict"] == "no_exact_match_found"
def test_prior_art_closest_n03():
    r = nb.prior_art_report(); assert r["closest_match"]["concept"] == "N03" and r["closest_match"]["similarity"] == 0.83
def test_prior_art_findings_sourced(): assert all(f["source"] for f in nb.PRIOR_ART_FINDINGS) and len(nb.PRIOR_ART_FINDINGS) == 11
def test_cli_priorart(): assert nb.main(["priorart"]) == 0
def test_scout_gather_local_only():
    nb.reset_scout_state(); c = nb.run_scout_cycle(1); assert c["gathered"] > 20 and c["all_live_false"]
def test_scout_formulas_wrong_fails():
    nb.reset_scout_state(); c = nb.run_scout_cycle(1); assert c["tested"] == len(nb.FORMULAS) and c["failed"] == 1
def test_scout_deploy_sandbox_only():
    nb.reset_scout_state(); c = nb.run_scout_cycle(1); assert c["deployed_to_sandbox"] and all(e["registry"] == "sandbox_only" for e in nb.SANDBOX_REGISTRY)
def test_scout_loop_repeats_blocked():
    nb.reset_scout_state(); loop = nb.run_scout_loop(2)
    assert loop[1]["deployed_to_sandbox"] == [] and loop[1]["repeats_blocked"] == loop[0]["passed"]
def test_verify_fingerprint_stable():
    assert nb.invention_fingerprint("Test  Name!", 1.0) == nb.invention_fingerprint("test name", 1.0)
def test_verify_exact_repeat():
    d = nb.verify_demo(); assert d["exact_repeat"] in ("repeat_exact", "repeat_name")
def test_verify_renamed_repeat():
    d = nb.verify_demo(); assert d["renamed_repeat"] in ("repeat_exact", "repeat_name", "repeat_semantic")
def test_verify_novel_passes():
    d = nb.verify_demo(); assert d["first"] == "novel" and d["genuinely_new"] == "novel"
def test_verify_reruns_tests():
    assert nb.VerifyBot(registry=[]).verify_and_check(nb.FORMULAS[-1])["verdict"] == "failed_tests"
def test_verify_semantic_renamed_copy():
    reg = [{"formula_id": "X1", "name": "Cryo wiring heat load model", "result": 10.0,
            "fingerprint": nb.invention_fingerprint("Cryo wiring heat load model", 10.0)}]
    bot = nb.VerifyBot(registry=reg)
    v = bot.check({"id": "X2", "name": "Cryo wiring heat load model v2", "result": 10.0})
    assert v["verdict"] in ("repeat_semantic", "repeat_name", "repeat_exact")
def test_top20_count_unique():
    assert len(nb.TOP20) == 20 and len({t.id for t in nb.TOP20}) == 20 and len({t.invention for t in nb.TOP20}) == 20
def test_top20_fields(): assert {t.field for t in nb.TOP20} >= {"quantum", "nano", "data"}
def test_top20_companies_present():
    companies = {t.company for t in nb.TOP20}
    for c in ("Google Quantum AI", "IBM", "Microsoft", "Quantinuum", "IonQ", "QuEra / Harvard / MIT", "PsiQuantum", "Diraq + imec"): assert c in companies
def test_deconstruction_scout_in_fleet(): assert any(b.name == "DeconstructionScout" for b in nb.SCOUT_BOTS)
def test_deconstruct_all():
    dec = nb.DECONSTRUCTION_SCOUT.deconstruct_all(); assert len(dec) == 20 and all(len(d["component_tags"]) >= 4 for d in dec)
def test_create_new_inventions():
    nb.reset_scout_state(); r = nb.create_new_inventions(10)
    assert r["created_count"] >= 8 and all(len(set(c["parents"])) == 3 for c in r["created"])
def test_new_inventions_not_repeats_of_top20():
    nb.reset_scout_state(); r = nb.create_new_inventions(10)
    top_names = {t.invention for t in nb.TOP20}; assert all(c["name"] not in top_names for c in r["created"])
def test_recreate_blocked_by_verifybot():
    nb.reset_scout_state(); nb.create_new_inventions(10); r2 = nb.create_new_inventions(10)
    assert r2["created_count"] == 0 and r2["blocked_count"] == 10
def test_carbon4_config():
    assert nb.CARBON4["role"] == "DECIDER" and nb.CARBON4["model"] == "google/gemini-carbon-4-extended-pro-thinking" and nb.CARBON4["can_override_hold"] is False
def test_carbon4_tiers(): assert (nb.carbon4_tier("standard"), nb.carbon4_tier("deep"), nb.carbon4_tier("extended")) == (2048, 8192, 32768)
def test_carbon4_proceed_sandbox():
    d = nb.carbon4_decide("sandbox deploy of verified formulas", {"passed": 7, "failed": 1}); assert d["decision"] == "PROCEED" and len(d["trace_hash"]) == 64
def test_carbon4_hold_real(): assert nb.carbon4_decide("real deployment to live hardware", {"passed": 7, "failed": 0})["decision"] == "HOLD"
def test_carbon4_hold_failures(): assert nb.carbon4_decide("sandbox deploy", {"passed": 2, "failed": 5})["decision"] == "HOLD"
def test_carbon4_key_presence_only(): assert nb.carbon4_key_presence()["key_name"] == "GEMINI_API_KEY"
def test_google_flows_plan_only():
    gf = nb.google_flows(); assert gf["flow_count"] == 4 and gf["live_calls"] == 0 and gf["rendered"] is False
def test_flow_filmmaking_storyboard(): assert nb.flow_filmmaking()["shot_count"] == 5
def test_flowx_graph(): assert "verifybot_check" in nb.flowx_graph()["steps"]
def test_brains_fusion(): assert len(nb.brains()["local_models"]) == 4
def test_hold_gates_17(): assert len(nb.HOLD_GATES) == 17
def test_scout_cycle_carbon_fields():
    nb.reset_scout_state(); c = nb.run_scout_cycle(1)
    assert c["carbon4_sandbox_decision"] == "PROCEED" and c["carbon4_real_decision"] == "HOLD"
def test_cli_brains(): assert nb.main(["brains"]) == 0
def test_cli_carbon(): assert nb.main(["carbon"]) == 0
def test_cli_flow(): assert nb.main(["flow"]) == 0
def test_brief_llm_extends(): assert len(nb.model_brief("silicon_spin")["llm_draft"]) > 25
def test_cli_demo(): assert nb.main(["demo"]) == 0
def test_cli_scouts(): assert nb.main(["scouts"]) == 0
def test_cli_verify(): assert nb.main(["verify"]) == 0
def test_cli_top20(): assert nb.main(["top20"]) == 0
def test_cli_invent(): assert nb.main(["invent"]) == 0
def test_cli_checks(): assert nb.main(["checks"]) == 0
