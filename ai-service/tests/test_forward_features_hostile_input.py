"""Regression: forward engines degrade on hostile rows instead of raising.

These mirror the discipline of ``test_forward_features_robustness.py`` but target the
Epic 10.11 (progression) and Epic 10.13 (interview prep) pure builders specifically --
the ones the health check showed still raised ``TypeError`` / ``AttributeError`` on
``None`` / empty / wrong-shaped input. A malformed payload from a peer service or a
stale cached row must produce an empty/safe result, never crash the request path.
"""

import pytest

from app.features import (company, cover_letter, counter_offer, demand, equity, export,
                             export_redact, export_render, export_words, gap_analysis,
                             import_plan, interview, interview_prep, jd_analyze, learning,
                             match, negotiation, offers, prioritize, progress, progression,
                             readiness, resume_parse, roles, salary, tailor)


# --- progression.build_stepping_stones -------------------------------------

def test_stepping_stones_none_families_and_gaps():
    assert progression.build_stepping_stones(None, None, None) == []


def test_stepping_stones_none_gap_lists_with_families():
    fams = [{"family": "f", "topDemands": ["x"], "coverage": 0.2, "postings": 3}]
    # No gaps to build -> nothing qualifies, but it must not raise.
    assert progression.build_stepping_stones(fams, None, None) == []


def test_stepping_stones_none_family_entry_is_skipped():
    fams = [None, {"family": "f", "topDemands": ["x"], "coverage": 0.2, "postings": 3}]
    # The None entry must be skipped (no crash), leaving only the real family.
    stones = progression.build_stepping_stones(fams, ["x"], [])
    assert [s["family"] for s in stones] == ["f"]


def test_stepping_stones_non_str_gap_entries_ignored():
    fams = [{"family": "f", "topDemands": ["x"], "coverage": 0.2, "postings": 3}]
    # A non-string gap must not break the set comprehension; only "x" survives.
    stones = progression.build_stepping_stones(fams, ["x", 12, None], [])
    assert len(stones) == 1
    assert stones[0]["family"] == "f"
    assert stones[0]["buildsSkills"] == ["x"]
    assert stones[0]["buildsCount"] == 1


def test_stepping_stones_topdemands_none_skips_family():
    fams = [{"family": "f", "topDemands": None, "coverage": 0.2, "postings": 3}]
    assert progression.build_stepping_stones(fams, ["x"], []) == []


def test_stepping_stones_real_match_produces_stone():
    fams = [{"family": "data", "topDemands": ["sql", "python"], "coverage": 0.5, "postings": 10}]
    stones = progression.build_stepping_stones(fams, ["sql", "python"], ["sql"])
    assert len(stones) == 1
    assert stones[0]["family"] == "data"
    assert stones[0]["buildsMustCount"] == 1
    assert stones[0]["bridgeScore"] > 0


# --- progression.build_advice ----------------------------------------------

def test_build_advice_none_must_gaps_no_crash():
    lines = progression.build_advice(0.4, 2, None)
    assert isinstance(lines, list) and lines


def test_build_advice_none_coverage_no_crash():
    lines = progression.build_advice(None, 0, [])
    assert isinstance(lines, list) and lines


def test_build_advice_non_numeric_coverage_coerced():
    # A non-float coverage must not raise on comparison.
    lines = progression.build_advice("high", 0, [])
    assert isinstance(lines, list)


def test_build_advice_must_gaps_and_readiness_lines():
    lines = progression.build_advice(0.85, 1, ["distributed-systems"])
    joined = " ".join(lines)
    assert "hard-requirement gap" in joined
    assert "85%" in joined


# --- interview_prep.build_prep_plan ----------------------------------------

def test_prep_plan_none_inputs_returns_safe_dict():
    plan = interview_prep.build_prep_plan(None, None)
    assert plan["weakAreaCount"] == 0
    assert plan["coverage"] == 0.0
    assert plan["weakAreas"] == []
    assert plan["storyBankSize"] == 0


def test_prep_plan_empty_dicts_returns_safe_dict():
    plan = interview_prep.build_prep_plan({}, {})
    assert plan["weakAreaCount"] == 0
    assert plan["coverage"] == 0.0


def test_prep_plan_present_none_value_keys_handled():
    # A key present but set to None must behave like missing.
    report = {"gaps": None, "covered": None, "responsibilities": None}
    plan = interview_prep.build_prep_plan(report, {"stories": None})
    assert plan["weakAreaCount"] == 0
    assert plan["likelyTopics"] == []


def test_prep_plan_non_dict_gap_entry_filtered():
    report = {"gaps": [None, "not-a-dict", {"skill": "sql", "importance": "must"}]}
    plan = interview_prep.build_prep_plan(report, {})
    assert plan["weakAreaCount"] == 1
    assert plan["weakAreas"][0]["skill"] == "sql"


def test_prep_plan_gap_missing_skill_uses_unknown():
    report = {"gaps": [{"importance": "should"}]}
    plan = interview_prep.build_prep_plan(report, {})
    assert plan["weakAreas"][0]["skill"] == "unknown"


# --- prioritize.rank_gap_priorities ----------------------------------------

def test_rank_priorities_none_inputs_returns_empty():
    assert prioritize.rank_gap_priorities(None, None, None) == []


def test_rank_priorities_none_gap_entry_skipped():
    gaps = [None, {"skill": "k8s", "importance": "must"}]
    ranked = prioritize.rank_gap_priorities(gaps, [], 0)
    assert [r["skill"] for r in ranked] == ["k8s"]


def test_rank_priorities_non_dict_demand_skipped():
    # A demand entry that is None/non-dict must not break the demand map build.
    demand = [None, "not-a-dict", {"skill": "k8s", "count": 3, "share": 0.5}]
    gaps = [{"skill": "k8s", "importance": "must"}]
    ranked = prioritize.rank_gap_priorities(gaps, demand, 10)
    assert ranked[0]["marketRank"] == 3
    assert ranked[0]["marketShare"] == 0.5


def test_rank_priorities_gap_missing_skill_skipped():
    gaps = [{"importance": "must"}, {"skill": "docker", "importance": "should"}]
    ranked = prioritize.rank_gap_priorities(gaps, [], 0)
    assert [r["skill"] for r in ranked] == ["docker"]


def test_rank_priorities_demand_missing_share_defaults_zero():
    demand = [{"skill": "k8s", "count": 2}]  # no "share" key
    gaps = [{"skill": "k8s", "importance": "must"}]
    ranked = prioritize.rank_gap_priorities(gaps, demand, 5)
    assert ranked[0]["marketShare"] == 0.0
    assert ranked[0]["marketRank"] == 2


def test_rank_priorities_real_match_ranks_by_importance_then_share():
    gaps = [
        {"skill": "docker", "importance": "should"},
        {"skill": "k8s", "importance": "must"},
    ]
    demand = [
        {"skill": "k8s", "count": 10, "share": 0.6},
        {"skill": "docker", "count": 4, "share": 0.3},
    ]
    ranked = prioritize.rank_gap_priorities(gaps, demand, 20)
    assert ranked[0]["skill"] == "k8s"  # must + high share ranks first
    assert ranked[0]["priority"] == "critical"


# --- readiness / learning / progress: gap-report consumers ------------------

def test_must_gaps_none_report_returns_empty():
    assert readiness.must_gaps(None) == []


def test_compose_none_report_is_safe():
    out = readiness.compose(None)
    assert out["verdict"] == "not_ready"
    assert out["skillReadiness"] == 0.0
    assert out["mustGaps"] == []


def test_compose_present_none_keys_is_safe():
    out = readiness.compose({"gaps": None, "developmentPlan": None})
    assert out["targetRole"] == ""
    assert out["gapCount"] == 0


def test_build_learning_plan_none_report_is_safe():
    out = learning.build_learning_plan(None)
    assert out["totalItems"] == 0
    assert out["phases"] == []


def test_build_learning_plan_none_gap_entry_skipped():
    report = {"gaps": [None, {"skill": "sql", "category": "data"}]}
    out = learning.build_learning_plan(report)
    assert out["totalItems"] == 1
    assert out["phases"][0]["items"][0]["topic"] == "sql"


def test_skill_states_none_entry_filtered():
    report = {"gaps": [None, "not-a-dict", {"skill": "k8s", "importance": "must"}]}
    states = progress.skill_states(report)
    assert states == {"k8s": "gap"}


def test_diff_progress_none_both_is_safe():
    out = progress.diff_progress(None, None)
    assert out["baseline"] is True
    assert out["closed"] == []
    assert out["currentCoverage"] == 0.0


# --- Epic 12 salary / offer / negotiation / equity / counter-offer ----------

def test_salary_percentile_none_returns_none():
    assert salary.percentile(None, 0.5) is None


def test_salary_representative_none_row_returns_none():
    assert salary.representative(None) is None


def test_salary_summarize_none_is_empty():
    assert salary.summarize(None) == {"count": 0}


def test_salary_filter_samples_none_is_empty():
    assert salary.filter_samples(None, role="backend") == []


def test_salary_position_none_values_is_unknown():
    assert salary.position(100000, None) == {"percentile": None, "verdict": "unknown"}


def test_salary_benchmark_none_samples_is_safe():
    out = salary.benchmark(None, role="backend engineer")
    assert out["sampleSize"] == 0
    assert "note" in out


def test_negotiation_stats_none_is_zero():
    assert negotiation._stats(None) == {"count": 0}


def test_negotiation_assess_none_stats_is_unknown():
    out = negotiation.assess(100000, None)
    assert out["verdict"] == "unknown"


def test_negotiation_leverage_none_stats_is_unknown():
    assert negotiation.leverage(100000, None) == "unknown"


def test_negotiation_talking_points_none_stats_safe():
    pts = negotiation.talking_points(100000, None)
    assert isinstance(pts, list) and pts


def test_offers_stats_none_is_zero():
    assert offers._stats(None) == {"count": 0}


def test_compare_offers_none_list_is_safe():
    out = offers.compare_offers(None, {})
    assert out["offers"] == []
    assert out["bestByComp"] is None


def test_compare_offers_none_offer_entry_skipped():
    out = offers.compare_offers([None, {"base": 100000}], {})
    assert len(out["offers"]) == 1
    assert out["bestByComp"] == ""


def test_equity_annualized_none_grant_is_zero():
    out = equity.annualized_value(None)
    assert out["annualValue"] == 0
    assert "perYear" in out


def test_equity_annualized_bad_vest_years_falls_back():
    out = equity.annualized_value({"vest_years": "abc"})
    assert out["vestYears"] == equity.DEFAULT_VEST_YEARS


def test_equity_annualized_bad_schedule_falls_back():
    out = equity.annualized_value({"schedule": [None, 0.5]})
    assert isinstance(out["perYear"], list)


def test_counter_offer_stats_none_is_zero():
    assert counter_offer._stats(None) == {"count": 0}


def test_counter_offer_target_ask_none_report_returns_offer():
    assert counter_offer.target_ask(100000, None) == 100000


def test_counter_offer_compose_none_report_and_out_is_safe():
    out = counter_offer.compose(100000, None, None)
    assert out["askAmount"] == 100000
    assert "subject" in out and "body" in out


# --- corpus consumers: roles.suggest_roles / demand.skill_demand ------------

def test_suggest_roles_none_samples_is_safe():
    out = roles.suggest_roles(None, ["python"])
    assert out["families"] == []


def test_suggest_roles_none_entry_skipped():
    out = roles.suggest_roles([None, {"title": "Backend Engineer", "skills": ["go"]}], None)
    assert [f["family"] for f in out["families"]] == ["backend"]


def test_suggest_roles_none_resume_skills_is_safe():
    out = roles.suggest_roles([{"title": "Backend Engineer", "skills": ["go"]}], None)
    assert out["families"][0]["youHave"] == []


def test_skill_demand_none_samples_is_safe():
    out = demand.skill_demand(None, role="backend")
    assert out["postings"] == 0
    assert out["skills"] == []


def test_skill_demand_none_entry_skipped():
    out = demand.skill_demand([None, {"title": "Backend Engineer", "skills": ["go"]}],
                              role="backend")
    assert out["postings"] == 1
    assert out["skills"][0]["skill"] == "Go"


# ---------------- company brief (forward Epic 4.8) ----------------

def test_company_brief_none_samples_is_safe():
    out = company.company_brief(None, "Acme")
    assert out == {"company": "Acme", "postings": 0, "roles": [],
                   "topSkills": [], "salaryBand": None}


def test_company_brief_none_and_non_dict_rows_skipped():
    samples = [None, "junk", 42, {"company": "Acme", "title": "Dev", "skills": ["Go"]}]
    out = company.company_brief(samples, "Acme")
    assert out["postings"] == 1
    assert out["roles"] == ["Dev"]
    assert out["topSkills"] == [{"skill": "Go", "count": 1}]


# ---------------- match scoring helpers (PRD §10) ----------------
# The resume parser and peer JD payloads feed these helpers; a None resume, a
# None JD, or a non-dict entry inside experience/education/projects/requirements
# must degrade to the neutral score, never AttributeError/TypeError the flow.

def test_match_helpers_survive_none_parsed_and_jd():
    assert match._skill_set(None) == set()
    assert match._user_years(None) == 0.0
    assert match._edu_rank(None) == -1.0
    assert match._min_degree(None) == ""
    score, _note = match._experience_score(None, None)   # no stated years -> neutral
    assert score == 0.75
    assert isinstance(match._education_score(None, None), float)


def test_user_years_skips_non_dict_experience_entries():
    p = {"experience": [None, "junk", {"start": "2019", "end": "2022"}]}
    assert match._user_years(p) == 3.9                     # only the real role counts


def test_projects_score_skips_non_dict_project_entries():
    p = {"projects": [None, "junk", {"tech": ["Go"]}], "experience": []}
    assert match._projects_score(p, [], [], {}) == 0.25     # one real project, no overlap


def test_skill_gaps_and_technical_score_skip_non_dict_requirements():
    req = [None, "junk", {"name": "Kubernetes", "priority": "must"}]
    gaps = match._skill_gaps(req, set())
    assert [g["skill"] for g in gaps] == ["Kubernetes"]
    # the denominator counts only the one real must, so holding it is full coverage
    assert match._technical_score(req, [], {"Kubernetes"}) == 1.0


# ---------------- export redact / render (Epic 13.1/13.3) ----------------
# The bundle is user data and reaches these from the bridge; a null bundle, a
# present-null data/manifest, or a junk entry inside a section must render/redact
# to a safe result, never raise on the download path.

def test_redact_bundle_none_and_wrong_typed_is_safe():
    out = export_redact.redact_bundle(None, ["memories"])
    assert out["manifest"]["redacted_sections"] == []
    assert "content_hash" in out["manifest"]
    bad = {"data": None, "manifest": None, "resumes": [1, 2]}
    out2 = export_redact.redact_bundle(bad, ["resumes"])
    assert out2["manifest"]["redacted_sections"] == []


def test_redact_bundle_still_rejects_unknown_section():
    # hardening the container must not blunt the typo guard
    with pytest.raises(ValueError):
        export_redact.redact_bundle({}, ["not-a-real-section"])


def test_to_html_none_bundle_is_safe():
    out = export_render.to_html(None)
    assert out.startswith("<!doctype html>")
    # The document's own words, in the language it was asked for.
    assert export_words.words("en")["title"] in out
    assert export_words.words("zh")["title"] in export_render.to_html(None, "zh")


def test_to_html_null_and_junk_sections_do_not_crash():
    bundle = {"data": {"profile": None, "resumes": None, "knowledge": [None, "junk"],
                       "growth_plans": [None, {"target_role": "SE"}]},
              "manifest": {"counts": None}, "user": None, "generated_at": None}
    out = export_render.to_html(bundle)
    assert out.startswith("<!doctype html>")
    assert "SE" in out          # the one real growth_plans row still renders


# ---------------- export composition (Epic 13.1/13.3) ----------------

def test_anonymize_none_and_null_sections_is_safe():
    out = export.anonymize(None)                       # a None bundle -> empty, stamped
    assert out["manifest"]["anonymized"] is True
    nullish = {"data": {"profile": None, "resumes": None}, "user": None, "manifest": None}
    out2 = export.anonymize(nullish)                   # {**None} used to raise TypeError
    assert out2["manifest"]["anonymized"] is True


def test_anonymize_still_strips_pii_and_leaves_non_pii():
    bundle = {"data": {"profile": {"email": "a@b.com", "display_name": "Ann",
                                   "headline": "SE"}}}
    out = export.anonymize(bundle)
    assert out["data"]["profile"]["email"] is None
    assert out["data"]["profile"]["display_name"] is None
    assert out["data"]["profile"]["headline"] == "SE"   # a non-PII field is left alone


def test_to_markdown_none_and_junk_sections_is_safe():
    assert export.to_markdown(None).startswith("# AI Career OS")
    junk = {"data": {"profile": "not-a-dict", "resumes": None,
                     "memories": [None, {"kind": "pref"}]},
            "manifest": {"counts": None}, "user": None}
    assert export.to_markdown(junk).startswith("# AI Career OS")


# ---------------- cover-letter prompt builder + JD suggester ----------------

def test_build_prompt_none_jd_and_null_profile_is_safe():
    out = cover_letter._build_prompt({}, None, None, "staff eng", "evidence",
                                      "", "", "generate", "")
    assert "ROLE" in out and "CANDIDATE" in out


def test_build_prompt_non_dict_required_skills_are_skipped():
    jd = {"title": "SE", "company": "Acme",
          "requiredSkills": [{"name": "Go"}, "junk", None, {"name": "Rust"}]}
    out = cover_letter._build_prompt({"profile": {"name": "Ann"}}, jd, None,
                                     "", "", "", "", "generate", "")
    assert "Go" in out and "Rust" in out and "junk" not in out and "None" not in out


def test_backfill_skills_none_out_is_safe():
    text = "We use Go and PostgreSQL daily."
    out = jd_analyze._backfill_skills(None, text)
    assert out["rawTextLength"] == len(text)
    assert isinstance(out.get("preferredSkills"), list)


def test_suggest_resume_improvements_none_inputs_is_safe():
    # a None JD + None resume still emits the structure/impact advice, no crash
    assert [g["type"] for g in jd_analyze.suggest_resume_improvements(None, None)] == [
        "structure", "impact"]
    junk = {"requiredSkills": [None, "golang"]}
    got = jd_analyze.suggest_resume_improvements(junk, {"experience": [None, "x"]})
    # a None requirement used to surface as the literal string "None"
    assert [g["skill"] for g in got if g["type"] == "missing_required"] == ["golang"]


# ---------------- tailoring verifier/applier (PRD §11) ----------------

def test_verify_no_fabrication_none_texts_are_safe():
    assert tailor.verify_no_fabrication(None, None, None) is None
    # a fabricated skill is still rejected once the texts are real
    reason = tailor.verify_no_fabrication("Built a Go service.", "",
                                          "Built a Go and Kubernetes service.")
    assert reason is not None and "Kubernetes" in reason


def test_apply_changes_none_and_junk_rows_are_safe():
    assert tailor._apply_changes(None, [None, "junk"], None, None) == {}
    structured = {"experience": [None, {"bullets": [None, "Wrote a Go service"]}],
                  "projects": "not-a-list", "profile": None, "skills": [None, {"name": "Go"}]}
    t = tailor._apply_changes(structured, [
        {"section": "experience", "index": 1, "before": "Wrote a Go service",
         "after": "Wrote a Go service"},
        {"section": "experience", "index": 0},          # a None row is skipped
        {"section": "projects", "index": 0},            # a non-list section is skipped
    ], {"summary": "Go engineer", "skillOrder": ["go", None]}, "Go")
    assert t["experience"][1]["bullets"] == [None, "Wrote a Go service"]
    assert t["profile"] == {"summary": "Go engineer"}
    assert [s["name"] for s in t["skills"]] == ["Go"]


# ---------------- resume parse / score (PRD §3) ----------------

def test_compute_resume_score_none_and_junk_rows_are_safe():
    assert resume_parse.compute_resume_score(None)["total"] == 0
    junk = {"profile": None, "experience": [None, "x", {"bullets": [None, 3, "cut p95 by 40%"]}],
            "projects": None, "education": None, "skills": None}
    out = resume_parse.compute_resume_score(junk)
    # 20 experience + 10 quantified; the bullets bar needs >=3 str bullets (only 1 here)
    assert out["total"] == 30
    assert out["impact"] == 100


def test_merge_skills_skips_rows_without_a_name():
    merged = resume_parse._merge_skills([{"category": "cloud"}, None, "junk",
                                         {"name": "react"}], ["Go", None])
    assert [s["name"] for s in merged] == ["React", "Go"]


# ---------------- import planning + bundle validation (Epic 13.2) ----------------

def test_validate_bundle_null_manifest_and_data_are_contract_errors():
    # a present-null manifest/data used to raise TypeError inside validate_bundle
    errs = export.validate_bundle({"schema_version": "1.1.0", "generator": "g",
                                   "generated_at": "t", "user": {}, "manifest": None,
                                   "data": None})
    assert "manifest is not a JSON object" in errs
    assert "data is not a JSON object" in errs


def test_plan_import_skips_non_dict_items_and_null_data():
    data = {"profile": None, "resumes": [None, "junk", {"id": "r1"}],
            "knowledge": [], "job_descriptions": [], "interviews": [], "memories": []}
    bundle = {"schema_version": "1.0.0", "generator": "g", "generated_at": "t",
              "user": {"id": "u"},
              "manifest": {"schema_version": "1.0.0", "generator": "g", "counts": {},
                           "content_hash": export.content_hash(data),
                           "anonymized": False},
              "data": data}
    plan = import_plan.plan_import(bundle)
    assert plan["sections"]["resumes"] == [
        {"op": "create", "id": "r1",
         "content_hash": export.content_hash({"id": "r1"})}]
    assert "profile" not in plan["sections"]      # a null profile is nothing to plan


# ---------------- career gap analysis (Epic 10.1) ----------------

def test_classify_coverage_skips_non_dict_and_keyless_rows():
    expected = [None, "junk", {"name": "Go", "importance": "must", "category": "core"},
                {"importance": "should"}]                      # no name -> skipped
    covered, partial, gaps = gap_analysis.classify_coverage(expected, set(), None)
    assert covered == [] and partial == []
    assert [g["skill"] for g in gaps] == ["Go"]
    assert gaps[0]["importance"] == "must" and gaps[0]["category"] == "core"


def test_build_development_plan_skips_non_dict_rows():
    plan = gap_analysis.build_development_plan([None, {"skill": "Go", "importance": "must"}],
                                               ["junk", {"skill": "Rust", "importance": "nice"}])
    assert [i["skill"] for i in plan] == ["Go", "Rust"]       # must ranks before nice
    assert plan[0]["priority"] == "must"


def test_build_evidence_and_sanitize_survive_none():
    skills, corpus = gap_analysis.build_evidence(None, None)
    assert skills == set() and corpus == ""
    out = gap_analysis._sanitize_expected(None, None)
    assert out == {"expectedSkills": [], "responsibilities": [], "seniorityHint": ""}
    # a non-str importance falls back to "should" rather than raising
    out2 = gap_analysis._sanitize_expected({"expectedSkills": [{"name": "go",
                                                               "importance": 7}]}, "go")
    assert out2["expectedSkills"][0]["importance"] == "should"


# ---------------- adaptive interview (PRD §13-15) ----------------

def test_decide_next_none_out_and_junk_turns_are_safe():
    got = interview.decide_next(None, difficulty=0.5, qnum=8, max_q=8,
                                turns=[None, "junk", {"role": "candidate"}])
    assert got["action"] == "finish"          # budget spent, last real turn is a candidate
    assert got["question"] == ""
    # a non-str question is coerced rather than crashing on .strip()
    got2 = interview.decide_next({"action": "followup", "question": 7}, difficulty=0.5,
                                 qnum=1, max_q=8, turns=[])
    assert got2["question"] == "" and got2["action"] == "followup"


def test_trajectory_detail_skips_non_dict_turns_and_meta():
    rows = interview._trajectory_detail([None, "junk", {"seq": 1, "role": "interviewer"},
                                         {"seq": 2, "role": "candidate",
                                          "question_meta": "not-a-dict",
                                          "evaluation": None}])
    assert [r["seq"] for r in rows] == [1, 2]
    assert rows[1]["topic"] is None and rows[1]["score"] is None


def test_state_brief_none_turns_and_ctx_are_safe():
    brief = interview._state_brief("persona", "mixed", [None, {"role": "interviewer"}],
                                   0.5, 1, 8, None, ["systems"])
    assert "CANDIDATE" in brief and "Question 1 asked so far" in brief

