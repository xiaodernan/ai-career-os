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

    public record OpeningResponse(TurnItem question, SessionItem session) {
    }

    public record AnswerResponse(TurnItem candidateTurn, TurnItem followup,
                                 Map<String, Object> evaluation, Map<String, Object> next,
                                 SessionItem session) {
    }

    public record FinalizeResponse(EvaluationItem evaluation, SessionItem session) {
    }

    /**
     * 19.6 -- one recorded answer on its way to the speech provider. The audio
     * is base64 because it crosses the ai-service bridge as JSON; the cap is
     * the decoded 10 MB the renderer's sibling route enforces, in base64
     * characters. Voice is an enhancement: nothing about the interview's
     * scoring reads this record.
     */
    public record VoiceAnswerRequest(@NotBlank @Size(max = 14_000_000) String audio,
                                     @Size(max = 100) String mime,
                                     @Size(max = 16) String locale) {
    }

    /** 19.6 -- one question on its way to the speaker, capped at the ai-service's own limit. */
    public record VoiceLineRequest(@NotBlank @Size(max = 4000) String text,
                                   @Size(max = 16) String locale) {
    }

    /** The words of one answer, and which provider heard them. */
    public record VoiceTranscript(String text, String provider) {
    }

    /** One question as base64 audio, and the mime type the browser plays it as. */
    public record VoiceClip(String audio, String mime, String provider) {
    }

    /**
     * Whether this deployment can hear and speak. Both false leaves the browser
     * its own speech APIs -- the page chooses before it records, so a deployment
     * with no provider never uploads an answer that cannot be read.
     */
    public record VoiceState(String provider, boolean stt, boolean tts) {
    }
}
