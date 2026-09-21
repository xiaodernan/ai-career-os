package com.careeros;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.BeforeAll;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Integration tests run against localhost infrastructure instead of Testcontainers:
 * on this Windows/Docker-Desktop 29 machine every docker-java npipe strategy returns
 * HTTP 400 from the Desktop pipe proxy ("Could not find a valid Docker environment"),
 * while the plain docker CLI works. Fallback per task instructions:
 *  - Postgres: the project's careeros-postgres container, dedicated database `career_os_it`
 *    (created + schema-reset here; the dev `career_os` DB is never touched).
 *  - Redis: dedicated `careeros-it-redis` container on 127.0.0.1:16399 (host 6379 is taken
 *    by an unrelated project), started idempotently and flushed before the suite.
 * Object storage (MinIO) is disabled — not needed for this suite.
 * To restore Testcontainers once the Desktop proxy issue is fixed, reintroduce
 * PostgreSQLContainer/GenericContainer with @DynamicPropertySource as before.
 */
@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = "app.storage.enabled=false")
public abstract class AbstractIntegrationTest {

    private static final String PG_ADMIN_URL = "jdbc:postgresql://localhost:5432/postgres";
    private static final String PG_IT_URL = "jdbc:postgresql://localhost:5432/career_os_it";
    private static final String PG_USER = "career_os";
    private static final String PG_PASS = "dev_pg_pass_9f3k";
    private static final String REDIS_CONTAINER = "careeros-it-redis";
    private static final int REDIS_PORT = 16399;

    static {
        try {
            ensureItDatabase();
            ensureItRedis();
        } catch (Exception e) {
            throw new IllegalStateException("IT infrastructure bootstrap failed (local postgres/redis)", e);
        }
    }

    private static void ensureItDatabase() throws Exception {
        try (Connection admin = DriverManager.getConnection(PG_ADMIN_URL, PG_USER, PG_PASS);
             Statement st = admin.createStatement()) {
            try (ResultSet rs = st.executeQuery(
                    "SELECT 1 FROM pg_database WHERE datname = 'career_os_it'")) {
                if (!rs.next()) {
                    st.execute("CREATE DATABASE career_os_it OWNER " + PG_USER);
                }
            }
        }
        // Deterministic schema: Flyway V1 rebuilds it from scratch on every suite run.
        try (Connection it = DriverManager.getConnection(PG_IT_URL, PG_USER, PG_PASS);
             Statement st = it.createStatement()) {
            st.execute("DROP SCHEMA public CASCADE");
            st.execute("CREATE SCHEMA public");
            st.execute("ALTER SCHEMA public OWNER TO " + PG_USER);
        }
    }

    private static void ensureItRedis() throws Exception {
        if (dockerInspectExists(REDIS_CONTAINER)) {
            runDocker(15, "docker", "start", REDIS_CONTAINER);
        } else {
            runDocker(60, "docker", "run", "-d", "--name", REDIS_CONTAINER,
                    "-p", "127.0.0.1:" + REDIS_PORT + ":6379", "redis:7.4-alpine");
        }
        LettuceConnectionFactory factory = new LettuceConnectionFactory("127.0.0.1", REDIS_PORT);
        factory.afterPropertiesSet();
        factory.getConnection().serverCommands().flushAll();
        factory.destroy();
    }

    private static boolean dockerInspectExists(String name) throws Exception {
        Process p = new ProcessBuilder("docker", "inspect", "-f", "{{.Id}}", name)
                .redirectErrorStream(true).start();
        boolean done = p.waitFor(15, TimeUnit.SECONDS);
        return done && p.exitValue() == 0;
    }

    private static void runDocker(int timeoutSeconds, String... cmd) throws Exception {
        Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
        if (!p.waitFor(timeoutSeconds, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            throw new IllegalStateException("docker command timed out: " + String.join(" ", cmd));
        }
        if (p.exitValue() != 0) {
            throw new IllegalStateException("docker command failed (" + p.exitValue() + "): "
                    + String.join(" ", cmd) + " / "
                    + new String(p.getInputStream().readAllBytes()));
        }
    }

    @DynamicPropertySource
    static void infrastructure(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> PG_IT_URL);
        registry.add("spring.datasource.username", () -> PG_USER);
        registry.add("spring.datasource.password", () -> PG_PASS);
        registry.add("spring.data.redis.url", () -> "redis://127.0.0.1:" + REDIS_PORT + "/0");
    }

    @BeforeAll
    static void requireInfrastructure() {
        // static initializer above already validated bootstrap; kept for a clear failure point
    }

    @Autowired
    protected MockMvc mvc;
}
