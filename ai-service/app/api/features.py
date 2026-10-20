from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import Ctx, require_internal
from app.db import domain, observability
from app.features import company as company_mod
from app.features import gap_analysis as gap_mod
from app.features import growth as growth_mod
from app.features import jd_analyze as jd_an
from app.features import learning as learning_mod
from app.features import match as match_mod
from app.features import negotiation as negotiation_mod
from app.features import offers as offers_mod
from app.features import outreach as outreach_mod
from app.features import progress as progress_mod
from app.features import readiness as readiness_mod
from app.features import reminders as reminders_mod
from app.features import resume_parse as rp
from app.features import roles as roles_mod
from app.features import salary as salary_mod
from app.features import stories as stories_mod
from app.features import tailor as tailor_mod
from app.features import counter_offer as counter_offer_mod
from app.features import demand as demand_mod
from app.features import progression as progression_mod
from app.features import prioritize as prioritize_mod
from app.features import interview_prep as interview_prep_mod
from app.features import analytics as analytics_mod
from app.features import ingestion as ingestion_mod
from app.features import monitoring as monitoring_mod
from app.features import export as export_mod
from app.features import import_plan as import_plan_mod
from app.features import export_redact as export_redact_mod
from app.features.cover_letter import generate as cover_generate

router = APIRouter(prefix="/internal/features", tags=["features"])


async def _run(ctx: Ctx, agent: str, trigger: str) -> str:
    return ctx.run_id or await observability.create_run(ctx.user_id, agent, trigger)


async def _resume_payload(user_id: str, resume_version_id: str | None) -> tuple[dict, str]:
    rv = await domain.get_resume_version(resume_version_id, user_id) \
        if resume_version_id else await domain.get_current_resume_version(user_id)
    if not rv:
        raise HTTPException(404, "no resume version found")
    import json

    structured = rv["structured"]
    if isinstance(structured, str):
        structured = json.loads(structured)
    return structured, rv.get("plaintext") or ""


class ParseReq(BaseModel):
    text: str = Field(min_length=20)


@router.post("/resume/parse")
async def resume_parse(req: ParseReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "resume", "resume_parse")
    try:
        parsed = await rp.parse_resume(req.text, user_id=ctx.user_id, run_id=run_id)
    finally:
        pass
    score = rp.compute_resume_score(parsed)
    await observability.finish_run(run_id, "completed")
    return {"parsed": parsed, "score": score}


class JdReq(BaseModel):
    raw_text: str = Field(min_length=20)


@router.post("/jd/analyze")
async def jd_analyze_ep(req: JdReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "jd_analyst", "jd_analyze")
    parsed = await jd_an.analyze_jd(req.raw_text, user_id=ctx.user_id, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return {"parsed": parsed}


class MatchReq(BaseModel):
    job_id: str
    resume_version_id: str | None = None


@router.post("/match")
async def match_ep(req: MatchReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "jd_analyst", "match")
    job = await domain.get_job(req.job_id)
    if not job:
        raise HTTPException(404, "job not found")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    jd = job.get("jd_parsed") or job.get("parsed")
    import json

    if isinstance(jd, str):
        jd = json.loads(jd)
    if not jd:
        jd = await jd_an.analyze_jd(job["description"], user_id=ctx.user_id, run_id=run_id)
    result = await match_mod.compute_match(structured, jd, user_id=ctx.user_id,
                                           job_id=req.job_id, run_id=run_id)
    rv = await domain.get_current_resume_version(ctx.user_id) if not req.resume_version_id \
        else await domain.get_resume_version(req.resume_version_id, ctx.user_id)
    match_id = None
    if rv and result:
        match_id = await match_mod.persist_match(ctx.user_id, req.job_id, str(rv["id"]),
                                                 result)
    await observability.finish_run(run_id, "completed")
    return {"match": result, "match_id": match_id, "jd": jd}


class TailorReq(BaseModel):
    job_id: str
    resume_version_id: str | None = None


@router.post("/tailor")
async def tailor_ep(req: TailorReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "resume", "tailor")
    job = await domain.get_job(req.job_id)
    if not job:
        raise HTTPException(404, "job not found")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    import json

    jd = job.get("jd_parsed")
    if isinstance(jd, str):
        jd = json.loads(jd)
    if not jd:
        jd = await jd_an.analyze_jd(job["description"], user_id=ctx.user_id, run_id=run_id)
    out = await tailor_mod.tailor(structured, plaintext, jd, user_id=ctx.user_id,
                                  job_title=job["title"], run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return out


class CoverReq(BaseModel):
    job_id: str
    resume_version_id: str | None = None
    mode: str = "generate"
    previous: str = ""
    goal: str = ""
    tone: str = ""
    length: str = ""


@router.post("/cover-letter")
async def cover_ep(req: CoverReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "resume", "cover_letter")
    job = await domain.get_job(req.job_id)
    if not job:
        raise HTTPException(404, "job not found")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    import json

    jd = job.get("jd_parsed")
    if isinstance(jd, str):
        jd = json.loads(jd)
    if not jd:
        jd = await jd_an.analyze_jd(job["description"], user_id=ctx.user_id, run_id=run_id)
    company = {"name": job.get("company_name"), "overview": job.get("company_overview")}
    out = await cover_generate(structured, plaintext, jd, company, req.goal,
                               user_id=ctx.user_id, mode=req.mode,
                               previous=req.previous, tone=req.tone,
                               length=req.length, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return out


class SuggestReq(BaseModel):
    resume_version_id: str | None = None
    jd_raw: str = Field(min_length=20)


@router.post("/jd/suggestions")
async def suggestions_ep(req: SuggestReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "jd_analyst", "jd_suggestions")
    structured, _ = await _resume_payload(ctx.user_id, req.resume_version_id)
    jd = await jd_an.analyze_jd(req.jd_raw, user_id=ctx.user_id, run_id=run_id)
    suggestions = jd_an.suggest_resume_improvements(jd, structured)
    await observability.finish_run(run_id, "completed")
    return {"suggestions": suggestions, "jd": jd}


class GapReq(BaseModel):
    target_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None


@router.post("/gap-analysis")
async def gap_analysis_ep(req: GapReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "learning", "gap_analysis")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    result = await gap_mod.analyze_gap(req.target_role, req.seniority, structured,
                                      plaintext, user_id=ctx.user_id, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return result


class SalaryReq(BaseModel):
    role: str = Field(min_length=2)
    location: str | None = None
    seniority: str | None = None
    target_salary: int | None = None
    currency: str = "CNY"


@router.post("/salary-benchmark")
async def salary_benchmark_ep(req: SalaryReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "salary_benchmark")
    samples = await salary_mod.load_job_samples()
    report = salary_mod.benchmark(samples, role=req.role, location=req.location,
                                  seniority=req.seniority, target_salary=req.target_salary,
                                  currency=req.currency)
    await observability.finish_run(run_id, "completed")
    return report


class NegotiateReq(BaseModel):
    role: str = Field(min_length=2)
    location: str | None = None
    seniority: str | None = None
    currency: str = "CNY"
    offer_base: int = Field(gt=0)
    match_score: float | None = Field(default=None, ge=0, le=1)


@router.post("/negotiate")
async def negotiate_ep(req: NegotiateReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "negotiate")
    samples = await salary_mod.load_job_samples()
    report = salary_mod.benchmark(samples, role=req.role, location=req.location,
                                  seniority=req.seniority, currency=req.currency)
    plan = negotiation_mod.negotiation_plan(req.offer_base, report,
                                            match_score=req.match_score,
                                            currency=req.currency)
    await observability.finish_run(run_id, "completed")
    return plan


class ReadinessReq(BaseModel):
    target_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None
    location: str | None = None
    currency: str = "CNY"
    target_salary: int | None = None


@router.post("/readiness")
async def readiness_ep(req: ReadinessReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "learning", "readiness")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    gap = await gap_mod.analyze_gap(req.target_role, req.seniority, structured, plaintext,
                                    user_id=ctx.user_id, run_id=run_id)
    samples = await salary_mod.load_job_samples()
    salary = salary_mod.benchmark(samples, role=req.target_role, location=req.location,
                                  seniority=req.seniority, target_salary=req.target_salary,
                                  currency=req.currency)
    result = readiness_mod.compose(gap, salary)
    await observability.finish_run(run_id, "completed")
    return {"readiness": result, "gap": gap, "salary": salary}


class LearningReq(BaseModel):
    target_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None


@router.post("/learning-plan")
async def learning_plan_ep(req: LearningReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "learning", "learning_plan")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    gap = await gap_mod.analyze_gap(req.target_role, req.seniority, structured, plaintext,
                                    user_id=ctx.user_id, run_id=run_id)
    plan = learning_mod.build_learning_plan(gap)
    await observability.finish_run(run_id, "completed")
    return {"plan": plan, "gap": gap}


class EquityGrant(BaseModel):
    shares: int = Field(ge=0)
    strike_price: float = Field(ge=0)
    current_price: float = Field(ge=0)
    vest_years: int | None = Field(default=None, gt=0)


class OfferItem(BaseModel):
    label: str = Field(min_length=1)
    base: int = Field(gt=0)
    bonus: int = Field(default=0, ge=0)
    equity: EquityGrant | None = None


class CompareOffersReq(BaseModel):
    role: str = Field(min_length=2)
    location: str | None = None
    seniority: str | None = None
    currency: str = "CNY"
    match_score: float | None = Field(default=None, ge=0, le=1)
    offers: list[OfferItem] = Field(min_length=1)


@router.post("/compare-offers")
async def compare_offers_ep(req: CompareOffersReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "compare_offers")
    samples = await salary_mod.load_job_samples()
    report = salary_mod.benchmark(samples, role=req.role, location=req.location,
                                  seniority=req.seniority, currency=req.currency)
    result = offers_mod.compare_offers([o.model_dump() for o in req.offers], report,
                                       match_score=req.match_score)
    await observability.finish_run(run_id, "completed")
    return result


class OutreachReq(BaseModel):
    name: str = Field(min_length=1)
    role: str = ""
    company: str = ""
    purpose: str = "referral"
    context: str = ""
    resume_version_id: str | None = None


@router.post("/outreach")
async def outreach_ep(req: OutreachReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "outreach", "outreach_message")
    try:
        structured, _ = await _resume_payload(ctx.user_id, req.resume_version_id)
    except HTTPException:
        structured = {}          # outreach does not require a resume; it just cites less
    contact = {"name": req.name, "role": req.role, "company": req.company}
    result = await outreach_mod.draft_message(contact, req.purpose, structured,
                                              context=req.context, user_id=ctx.user_id,
                                              run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return result


class ProgressReq(BaseModel):
    target_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None
    previous: dict | None = None


@router.post("/progress")
async def progress_ep(req: ProgressReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "learning", "progress")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    current = await gap_mod.analyze_gap(req.target_role, req.seniority, structured, plaintext,
                                        user_id=ctx.user_id, run_id=run_id)
    result = progress_mod.diff_progress(req.previous, current)
    await observability.finish_run(run_id, "completed")
    return result


class GrowthReportReq(BaseModel):
    target_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None
    location: str | None = None
    currency: str = "CNY"
    target_salary: int | None = None
    previous: dict | None = None


@router.post("/growth-report")
async def growth_report_ep(req: GrowthReportReq, ctx: Ctx = Depends(require_internal)):
    """One call for the whole growth page: readiness + gap + salary + learning plan +
    progress, so the bridge and the frontend need a single endpoint rather than seven."""
    run_id = await _run(ctx, "learning", "growth_report")
    structured, plaintext = await _resume_payload(ctx.user_id, req.resume_version_id)
    gap = await gap_mod.analyze_gap(req.target_role, req.seniority, structured, plaintext,
                                    user_id=ctx.user_id, run_id=run_id)
    samples = await salary_mod.load_job_samples()
    salary = salary_mod.benchmark(samples, role=req.target_role, location=req.location,
                                  seniority=req.seniority, target_salary=req.target_salary,
                                  currency=req.currency)
    result = growth_mod.build_growth_report(gap, salary, req.previous)
    await observability.finish_run(run_id, "completed")
    return result


class CounterOfferReq(BaseModel):
    role: str = Field(min_length=2)
    location: str | None = None
    seniority: str | None = None
    currency: str = "CNY"
    offer_base: int = Field(gt=0)
    match_score: float | None = Field(default=None, ge=0, le=1)


@router.post("/counter-offer")
async def counter_offer_ep(req: CounterOfferReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "counter_offer")
    samples = await salary_mod.load_job_samples()
    report = salary_mod.benchmark(samples, role=req.role, location=req.location,
                                  seniority=req.seniority, currency=req.currency)
    result = await counter_offer_mod.draft_counter_offer(
        req.offer_base, report, match_score=req.match_score, currency=req.currency,
        user_id=ctx.user_id, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return result


class SkillDemandReq(BaseModel):
    role: str = Field(min_length=2)
    location: str | None = None
    top: int = Field(default=15, ge=1, le=50)


@router.post("/skill-demand")
async def skill_demand_ep(req: SkillDemandReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "skill_demand")
    samples = await demand_mod.load_job_skill_samples()
    result = demand_mod.skill_demand(samples, role=req.role, location=req.location,
                                     top=req.top)
    await observability.finish_run(run_id, "completed")
    return result


class StoryBankReq(BaseModel):
    resume_version_id: str | None = None


@router.post("/story-bank")
async def story_bank_ep(req: StoryBankReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "resume", "story_bank")
    structured, _ = await _resume_payload(ctx.user_id, req.resume_version_id)
    result = stories_mod.build_story_bank(structured)
    await observability.finish_run(run_id, "completed")
    return result


class RoleSuggestReq(BaseModel):
    resume_version_id: str | None = None
    top: int = Field(default=8, ge=1, le=20)


@router.post("/role-suggestions")
async def role_suggestions_ep(req: RoleSuggestReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "role_suggestions")
    structured, _ = await _resume_payload(ctx.user_id, req.resume_version_id)
    samples = await demand_mod.load_job_skill_samples()
    result = roles_mod.suggest_roles(samples, roles_mod.declared_skills(structured),
                                     top=req.top)
    await observability.finish_run(run_id, "completed")
    return result


class CompanyBriefReq(BaseModel):
    company: str = Field(min_length=2)
    top: int = Field(default=10, ge=1, le=30)


class ProgressionReq(BaseModel):
    aspirational_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None


@router.post("/progression")
async def progression_ep(req: ProgressionReq, ctx: Ctx = Depends(require_internal)):
    """Stepping-stone roles toward a dream role: reachable *and* gap-closing."""
    run_id = await _run(ctx, "learning", "progression")
    structured, _ = await _resume_payload(ctx.user_id, req.resume_version_id)
    samples = await demand_mod.load_job_skill_samples()
    result = await progression_mod.plan_progression(
        aspirational_role=req.aspirational_role, resume_structured=structured,
        samples=samples, seniority=req.seniority, user_id=ctx.user_id, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return result


class LearningPriorityReq(BaseModel):
    target_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None


@router.post("/learning-priority")
async def learning_priority_ep(req: LearningPriorityReq, ctx: Ctx = Depends(require_internal)):
    """Rank the target role's gaps by importance and market pull -- learn what first."""
    run_id = await _run(ctx, "learning", "learning_priority")
    structured, _ = await _resume_payload(ctx.user_id, req.resume_version_id)
    samples = await demand_mod.load_job_skill_samples()
    result = await prioritize_mod.plan_learning_priority(
        target_role=req.target_role, resume_structured=structured, samples=samples,
        seniority=req.seniority, user_id=ctx.user_id, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return result


class InterviewPrepReq(BaseModel):
    target_role: str = Field(min_length=10)
    seniority: str | None = None
    resume_version_id: str | None = None


@router.post("/interview-prep")
async def interview_prep_ep(req: InterviewPrepReq, ctx: Ctx = Depends(require_internal)):
    """Pre-interview checklist: study the gaps, rehearse the strength stories."""
    run_id = await _run(ctx, "interview", "interview_prep")
    structured, _ = await _resume_payload(ctx.user_id, req.resume_version_id)
    result = await interview_prep_mod.plan_interview_prep(
        target_role=req.target_role, resume_structured=structured,
        seniority=req.seniority, user_id=ctx.user_id, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return result


@router.post("/company-brief")
async def company_brief_ep(req: CompanyBriefReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "company_brief")
    samples = await company_mod.load_company_samples()
    result = company_mod.company_brief(samples, req.company, top=req.top)
    await observability.finish_run(run_id, "completed")
    return result


class ApplicationInput(BaseModel):
    id: str
    status: str
    title: str | None = None
    company: str | None = None
    applied_at: str | None = None
    oa_at: str | None = None
    interview_at: str | None = None
    final_round_at: str | None = None
    offer_at: str | None = None
    created_at: str | None = None


class PipelineFunnelReq(BaseModel):
    applications: list[ApplicationInput] = Field(min_length=1)


@router.post("/pipeline-funnel")
async def pipeline_funnel_ep(req: PipelineFunnelReq, ctx: Ctx = Depends(require_internal)):
    """15.1 -- how many applications reached each stage and where the leak is."""
    run_id = await _run(ctx, "analytics", "pipeline_funnel")
    result = analytics_mod.pipeline_funnel([a.model_dump() for a in req.applications])
    await observability.finish_run(run_id, "completed")
    return result


class ResponseRateReq(BaseModel):
    applications: list[ApplicationInput] = Field(min_length=1)


@router.post("/response-rate")
async def response_rate_ep(req: ResponseRateReq, ctx: Ctx = Depends(require_internal)):
    """15.2 -- reply / interview / offer rates and per-stage durations."""
    run_id = await _run(ctx, "analytics", "response_rate")
    result = analytics_mod.response_rate([a.model_dump() for a in req.applications])
    await observability.finish_run(run_id, "completed")
    return result


class InsightDigestReq(BaseModel):
    """The digest's input. `applications` is optional because an account with no
    applications is a real state, not an error: the engine then answers "the
    funnel is empty", which is the honest digest for a workspace that has not
    started. A required list would make the first run a 422."""
    applications: list[ApplicationInput] = Field(default_factory=list)
    stale_days: int = Field(default=14, ge=1, le=120)
    growth_deltas: list[dict] | None = None
    top_matches: list[dict] | None = None


@router.post("/insight-digest")
async def insight_digest_ep(req: InsightDigestReq, ctx: Ctx = Depends(require_internal)):
    """15.3 -- weekly snapshot: stalled apps, live stage mix, headline rates."""
    run_id = await _run(ctx, "analytics", "insight_digest")
    result = analytics_mod.insight_digest(
        [a.model_dump() for a in req.applications], stale_days=req.stale_days,
        growth_deltas=req.growth_deltas, top_matches=req.top_matches)
    await observability.finish_run(run_id, "completed")
    return result


class DedupeJobsReq(BaseModel):
    postings: list[dict] = Field(min_length=1)


@router.post("/dedupe-jobs")
async def dedupe_jobs_ep(req: DedupeJobsReq, ctx: Ctx = Depends(require_internal)):
    """14.3 -- collapse the same posting seen from multiple sources to one survivor."""
    run_id = await _run(ctx, "ingestion", "dedupe_jobs")
    result = ingestion_mod.dedupe_postings(req.postings)
    await observability.finish_run(run_id, "completed")
    return result


class FreshnessSweepReq(BaseModel):
    postings: list[dict] = Field(min_length=1)
    max_age_days: int = Field(default=60, ge=1, le=365)
    stale_seen_days: int = Field(default=30, ge=1, le=365)


@router.post("/freshness-sweep")
async def freshness_sweep_ep(req: FreshnessSweepReq, ctx: Ctx = Depends(require_internal)):
    """14.3 -- split the corpus into fresh / stale (re-check) / expired (close)."""
    run_id = await _run(ctx, "ingestion", "freshness_sweep")
    result = ingestion_mod.freshness_sweep(req.postings, max_age_days=req.max_age_days,
                                           stale_seen_days=req.stale_seen_days)
    await observability.finish_run(run_id, "completed")
    return result


class PlanIngestReq(BaseModel):
    """The sweep plan's input. Exactly one of `postings` / `feed` carries the batch.

    `postings` is an already-parsed list; `feed` is the raw RSS/Atom XML or
    board-API JSON the caller got from a source, which the engine parses first.
    `plan_ingest` accepts either, so the route does too -- but exactly one, so a
    request cannot carry a batch and a feed that disagree.
    """
    postings: list[dict] | None = Field(default=None, min_length=1)
    feed: str | None = Field(default=None, min_length=1)
    existing: list[dict] | None = None
    source: str = "rss"
    max_age_days: int = Field(default=60, ge=1, le=365)
    stale_seen_days: int = Field(default=30, ge=1, le=365)


@router.post("/plan-ingest")
async def plan_ingest_ep(req: PlanIngestReq, ctx: Ctx = Depends(require_internal)):
    """14.3 -- one plan for a sweep: create / update / close + within-batch duplicates."""
    if (req.postings is None) == (req.feed is None):
        raise HTTPException(400, "send exactly one of postings / feed")
    run_id = await _run(ctx, "ingestion", "plan_ingest")
    result = ingestion_mod.plan_ingest(
        req.postings if req.postings is not None else req.feed,
        source=req.source, existing=req.existing,
        max_age_days=req.max_age_days, stale_seen_days=req.stale_seen_days)
    await observability.finish_run(run_id, "completed")
    return result


class HealthReportReq(BaseModel):
    """The health report's input. `runs` is optional for the same reason the
    digest's `applications` is: an account that has never run an agent is a real
    state, and the engine's answer for it is "nothing to report", not a 422."""
    runs: list[dict] = Field(default_factory=list)
    baseline_summary: dict | None = None
    usage_events: list[dict] | None = None
    current_metrics: dict | None = None
    baseline_metrics: dict | None = None
    tolerance: float = Field(default=0.2, gt=0, le=1)


@router.post("/health-report")
async def health_report_ep(req: HealthReportReq, ctx: Ctx = Depends(require_internal)):
    """16.1 -- agent health + cost + regression verdict over a window of runs."""
    run_id = await _run(ctx, "monitoring", "health_report")
    result = monitoring_mod.health_report(
        req.runs, baseline_summary=req.baseline_summary, usage_events=req.usage_events,
        current_metrics=req.current_metrics, baseline_metrics=req.baseline_metrics,
        tolerance=req.tolerance)
    await observability.finish_run(run_id, "completed")
    return result


class ParseBoardReq(BaseModel):
    payload: str = Field(min_length=2)
    source: str = "board"


@router.post("/parse-board")
async def parse_board_ep(req: ParseBoardReq, ctx: Ctx = Depends(require_internal)):
    """14.2 -- parse a board-API JSON payload into raw postings."""
    run_id = await _run(ctx, "ingestion", "parse_board")
    postings = ingestion_mod.parse_json_board(req.payload, source=req.source)
    await observability.finish_run(run_id, "completed")
    return {"postings": postings, "count": len(postings)}


class FollowUpsReq(BaseModel):
    include_fresh: bool = False
    limit: int = Field(default=15, ge=1, le=50)


@router.post("/follow-ups")
async def follow_ups_ep(req: FollowUpsReq, ctx: Ctx = Depends(require_internal)):
    """11.3 -- who in the caller's contacts has gone cold, ranked, each with a draft.

    The dashboard tile this feeds is the last half of 11.3: the ranking and the drafting
    are `features/reminders.follow_ups_for`, the read is
    `domain.list_contacts_for_follow_ups`, and the agent's `get_follow_ups` tool goes
    through the same two -- so the conversation and the tile cannot disagree about who is
    overdue. Nothing here invents a message: each draft cites only the contact's own name,
    company and relation.
    """
    run_id = await _run(ctx, "networking", "follow_ups")
    contacts = await domain.list_contacts_for_follow_ups(ctx.user_id, req.limit)
    ranked = reminders_mod.follow_ups_for(contacts, include_fresh=req.include_fresh)
    await observability.finish_run(run_id, "completed")
    return {"follow_ups": ranked, "count": len(ranked)}


class ExportBundleReq(BaseModel):
    """The export request.

    `sections` carries the rows the BACKEND owns -- `applications` and
    `growth_plans`. The ai-service cannot read them (it does not write them),
    so the bridge hands them over and the hash is computed here, over the whole
    bundle, in one place. A section the bridge did not send stays absent.
    """
    anonymized: bool = False
    sections: dict | None = None


@router.post("/export-bundle")
async def export_bundle_ep(req: ExportBundleReq, ctx: Ctx = Depends(require_internal)):
    """13.1 -- export all user data as a versioned, hashed bundle."""
    run_id = await _run(ctx, "export", "export_bundle")
    bundle = await export_mod.export_bundle(ctx.user_id, anonymized=req.anonymized,
                                            extra=req.sections)
    await observability.finish_run(run_id, "completed")
    return bundle


class ImportPlanReq(BaseModel):
    bundle: dict
    existing: dict | None = None


@router.post("/import-plan")
async def import_plan_ep(req: ImportPlanReq, ctx: Ctx = Depends(require_internal)):
    """13.2 -- plan an idempotent re-import from a bundle."""
    run_id = await _run(ctx, "import", "import_plan")
    plan = import_plan_mod.plan_import(req.bundle, existing=req.existing)
    await observability.finish_run(run_id, "completed")
    return plan


class RedactBundleReq(BaseModel):
    bundle: dict
    drop: list[str] | None = None


@router.post("/redact-bundle")
async def redact_bundle_ep(req: RedactBundleReq, ctx: Ctx = Depends(require_internal)):
    """13.3 -- redact sections from a bundle before sharing."""
    run_id = await _run(ctx, "export", "redact_bundle")
    result = export_redact_mod.redact_bundle(req.bundle, drop=req.drop)
    await observability.finish_run(run_id, "completed")
    return result
