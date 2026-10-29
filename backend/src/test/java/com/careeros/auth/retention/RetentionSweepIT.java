package com.careeros.auth.retention;

import static org.assertj.core.api.Assertions.assertThat;

import com.careeros.ApiIntegrationTest;
import java.time.OffsetDateTime;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;

/**
 * Roadmap 28.3: the sweep's delete and the index it rides are the database's facts, not the
 * mocks'. The unit tests pin the cutoff and the isolation; this one runs the JPQL against the
 * schema Flyway built, where a column renamed or an index dropped would never show up in a
 * fixture.
 *
 * <p>Each table carries two rows: one expired two months ago (past the thirty-day grace) and
 * one expired yesterday (inside it). Only the first may go — the second is the row a late
 * request or a support investigation still finds. The registration itself writes a refresh
 * token, so every count is scoped to this test's own hashes.
 */
class RetentionSweepIT extends ApiIntegrationTest {

    private static final OffsetDateTime NOW = OffsetDateTime.now();

    @Autowired
    private JdbcTemplate jdbc;

    @Autowired
    private RetentionSweeper sweeper;

    @Test
    void theSweepDeletesOnlyRowsPastTheGraceWindowAndKeepsTheIndexesThatCarryIt() throws Exception {
        String email = "retention-" + UUID.randomUUID() + "@example.com";
        register(email);
        UUID userId = jdbc.queryForObject("select id from users where email = ?", UUID.class, email);

        String expired = "retention-expired-" + UUID.randomUUID();
        String fresh = "retention-fresh-" + UUID.randomUUID();
        insertTokens(userId, expired, fresh);

        sweeper.sweep(NOW);

        for (String table : new String[]{RetentionSweeper.REFRESH_TOKENS,
                RetentionSweeper.PASSWORD_RESET_TOKENS, RetentionSweeper.EMAIL_CHANGE_TOKENS}) {
            assertThat(count(table, expired))
                    .as("%s kept a row expired two months ago", table).isZero();
            assertThat(count(table, fresh))
                    .as("%s deleted a row that is only a day past expiry", table).isEqualTo(1);
        }
        assertThat(index("idx_refresh_expires")).isEqualTo(1);
        assertThat(index("idx_reset_expires")).isEqualTo(1);
        assertThat(index("idx_email_change_expires")).isEqualTo(1);
    }

    private void insertTokens(UUID userId, String expired, String fresh) {
        for (Object[] pair : new Object[][]{{expired, NOW.minusDays(60)}, {fresh, NOW.minusDays(1)}}) {
            jdbc.update("insert into refresh_tokens (user_id, token_hash, family_id, expires_at) "
                    + "values (?, ?, ?, ?)", userId, pair[0], UUID.randomUUID(), pair[1]);
            jdbc.update("insert into password_reset_tokens (user_id, token_hash, expires_at) "
                    + "values (?, ?, ?)", userId, pair[0] + "-reset", pair[1]);
            jdbc.update("insert into email_change_tokens (user_id, token_hash, new_email, expires_at) "
                    + "values (?, ?, ?, ?)", userId, pair[0] + "-move",
                    "moved-" + UUID.randomUUID() + "@example.com", pair[1]);
        }
    }

    private int count(String table, String tokenHash) {
        Integer rows = jdbc.queryForObject("select count(*) from " + table + " where token_hash like ?",
                Integer.class, tokenHash + "%");
        return rows == null ? 0 : rows;
    }

    private int index(String name) {
        Integer rows = jdbc.queryForObject(
                "select count(*) from pg_indexes where schemaname = 'public' and indexname = ?",
                Integer.class, name);
        return rows == null ? 0 : rows;
    }
}
