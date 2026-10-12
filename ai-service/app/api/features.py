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
from app.features import resume_parse as rp
from app.features import roles as roles_mod
from app.features import salary as salary_mod
from app.features import stories as stories_mod
from app.features import tailor as tailor_mod
from app.features import counter_offer as counter_offer_mod
from app.features import demand as demand_mod
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


@router.post("/company-brief")
async def company_brief_ep(req: CompanyBriefReq, ctx: Ctx = Depends(require_internal)):
    run_id = await _run(ctx, "job_research", "company_brief")
    samples = await company_mod.load_company_samples()
    result = company_mod.company_brief(samples, req.company, top=req.top)
    await observability.finish_run(run_id, "completed")
    return result
