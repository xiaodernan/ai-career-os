package com.careeros;

/**
 * The docker-CLI half of the IT bootstrap, split out of {@link AbstractIntegrationTest} so it
 * can be exercised without a Spring context and without that class's static initializer,
 * which talks to real docker and postgres.
 */
final class ItInfrastructure {

    interface DockerCli {
        boolean exists(String container) throws Exception;

        /** Runs one docker command; a non-zero exit or a timeout is an IllegalStateException. */
        void run(int timeoutSeconds, String... args) throws Exception;
    }

    private ItInfrastructure() {
    }

    /**
     * Brings a container up idempotently. {@code exists} is only a hint: a transient CLI failure
     * reads as "missing", and the following {@code run} then dies with "the container name is
     * already in use". In that case the container is evidently there, so start it instead of
     * failing every IT class through the bootstrap's static initializer.
     */
    static void ensureContainer(DockerCli docker, String name, String... runArgs) throws Exception {
        if (docker.exists(name)) {
            docker.run(15, "start", name);
            return;
        }
        try {
            docker.run(60, runArgs);
        } catch (IllegalStateException runFailure) {
            try {
                docker.run(15, "start", name);
            } catch (IllegalStateException startFailure) {
                runFailure.addSuppressed(startFailure);
                throw runFailure;
            }
        }
    }
}
