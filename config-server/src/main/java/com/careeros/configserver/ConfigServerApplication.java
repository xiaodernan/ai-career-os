package com.careeros.configserver;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.config.server.EnableConfigServer;

/**
 * Opt-in Spring Cloud Config Server (Epic 103).
 *
 * <p>Serves externalized configuration from a native/file backend so deployments can
 * centralize service configuration without introducing a git dependency. Disabled in the
 * default stack; services opt in via {@code SPRING_CLOUD_CONFIG_ENABLED=true} and a
 * {@code spring.config.import=configserver:...} URI.
 */
@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}
