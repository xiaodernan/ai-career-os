package com.careeros.interview.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.interview.entity.InterviewTurn;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * Wire-contract lock for {@link InterviewService#toAiTurn}: the map it builds is POSTed to
 * ai-service, whose {@code features/interview.py} reads it with hard indexing — {@code t["role"]}
 * and {@code t["content"]} (a missing key is a KeyError / 500 on the AI side) and
 * {@code t.get("question_meta")} / {@code t["seq"]} by those exact snake_case names. A rename to
 * camelCase, or omitting a key when the entity field is null, silently breaks every interview.
 */
class InterviewServiceToAiTurnTest {

    private static InterviewTurn turn(int seq, String role, String content,
                                      Map<String, Object> meta, Map<String, Object> evaluation) {
        InterviewTurn t = new InterviewTurn();
        t.setSessionId(UUID.randomUUID());
        t.setUserId(UUID.randomUUID());
        t.setSeq(seq);
        t.setRole(role);
        t.setContent(content);
        t.setQuestionMeta(meta);
        t.setEvaluation(evaluation);
        return t;
    }

    @Test
    void emitsExactlyTheSnakeCaseKeysAiServiceReads() {
        Map<String, Object> meta = new LinkedHashMap<>();
        meta.put("topic", "系统设计");
        meta.put("depth_level", 1);
        InterviewTurn t = turn(2, "interviewer", "请介绍一个你主导的服务", meta, null);

        Map<String, Object> wire = InterviewService.toAiTurn(t);

        assertThat(wire).containsOnlyKeys("seq", "role", "content", "question_meta", "evaluation");
        // No camelCase leakage — ai-service would read null and drop the field silently.
        assertThat(wire).doesNotContainKeys("questionMeta", "depthLevel");
        assertThat(wire).containsEntry("seq", 2)
                .containsEntry("role", "interviewer")
                .containsEntry("content", "请介绍一个你主导的服务");
    }

    @Test
    void alwaysCarriesRoleAndContentKeysEvenWhenNull() {
        // ai-service does t["role"] / t["content"] (hard index): the KEY must exist even if the
        // value is null, otherwise the interview request 500s on the AI side.
        InterviewTurn t = turn(1, null, null, null, null);

        Map<String, Object> wire = InterviewService.toAiTurn(t);

        assertThat(wire).containsKeys("seq", "role", "content", "question_meta", "evaluation");
        assertThat(wire).containsEntry("role", null).containsEntry("content", null);
    }

    @Test
    void passesNestedJsonColumnsThroughByReferenceUnchanged() {
        Map<String, Object> meta = Map.of("topic", "concurrency", "depth_level", 0);
        Map<String, Object> evaluation = Map.of("score", 0.75);
        InterviewTurn t = turn(3, "candidate", "我用了线程池", meta, evaluation);

        Map<String, Object> wire = InterviewService.toAiTurn(t);

        // toAiTurn must not copy/reshape these — ai-service navigates their inner keys verbatim.
        assertThat(wire).containsEntry("question_meta", meta);
        assertThat(wire).containsEntry("evaluation", evaluation);
        assertThat(wire.get("question_meta")).isSameAs(meta);
        assertThat(wire.get("evaluation")).isSameAs(evaluation);
    }

    @Test
    void nullQuestionMetaStaysNullNotAnEmptyMap() {
        // ai-service guards with `(t.get("question_meta") or {}).get("topic")`, so an explicit
        // null is meaningful (turn had no question metadata) and must not be coerced to {}.
        InterviewTurn t = turn(4, "candidate", "answer", null, null);

        Map<String, Object> wire = InterviewService.toAiTurn(t);

        assertThat(wire.get("question_meta")).isNull();
    }
}
