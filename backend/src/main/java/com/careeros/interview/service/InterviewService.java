package com.careeros.interview.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.common.Json;
import com.careeros.common.PageDTO;
import com.careeros.interview.dto.InterviewDtos.AnswerResponse;
import com.careeros.interview.dto.InterviewDtos.CreateSessionRequest;
import com.careeros.interview.dto.InterviewDtos.EvaluationItem;
import com.careeros.interview.dto.InterviewDtos.FinalizeResponse;
import com.careeros.interview.dto.InterviewDtos.OpeningResponse;
import com.careeros.interview.dto.InterviewDtos.SessionDetail;
import com.careeros.interview.dto.InterviewDtos.SessionItem;
import com.careeros.interview.dto.InterviewDtos.TurnItem;
import com.careeros.interview.entity.InterviewEvaluation;
import com.careeros.interview.entity.InterviewSession;
import com.careeros.interview.entity.InterviewTurn;
import com.careeros.interview.repository.InterviewDigestRepository;
import com.careeros.interview.repository.InterviewDigestRepository;
import com.careeros.interview.repository.InterviewEvaluationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.interview.repository.InterviewTurnRepository;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobRepository;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Mock-interview orchestration: backend owns session/turn rows, ai-service answers. */
@Service
public class InterviewService {

    private final InterviewSessionRepository sessions;
    private final InterviewTurnRepository turns;
    private final InterviewEvaluationRepository evaluations;
    private final JobRepository jobs;
    private final CompanyRepository companies;
    private final InterviewDigestRepository digests;
    private final AiServiceClient ai;

    public InterviewService(InterviewSessionRepository sessions, InterviewTurnRepository turns,
                            InterviewEvaluationRepository evaluations, JobRepository jobs,
                            CompanyRepository companies, InterviewDigestRepository digests,
                            AiServiceClient ai) {
        this.sessions = sessions;
        this.turns = turns;
        this.evaluations = evaluations;
        this.jobs = jobs;
        this.companies = companies;
        this.digests = digests;
        this.ai = ai;
    }

    @Transactional(readOnly = true)
    public PageDTO<SessionItem> list(UUID userId, int page, int size) {
        var result = sessions.findByUserIdOrderByStartedAtDesc(userId, PageRequest.of(page, size));
        // Two grouped reads for the whole page; a per-row query would scale with the board.
        Map<UUID, InterviewDigestRepository.Digest> rows = digests.forSessions(
                result.getContent().stream().map(InterviewSession::getId).toList());
        return PageDTO.from(result,
                s -> toItem(s, rows.getOrDefault(s.getId(), InterviewDigestRepository.Digest.UNKNOWN)));
    }

    @Transactional(readOnly = true)
    public SessionDetail detail(UUID userId, UUID sessionId) {
        InterviewSession session = require(userId, sessionId);
        return new SessionDetail(toItem(session),
                turns.findBySessionIdOrderBySeqAsc(sessionId).stream().map(InterviewService::toTurnItem).toList(),
                evaluations.findBySessionId(sessionId)
                        .map(e -> new EvaluationItem(e.getId(), e.getDims(), e.getSummary(),
                                e.getTrajectory(), e.getCreatedAt()))
                        .orElse(null));
    }

    @Transactional
    public SessionItem create(UUID userId, CreateSessionRequest request) {
        InterviewSession session = new InterviewSession();
        session.setUserId(userId);
        session.setJobId(request.jobId());
        session.setJdId(request.jdId());
        session.setResumeVersionId(request.resumeVersionId());
        session.setCompanyName(request.companyName());
        session.setPositionTitle(request.positionTitle());
        // The UI starts a job-targeted session with only job_id, so without this copy the row
        // is born without a role or company and every screen naming the target stays blank.
        // Text the caller supplied wins — including text the job cannot know about — and a
        // job row that is gone (job_id has ON DELETE SET NULL) leaves the fields untouched.
        if (request.jobId() != null) {
            jobs.findById(request.jobId()).ifPresent(job -> {
                if (isBlank(request.positionTitle())) {
                    session.setPositionTitle(job.getTitle());
                }
                if (isBlank(request.companyName())) {
                    companies.findById(job.getCompanyId())
                            .ifPresent(c -> session.setCompanyName(c.getName()));
                }
            });
        }
        if (request.mode() != null && !request.mode().isBlank()) {
            session.setMode(request.mode());
        }
        session.setConfig(request.config());
        sessions.save(session);
        return toItem(session);
    }

    @Transactional
    public SessionItem update(UUID userId, UUID sessionId, Map<String, Object> patch) {
        InterviewSession session = require(userId, sessionId);
        String status = Json.str(patch, "status");
        if (status != null) {
            session.setStatus(status);
        }
        String mode = Json.str(patch, "mode");
        if (mode != null) {
            session.setMode(mode);
        }
        Double difficulty = Json.dbl(patch, "difficulty");
        if (difficulty != null) {
            session.setDifficulty(difficulty.floatValue());
        }
        if (patch.get("config") instanceof Map<?, ?>) {
            session.setConfig(Json.obj(patch.get("config")));
        }
        return toItem(sessions.save(session));
    }

    @Transactional
    public void delete(UUID userId, UUID sessionId) {
        sessions.delete(require(userId, sessionId));
    }

    public OpeningResponse opening(UUID userId, UUID sessionId) {
        InterviewSession session = requireReadOnly(userId, sessionId);
        if (!turns.findBySessionIdOrderBySeqAsc(sessionId).isEmpty()) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Session already has turns");
        }
        Map<String, Object> result = ai.interviewOpening(sessionId, userId);
        String question = Json.strOr(result, "question", "");
        TurnItem saved = persistTurn(sessionId, userId, 1, "interviewer", question,
                Json.obj(result.get("meta")));
        return new OpeningResponse(saved, toItem(session));
    }

    public AnswerResponse answer(UUID userId, UUID sessionId, String answer) {
        InterviewSession session = requireReadOnly(userId, sessionId);
        List<InterviewTurn> existing = turns.findBySessionIdOrderBySeqAsc(sessionId);
        if (existing.isEmpty()) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Start the interview with an opening question first");
        }
        InterviewTurn lastQuestion = lastInterviewerTurn(existing);
        int nextSeq = existing.get(existing.size() - 1).getSeq() + 1;
        List<Map<String, Object>> payload = existing.stream().map(InterviewService::toAiTurn).toList();

        Map<String, Object> result = ai.interviewAnswer(sessionId, answer,
                lastQuestion.getContent(), payload, userId);
        Map<String, Object> evaluation = Json.obj(result.get("evaluation"));
        Map<String, Object> next = Json.obj(result.get("next"));

        TurnItem candidateTurn = persistTurnAnswer(sessionId, userId, nextSeq, answer, evaluation);
        TurnItem followup = null;
        String question = Json.str(next, "question");
        if (question != null && !question.isBlank() && !"finish".equals(Json.str(next, "action"))) {
            Map<String, Object> meta = new HashMap<>();
            meta.put("topic", Json.strOr(next, "topic", ""));
            meta.put("depth_level", "followup".equals(Json.str(next, "action")) ? 1 : 0);
            meta.put("action", Json.strOr(next, "action", "next_topic"));
            meta.put("reasoning", Json.str(next, "reasoning"));
            followup = persistTurn(sessionId, userId, nextSeq + 1, "interviewer", question, meta);
        }

        Double difficulty = Json.dbl(next, "difficulty");
        if (difficulty != null) {
            session.setDifficulty(difficulty.floatValue());
            sessions.save(session);
        }
        return new AnswerResponse(candidateTurn, followup, evaluation, next, toItem(session));
    }

    public FinalizeResponse finalize(UUID userId, UUID sessionId) {
        InterviewSession session = requireReadOnly(userId, sessionId);
        List<InterviewTurn> existing = turns.findBySessionIdOrderBySeqAsc(sessionId);
        if (existing.isEmpty()) {
            throw new ApiException(ApiErrorCode.BAD_REQUEST, "Nothing to finalize");
        }
        Map<String, Object> result = ai.interviewFinalize(sessionId,
                existing.stream().map(InterviewService::toAiTurn).toList(), userId);
        Map<String, Object> evaluation = Json.obj(result.get("evaluation"));
        return persistFinalization(sessionId, userId, session, evaluation);
    }

    @Transactional
    public FinalizeResponse persistFinalization(UUID sessionId, UUID userId, InterviewSession session,
                                                Map<String, Object> evaluation) {
        InterviewEvaluation entity = evaluations.findBySessionId(sessionId).orElseGet(() -> {
            InterviewEvaluation e = new InterviewEvaluation();
            e.setSessionId(sessionId);
            e.setUserId(userId);
            return e;
        });
        entity.setDims(Json.obj(evaluation.get("dims")));
        Map<String, Object> summary = new HashMap<>();
        for (String key : List.of("what_you_did_well", "what_was_weak", "missing_concepts",
                "better_answers", "follow_up_questions_to_prepare", "recommended_study",
                "overall", "trajectory_note")) {
            if (evaluation.containsKey(key)) {
                summary.put(key, evaluation.get(key));
            }
        }
        entity.setSummary(summary);
        entity.setTrajectory(Json.arr(evaluation.get("trajectory_detail")));
        evaluations.save(entity);

        session.setStatus("completed");
        session.setFinishedAt(OffsetDateTime.now());
        sessions.save(session);
        return new FinalizeResponse(
                new EvaluationItem(entity.getId(), entity.getDims(), entity.getSummary(),
                        entity.getTrajectory(), entity.getCreatedAt()),
                toItem(session));
    }

    public InterviewSession requireReadOnly(UUID userId, UUID sessionId) {
        return sessions.findByIdAndUserId(sessionId, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.SESSION_NOT_FOUND, "Interview session not found"));
    }

    @Transactional
    public InterviewSession require(UUID userId, UUID sessionId) {
        return requireReadOnly(userId, sessionId);
    }

    private InterviewTurn lastInterviewerTurn(List<InterviewTurn> turns) {
        for (int i = turns.size() - 1; i >= 0; i--) {
            if ("interviewer".equals(turns.get(i).getRole())) {
                return turns.get(i);
            }
        }
        throw new ApiException(ApiErrorCode.BAD_REQUEST, "No interviewer question on record");
    }

    private TurnItem persistTurn(UUID sessionId, UUID userId, int seq, String role, String content,
                                 Map<String, Object> meta) {
        InterviewTurn turn = new InterviewTurn();
        turn.setSessionId(sessionId);
        turn.setUserId(userId);
        turn.setSeq(seq);
        turn.setRole(role);
        turn.setContent(content);
        turn.setQuestionMeta(meta);
        turns.save(turn);
        return toTurnItem(turn);
    }

    private TurnItem persistTurnAnswer(UUID sessionId, UUID userId, int seq, String content,
                                       Map<String, Object> evaluation) {
        InterviewTurn turn = new InterviewTurn();
        turn.setSessionId(sessionId);
        turn.setUserId(userId);
        turn.setSeq(seq);
        turn.setRole("candidate");
        turn.setContent(content);
        turn.setEvaluation(evaluation);
        turns.save(turn);
        return toTurnItem(turn);
    }

    static Map<String, Object> toAiTurn(InterviewTurn t) {
        Map<String, Object> map = new HashMap<>();
        map.put("seq", t.getSeq());
        map.put("role", t.getRole());
        map.put("content", t.getContent());
        map.put("question_meta", t.getQuestionMeta());
        map.put("evaluation", t.getEvaluation());
        return map;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    static SessionItem toItem(InterviewSession s) {
        return toItem(s, InterviewDigestRepository.Digest.UNKNOWN);
    }

    static SessionItem toItem(InterviewSession s, InterviewDigestRepository.Digest digest) {
        return new SessionItem(s.getId(), s.getJobId(), s.getJdId(), s.getResumeVersionId(),
                s.getCompanyName(), s.getPositionTitle(), s.getMode(), s.getStatus(),
                s.getDifficulty(), s.getConfig(), s.getStartedAt(), s.getFinishedAt(),
                digest.questions(), digest.overall());
    }

    static TurnItem toTurnItem(InterviewTurn t) {
        return new TurnItem(t.getId(), t.getSeq(), t.getRole(), t.getContent(), t.getQuestionMeta(),
                t.getEvaluation(), t.getCreatedAt());
    }
}
