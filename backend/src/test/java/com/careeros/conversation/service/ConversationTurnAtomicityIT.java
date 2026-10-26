package com.careeros.conversation.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.groups.Tuple.tuple;

import com.careeros.ApiIntegrationTest;
import com.careeros.auth.repository.UserRepository;
import com.careeros.conversation.dto.ConversationDtos.ChatResponse;
import com.careeros.conversation.dto.ConversationDtos.ConversationItem;
import com.careeros.conversation.dto.ConversationDtos.CreateConversationRequest;
import com.careeros.conversation.entity.Conversation;
import com.careeros.conversation.entity.Message;
import com.careeros.conversation.repository.ConversationRepository;
import com.careeros.conversation.repository.MessageRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * One copilot turn is three rows: the question, the answer, and the conversation's own row, which
 * {@code persistTurn} retitles from "New chat" once the question is known. {@code
 * ConversationService.chat} reached that writer through a call on itself -- the one route Spring's
 * proxy does not intercept -- so its {@code @Transactional} never armed and each row committed
 * alone. A turn that cannot finish therefore filed the part it managed, and the reader is left with
 * a question and no answer under it: the copilot page renders that as an empty assistant bubble and
 * the sidebar digest counts it as a message.
 *
 * <p>The refusal used here is the database's own rather than an installed stand-in: {@code
 * messages.content} is {@code text}, and PostgreSQL takes no null character in one, so an answer
 * carrying it is refused at its INSERT after the question row is already filed. No shipped route is
 * claimed as the producer of that character -- ai-service's ingestion {@code clean()} strips control
 * characters from extracted document text -- so the case installs the value on the fake's answer and
 * grades the boundary, which is where a deadlock, a dropped connection or a refused row would land
 * just the same. {@link com.careeros.resume.service.ResumeParseAtomicityIT} is the sibling that has
 * to install a trigger instead, because nothing in that chain refuses a row at all.
 *
 * <p>The last case holds the other half of the boundary. {@code beginTurn} files the conversation
 * before the model is called, and the model call stays outside the transaction so that no pooled
 * connection waits on ai-service; a turn refused at its answer row must therefore still leave the
 * conversation the caller can come back to. Arming the whole of {@code chat}, writes and model call
 * together, would roll that row up as well, and this case would say so.
 */
class ConversationTurnAtomicityIT extends ApiIntegrationTest {

    @Autowired
    private ConversationService conversations;
    @Autowired
    private ConversationRepository conversationRows;
    @Autowired
    private MessageRepository messageRows;
    @Autowired
    private UserRepository users;

    private final UUID runId = UUID.randomUUID();
    /** Short enough that the turn's title claim and the question are the same string. */
    private final String question = "Lead with K8s? " + runId;

    private UUID userId;
    private UUID conversationId;

    @BeforeEach
    void openAConversation() throws Exception {
        String email = "turn-atomic-" + runId + "@example.test";
        register(email);
        userId = users.findByEmail(email).orElseThrow().getId();
        conversationId = conversations.create(userId, new CreateConversationRequest(null, null)).id();
    }

    private List<Message> rows() {
        return messageRows.findByConversationIdOrderByCreatedAtAsc(conversationId);
    }

    private Conversation row() {
        return conversationRows.findById(conversationId).orElseThrow();
    }

    private List<UUID> myConversations() {
        return conversations.list(userId, 0, 20).items().stream()
                .map(ConversationItem::id).toList();
    }

    /**
     * An answer the database itself refuses. The character is built rather than written as an
     * escape, so no null byte sits in this file; the refusal lands on the assistant row, which is
     * the second of the turn's three writes.
     */
    private void answerTheDatabaseRefuses() {
        ai.copilotAnswer = "Prioritise Kubernetes" + (char) 0 + " for this role.";
    }

    @Test
    @DisplayName("a turn files its question, its answer and the conversation's title")
    void aSuccessfulTurnFilesTheWholeTurn() {
        ChatResponse reply = conversations.chat(userId, conversationId, question, Map.of());

        assertThat(rows()).as("the rows the reply names").hasSize(2);
        assertThat(rows()).extracting(Message::getId)
                .containsExactlyInAnyOrder(reply.userMessageId(), reply.assistantMessageId());
        assertThat(rows()).extracting(Message::getRole, Message::getContent)
                .containsExactlyInAnyOrder(tuple("user", question),
                        tuple("assistant", reply.answer()));
        assertThat(row().getTitle())
                .as("a conversation opened with the default title takes its question")
                .isEqualTo(question);
    }

    @Test
    @DisplayName("a refused answer row leaves the question unfiled too")
    void aRefusedAnswerRowLeavesNoQuestionBehind() {
        answerTheDatabaseRefuses();

        assertThatThrownBy(() -> conversations.chat(userId, conversationId, question, Map.of()))
                .isInstanceOf(RuntimeException.class);

        assertThat(rows())
                .as("the question stayed behind the answer that could not be filed")
                .isEmpty();
        assertThat(row().getTitle())
                .as("the retitling that never ran had not been committed either")
                .isEqualTo("New chat");
    }

    @Test
    @DisplayName("a refused answer still leaves the conversation the turn opened")
    void aRefusedAnswerKeepsTheConversationTheTurnOpened() {
        answerTheDatabaseRefuses();

        assertThatThrownBy(() -> conversations.chat(userId, null, question, Map.of()))
                .isInstanceOf(RuntimeException.class);

        List<UUID> mine = myConversations();
        assertThat(mine).as("the conversation beginTurn filed before the model ran").hasSize(2);
        UUID opened = mine.stream().filter(id -> !id.equals(conversationId)).findFirst().orElseThrow();
        assertThat(messageRows.findByConversationIdOrderByCreatedAtAsc(opened))
                .as("the opened conversation holds half a turn")
                .isEmpty();
        assertThat(row().getTitle())
                .as("the conversation the caller already had was not touched by the failed turn")
                .isEqualTo("New chat");
    }
}
