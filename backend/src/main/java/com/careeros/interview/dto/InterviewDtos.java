package com.careeros.interview.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class InterviewDtos {

    private InterviewDtos() {
    }

    /**
     * `questionCount` and `overall` are aggregates over interview_turns / interview_evaluations:
     * the list row shows how far a session got and how it scored, and `overall` stays null when
     * no report exists (unknown is not zero). Null when the caller did not ask for digests.
     */
    public record SessionItem(UUID id, UUID jobId, UUID jdId, UUID resumeVersionId,
                              String companyName, String positionTitle, String mode, String status,
                              float difficulty, Map<String, Object> config, OffsetDateTime startedAt,
                              OffsetDateTime finishedAt, Integer questionCount, Float overall) {
    }

    public record TurnItem(UUID id, int seq, String role, String content,
                           Map<String, Object> questionMeta, Map<String, Object> evaluation,
                           OffsetDateTime createdAt) {
    }

    public record EvaluationItem(UUID id, Map<String, Object> dims, Map<String, Object> summary,
                                 List<Object> trajectory, OffsetDateTime createdAt) {
    }

    public record SessionDetail(SessionItem session, List<TurnItem> turns, EvaluationItem evaluation) {
    }

    public record CreateSessionRequest(@JsonAlias("job_id") UUID jobId,
                                       @JsonAlias("jd_id") UUID jdId,
                                       @JsonAlias("resume_version_id") UUID resumeVersionId,
                                       @JsonAlias("company_name") String companyName,
                                       @JsonAlias("position_title") String positionTitle,
                                       @Size(max = 32) String mode,
                                       Map<String, Object> config) {
    }

    public record AnswerRequest(@NotBlank String answer) {
    }

    public record TurnPayload(int seq, String role, String content,
                              @JsonAlias("question_meta") Map<String, Object> questionMeta,
                              @JsonAlias("evaluation") Map<String, Object> evaluation) {
    }

    public record OpeningResponse(TurnItem question, SessionItem session) {
    }

    public record AnswerResponse(TurnItem candidateTurn, TurnItem followup,
                                 Map<String, Object> evaluation, Map<String, Object> next,
                                 SessionItem session) {
    }

    public record FinalizeResponse(EvaluationItem evaluation, SessionItem session) {
    }
}
