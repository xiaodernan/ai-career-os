package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MvcResult;

/**
 * The account erasure against the real schema (roadmap 24.2).
 *
 * <p>This is the one claim mocks cannot make: the row delete really empties the workspace. The
 * test gives two accounts the same kinds of rows -- a document, its chunk, a knowledge source
 * pointing at the document, a mail preference, the refresh token registration issued -- puts a
 * file for each in the in-memory object store, and erases one of them through the public API.
 * Afterwards every user-scoped table is empty for the erased account, its file is gone from the
 * bucket, its refresh token no longer buys an access token, and the neighbour's rows and file
 * are untouched. The access token the erasure was made with still parses, and the next request
 * it makes is a 404 rather than a 500 or a leak: there is no account left for it to name.
 */
class AccountErasureIT extends ApiIntegrationTest {

    private static final String PASSWORD = "Str0ngPassphrase!23";

    @Autowired
    private JdbcTemplate jdbc;

    @Test
    void erasingAnAccountDeletesItsRowsItsFilesAndItsTokensAndLeavesTheNeighbourWhole() throws Exception {
        String aliceEmail = "erase-alice-" + UUID.randomUUID() + "@example.com";
        String bobEmail = "erase-bob-" + UUID.randomUUID() + "@example.com";
        JsonNode alice = registerFull(aliceEmail);
        JsonNode bob = registerFull(bobEmail);
        UUID aliceId = UUID.fromString(alice.path("user").path("id").asText());
        UUID bobId = UUID.fromString(bob.path("user").path("id").asText());
        String aliceAccess = alice.path("tokens").path("accessToken").asText();
        String aliceRefresh = alice.path("tokens").path("refreshToken").asText();
        String bobAccess = bob.path("tokens").path("accessToken").asText();

        String aliceKey = aliceId + "/notes/erase-me.txt";
        String bobKey = bobId + "/notes/stay.txt";
        UUID aliceDocument = insertDocument(aliceId, aliceKey, "erase me");
        UUID bobDocument = insertDocument(bobId, bobKey, "stay");
        assertThat(aliceDocument).isNotNull();
        assertThat(bobDocument).isNotNull();
        storage.put(aliceKey, "alice's file".getBytes(StandardCharsets.UTF_8), "text/plain");
        storage.put(bobKey, "bob's file".getBytes(StandardCharsets.UTF_8), "text/plain");
        // A forwarded reply is user data too: the erasure has to take the letters with the
        // account, or "no copy remains" would be false for every reader who configured one.
        // The id is the entity's own UUID generator, not a database default: a row written beside
        // Hibernate has to carry it.
        jdbc.update("insert into inbound_mails (id, user_id, message_key, from_address, subject, body_text, received_at) "
                        + "values (?, ?, ?, 'recruiter@example.com', 'Your application', 'Hello', now())",
                UUID.randomUUID(), aliceId, "erase-" + aliceId);
        jdbc.update("insert into inbound_mails (id, user_id, message_key, from_address, subject, body_text, received_at) "
                        + "values (?, ?, ?, 'recruiter@example.com', 'Your application', 'Hello', now())",
                UUID.randomUUID(), bobId, "stay-" + bobId);

        assertThat(count("select count(*) from documents where user_id = ?", aliceId)).isEqualTo(1);
        assertThat(count("select count(*) from refresh_tokens where user_id = ?", aliceId)).isEqualTo(1);
        assertThat(count("select count(*) from email_change_tokens where user_id = ?", aliceId)).isEqualTo(1);
        assertThat(count("select count(*) from user_mfa where user_id = ?", aliceId)).isEqualTo(1);
        assertThat(count("select count(*) from user_mfa_recovery_codes where user_id = ?", aliceId))
                .isEqualTo(1);
        assertThat(count("select count(*) from inbound_mails where user_id = ?", aliceId)).isEqualTo(1);
        assertThat(storage.store).containsKey(aliceKey);

        mvc.perform(post("/api/v1/me/erase")
                        .header("Authorization", "Bearer " + aliceAccess)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("password", PASSWORD, "confirmEmail", aliceEmail))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.erased").value(true));

        assertThat(count("select count(*) from users where id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from user_profiles where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from documents where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from document_chunks where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from knowledge_sources where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from mail_preferences where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from refresh_tokens where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from email_change_tokens where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from user_mfa where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from user_mfa_recovery_codes where user_id = ?", aliceId)).isZero();
        assertThat(count("select count(*) from inbound_mails where user_id = ?", aliceId)).isZero();
        assertThat(storage.store).doesNotContainKey(aliceKey);

        // The neighbour: every table and the bucket still hold what this account owns.
        assertThat(count("select count(*) from users where id = ?", bobId)).isEqualTo(1);
        assertThat(count("select count(*) from documents where user_id = ?", bobId)).isEqualTo(1);
        assertThat(count("select count(*) from refresh_tokens where user_id = ?", bobId)).isEqualTo(1);
        assertThat(count("select count(*) from user_mfa where user_id = ?", bobId)).isEqualTo(1);
        assertThat(count("select count(*) from user_mfa_recovery_codes where user_id = ?", bobId))
                .isEqualTo(1);
        assertThat(count("select count(*) from inbound_mails where user_id = ?", bobId)).isEqualTo(1);
        assertThat(storage.store).containsKey(bobKey);

        // The refresh token died with its row: there is no session left to rotate.
        mvc.perform(post("/api/v1/auth/refresh")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("refreshToken", aliceRefresh))))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error.code").value("TOKEN_INVALID"));

        // The access token still parses, and finds nothing to act on.
        mvc.perform(post("/api/v1/me/erase")
                        .header("Authorization", "Bearer " + aliceAccess)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(json(Map.of("password", PASSWORD, "confirmEmail", aliceEmail))))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error.code").value("USER_NOT_FOUND"));

        // The neighbour is signed in and whole, end to end.
        mvc.perform(get("/api/v1/me").header("Authorization", "Bearer " + bobAccess))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value(bobEmail));
    }

    private JsonNode registerFull(String email) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/register")
                        .header("X-Forwarded-For", freshIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"" + PASSWORD + "\","
                                + "\"displayName\":\"Erasure Tester\"}"))
                .andExpect(status().isCreated())
                .andReturn();
        return MAPPER.readTree(result.getResponse().getContentAsString()).path("data");
    }

    /**
     * A document with its chunk, a knowledge source pointing at the document, a mail
     * preference, an address move in flight and the second door's two rows -- one row in each
     * shape the cascade has to reach.
     */
    private UUID insertDocument(UUID userId, String fileKey, String title) {
        UUID documentId = jdbc.queryForObject(
                "insert into documents (user_id, file_key, media_type, content_hash, title) "
                        + "values (?, ?, 'text/plain', 'hash-" + userId + "', ?) returning id",
                UUID.class, userId, fileKey, title);
        jdbc.update("insert into document_chunks (document_id, user_id, ordinal, text) "
                + "values (?, ?, 0, 'a chunk of the note')", documentId, userId);
        jdbc.update("insert into knowledge_sources (user_id, kind, title, document_id) "
                + "values (?, 'note', ?, ?)", userId, title, documentId);
        jdbc.update("insert into mail_preferences (user_id, weekly_digest, signal_mail) "
                + "values (?, false, true)", userId);
        // A pending address move is a letter, not a row the erasure can leave behind.
        jdbc.update("insert into email_change_tokens (user_id, token_hash, new_email, expires_at) "
                        + "values (?, ?, ?, ?)", userId, "hash-" + userId,
                "moved-" + userId + "@example.invalid",
                java.time.OffsetDateTime.now().plusHours(2));
        // The seed and one printed code: the erasure reaches both tables or a second factor
        // outlives the account it guards.
        jdbc.update("insert into user_mfa (user_id, secret_ciphertext, active) values (?, ?, true)",
                userId, "sealed-" + userId);
        jdbc.update("insert into user_mfa_recovery_codes (id, user_id, code_hash) values (?, ?, ?)",
                UUID.randomUUID(), userId, "code-hash-" + userId);
        return documentId;
    }

    private long count(String sql, Object... args) {
        Long n = jdbc.queryForObject(sql, Long.class, args);
        return n == null ? 0 : n;
    }
}
