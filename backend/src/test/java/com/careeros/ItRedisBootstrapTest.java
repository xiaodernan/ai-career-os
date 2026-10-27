package com.careeros;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Witnesses the IT bootstrap's container bookkeeping against a fake CLI: no docker, no Spring,
 * so the offline gate can run it. The conflict text is the one the real CLI produced against an
 * already-running careeros-it-redis (exit 125).
 */
class ItRedisBootstrapTest {

    private static final String CONFLICT =
            "docker command failed (125): docker run -d --name careeros-it-redis / "
                    + "docker: Error response from daemon: Conflict. The container name "
                    + "\"/careeros-it-redis\" is already in use by container \"51d3...\".";

    private static final String[] RUN_ARGS = {
        "run", "-d", "--name", "careeros-it-redis",
        "-p", "127.0.0.1:16399:6379", "redis:7.4-alpine"
    };
    private static final String RUN_CALL = String.join(" ", RUN_ARGS);

    @Test
    void the_container_that_is_already_there_is_started_not_recreated() throws Exception {
        FakeDocker docker = new FakeDocker(true);

        ItInfrastructure.ensureContainer(docker, "careeros-it-redis", RUN_ARGS);

        assertThat(docker.calls).containsExactly("exists careeros-it-redis", "start careeros-it-redis");
    }

    @Test
    void a_missing_container_is_created_from_the_run_arguments() throws Exception {
        FakeDocker docker = new FakeDocker(false);

        ItInfrastructure.ensureContainer(docker, "careeros-it-redis", RUN_ARGS);

        assertThat(docker.calls).containsExactly("exists careeros-it-redis", RUN_CALL);
    }

    @Test
    void a_probe_that_lies_about_a_running_container_does_not_fail_the_suite() throws Exception {
        FakeDocker docker = new FakeDocker(false);
        docker.runFailure = CONFLICT;

        assertThatCode(() -> ItInfrastructure.ensureContainer(docker, "careeros-it-redis", RUN_ARGS))
                .doesNotThrowAnyException();

        assertThat(docker.calls).containsExactly(
                "exists careeros-it-redis", RUN_CALL, "start careeros-it-redis");
    }

    @Test
    void a_container_that_cannot_be_created_or_started_reports_the_create_failure() {
        FakeDocker docker = new FakeDocker(false);
        docker.runFailure = "create failed";
        docker.startFailure = "start failed";

        assertThatThrownBy(() -> ItInfrastructure.ensureContainer(docker, "careeros-it-redis", RUN_ARGS))
                .isInstanceOf(IllegalStateException.class)
                .hasMessage("create failed")
                .satisfies(t -> {
                    assertThat(t.getSuppressed()).hasSize(1);
                    assertThat(t.getSuppressed()[0]).hasMessage("start failed");
                });
    }

    private static final class FakeDocker implements ItInfrastructure.DockerCli {

        final List<String> calls = new ArrayList<>();
        private final boolean exists;
        String runFailure;
        String startFailure;

        FakeDocker(boolean exists) {
            this.exists = exists;
        }

        @Override
        public boolean exists(String container) {
            calls.add("exists " + container);
            return exists;
        }

        @Override
        public void run(int timeoutSeconds, String... args) {
            String call = String.join(" ", args);
            calls.add(call);
            if (call.startsWith("run") && runFailure != null) {
                throw new IllegalStateException(runFailure);
            }
            if (call.startsWith("start") && startFailure != null) {
                throw new IllegalStateException(startFailure);
            }
        }
    }
}
