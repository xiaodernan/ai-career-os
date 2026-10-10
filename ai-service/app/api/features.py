from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import Ctx, require_internal
from app.db import domain, observability
from app.features import gap_analysis as gap_mod
from app.features import jd_analyze as jd_an
from app.features import match as match_mod
from app.features import resume_parse as rp
from app.features import tailor as tailor_mod
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
