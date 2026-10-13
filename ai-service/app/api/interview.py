from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents import memory
from app.core.deps import Ctx, require_internal
from app.db import domain, observability
from app.features import interview as iv

router = APIRouter(prefix="/internal/interview", tags=["interview"])


class Turn(BaseModel):
    seq: int = 0
    role: str
    content: str
    question_meta: dict | None = None
    evaluation: dict | None = None


class StartReq(BaseModel):
    session_id: str


class AnswerReq(BaseModel):
    session_id: str
    answer: str = Field(min_length=1)
    question: str = ""
    turns: list[Turn] = Field(default_factory=list)


class FinalizeReq(BaseModel):
    session_id: str
    turns: list[Turn]


async def _session_ctx(session_id: str, user_id: str) -> tuple[dict, str, dict]:
    s = await domain.get_interview_session(session_id, user_id)
    if not s:
        raise HTTPException(404, "session not found")
    rv = (await domain.get_resume_version(str(s["resume_version_id"]), user_id)
          if s.get("resume_version_id") else None)
    text = (rv or {}).get("plaintext") or ""
    jd_topics: list[str] = []
    if s.get("jd_id"):
        jd = await domain.get_jd(str(s["jd_id"]), user_id)
        import json

        parsed = (jd or {}).get("parsed")
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        jd_topics = ((parsed or {}).get("interviewTopics") or [])
    resume_ctx = text or "no resume provided"
    return s, resume_ctx, {"jd_topics": jd_topics}


@router.post("/opening")
async def opening(req: StartReq, ctx: Ctx = Depends(require_internal)):
    run_id = ctx.run_id or await observability.create_run(ctx.user_id, "interview",
                                                          "interview_open")
    s, resume_ctx, extra = await _session_ctx(req.session_id, ctx.user_id)
    out = await iv.opening_question(
        mode=s.get("mode") or "mixed",
        company=s.get("company_name") or s.get("company") or "",
        position=s.get("position_title") or s.get("job_title") or "",
        resume_ctx=resume_ctx, jd_topics=extra["jd_topics"] or ["your background"],
        user_id=ctx.user_id, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return out


@router.post("/answer")
async def answer(req: AnswerReq, ctx: Ctx = Depends(require_internal)):
    run_id = ctx.run_id or await observability.create_run(ctx.user_id, "interview",
                                                          "interview_answer")
    s, resume_ctx, extra = await _session_ctx(req.session_id, ctx.user_id)
    question = req.question
    if not question:
        for t in reversed(req.turns):
            if t.role == "interviewer":
                question = t.content
                break
    evaluation = await iv.evaluate_answer(mode=s.get("mode") or "mixed",
                                          question=question or "(opening)",
                                          answer=req.answer, resume_ctx=resume_ctx,
                                          user_id=ctx.user_id, run_id=run_id)
    turns = [t.model_dump() for t in req.turns] + [
        {"seq": len(req.turns) + 1, "role": "candidate", "content": req.answer}]
    qnum = sum(1 for t in turns if t["role"] == "interviewer")
    max_q = int((s.get("config") or {}).get("max_questions", 8)) if isinstance(
        s.get("config"), dict) else 8
    nxt = await iv.advance(mode=s.get("mode") or "mixed", turns=turns,
                           difficulty=float(s.get("difficulty") or 0.5), qnum=qnum,
                           max_q=max_q, resume_ctx=resume_ctx,
                           jd_topics=extra["jd_topics"], user_id=ctx.user_id,
                           run_id=run_id)
    await observability.trace(run_id, "message", "interview", {
        "stage": "answer_eval", "score": evaluation.get("score"),
        "next_action": nxt["action"], "difficulty": nxt["difficulty"]})
    await observability.finish_run(run_id, "completed")
    return {"evaluation": evaluation, "next": nxt}


@router.post("/finalize")
async def finalize(req: FinalizeReq, ctx: Ctx = Depends(require_internal)):
    run_id = ctx.run_id or await observability.create_run(ctx.user_id, "interview",
                                                          "interview_finalize")
    s, resume_ctx, _ = await _session_ctx(req.session_id, ctx.user_id)
    turns = [t.model_dump() for t in req.turns]
    out = await iv.finalize(mode=s.get("mode") or "mixed", turns=turns,
                            resume_ctx=resume_ctx, user_id=ctx.user_id, run_id=run_id)
    # The report is the one finding that should outlive the session (§17 lists
    # `interview` as a long-term memory kind but nothing could write one). Best-effort:
    # a failed write must not fail the finalize the user is waiting on.
    await memory.record_interview_outcome(ctx.user_id, req.session_id, out, run_id=run_id)
    await observability.finish_run(run_id, "completed")
    return {"evaluation": out}
