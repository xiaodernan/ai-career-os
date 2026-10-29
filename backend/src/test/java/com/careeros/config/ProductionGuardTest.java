package com.careeros.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Component;

class ProductionGuardTest {

    private static final String PUBLISHED_JWT = "dev-only-secret-please-change-me-0123456789abcdef0123456789abcdef";
    private static final String PUBLISHED_MAIL = "dev-only-mail-link-secret-please-change-me-0123456789abcdef";
    private static final String PUBLISHED_INTERNAL = "shared-secret-between-backend-and-ai-service";

    private static final String REAL_JWT = "f3c1a9e2b7d44058a6c9e1d2b3f4a5c6d7e8f901a2b3c4d5e6f708192a3b4c5d";
    private static final String REAL_MAIL = "b4e2c9d7a1f3e5c8b6d2a4f7e9c1b3d508a6c4e2f1d7b9a3c5e8f2d4b6a9c1e7";
    private static final String REAL_INTERNAL = "internal-7c1e9a3f5b8d2c6e4a0f9b7d5c3e1a8f";

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withUserConfiguration(BoundProperties.class)
            .withBean(ProductionGuard.class);

    @Test
    void aDevBootKeepsThePublishedDefaults() {
        assertThat(ProductionGuard.offenders("dev", PUBLISHED_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL)).isEmpty();
        assertThat(ProductionGuard.offenders("test", PUBLISHED_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL)).isEmpty();
        assertThat(ProductionGuard.offenders(null, PUBLISHED_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL)).isEmpty();
    }

    @Test
    void aProdBootNamesEveryCredentialStillOnAPublishedValue() {
        assertThat(ProductionGuard.offenders("prod", PUBLISHED_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL))
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);
    }

    @Test
    void aLoneOverrideStillLeavesTheOthersNamed() {
        assertThat(ProductionGuard.offenders("prod", REAL_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL))
                .containsExactly(ProductionGuard.MAIL_LINK_SECRET, ProductionGuard.INTERNAL_TOKEN);
        assertThat(ProductionGuard.offenders("prod", REAL_JWT, REAL_MAIL, PUBLISHED_INTERNAL))
                .containsExactly(ProductionGuard.INTERNAL_TOKEN);
    }

    @Test
    void theExamplesChangeMePlaceholdersAndEmptyValuesAreRefusedToo() {
        assertThat(ProductionGuard.offenders("prod", "CHANGE_ME_64_PLUS_RANDOM_CHARS",
                "CHANGE_ME_MAIL_LINK_SECRET", "CHANGE_ME_STRONG_INTERNAL_TOKEN"))
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);
        assertThat(ProductionGuard.offenders("prod", " ", "", null))
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);
    }

    @Test
    void aProdBootWithRealSecretsHasNoOffenders() {
        assertThat(ProductionGuard.offenders("prod", REAL_JWT, REAL_MAIL, REAL_INTERNAL)).isEmpty();
    }

    @Test
    void theProdSwitchIgnoresCaseAndSurroundingSpace() {
        assertThat(ProductionGuard.offenders(" PROD ", PUBLISHED_JWT, REAL_MAIL, REAL_INTERNAL))
                .containsExactly(ProductionGuard.JWT_SECRET);
    }

    @Test
    void thePublishedLiteralsAgreeWithTheShippedFiles() throws IOException {
        assertThat(ProductionGuard.offenders("prod",
                ymlDefault("JWT_SECRET"), ymlDefault("APP_MAIL_LINK_SECRET"), ymlDefault("INTERNAL_API_TOKEN")))
                .as("application.yml's own defaults")
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);

        Path devExample = Path.of("..", ".env.example");
        assertThat(ProductionGuard.offenders("prod",
                envValue(devExample, "JWT_SECRET"), envValue(devExample, "APP_MAIL_LINK_SECRET"),
                envValue(devExample, "INTERNAL_API_TOKEN")))
                .as("a dev example copied into prod")
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);

        Path prodExample = Path.of("..", ".env.prod.example");
        assertThat(ProductionGuard.offenders("prod",
                envValue(prodExample, "JWT_SECRET"), envValue(prodExample, "APP_MAIL_LINK_SECRET"),
                envValue(prodExample, "INTERNAL_API_TOKEN")))
                .as("a prod example booted before its CHANGE_ME values were filled in")
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);
    }

    @Test
    void aProdContextRefusesToRefreshAndNamesEveryOffender() {
        runner.withPropertyValues("app.deployment.env=prod", "app.jwt.secret=" + PUBLISHED_JWT,
                        "app.mail.link-secret=" + PUBLISHED_MAIL, "app.internal.token=" + PUBLISHED_INTERNAL)
                .run(context -> {
                    assertThat(context).hasFailed();
                    assertThat(context.getStartupFailure())
                            .hasStackTraceContaining(ProductionGuard.JWT_SECRET)
                            .hasStackTraceContaining(ProductionGuard.MAIL_LINK_SECRET)
                            .hasStackTraceContaining(ProductionGuard.INTERNAL_TOKEN)
                            .hasStackTraceContaining("docs/DEPLOYMENT.md");
                });
    }

    @Test
    void aProdContextStartsOnceEveryCredentialIsReal() {
        runner.withPropertyValues("app.deployment.env=prod", "app.jwt.secret=" + REAL_JWT,
                        "app.mail.link-secret=" + REAL_MAIL, "app.internal.token=" + REAL_INTERNAL)
                .run(context -> {
                    assertThat(context).hasNotFailed();
                    assertThat(context).hasSingleBean(ProductionGuard.class);
                });
    }

    @Test
    void theDevContextStartsOnThePublishedDefaults() {
        runner.withPropertyValues("app.mail.link-secret=" + PUBLISHED_MAIL)
                .run(context -> assertThat(context).hasNotFailed());
    }

    @Test
    void theGuardIsOnTheShippedComponentScan() {
        assertThat(ProductionGuard.class).hasAnnotation(Component.class);
    }

    private static String ymlDefault(String envVar) throws IOException {
        String yml = Files.readString(Path.of("src", "main", "resources", "application.yml"));
        Matcher match = Pattern.compile("\\$\\{" + envVar + ":([^}]*)}").matcher(yml);
        assertThat(match.find()).as("%s's interpolated default in application.yml", envVar).isTrue();
        return match.group(1).trim();
    }

    private static String envValue(Path file, String envVar) throws IOException {
        Matcher match = Pattern.compile("(?m)^" + envVar + "=(.*)$").matcher(Files.readString(file));
        assertThat(match.find()).as("%s in %s", envVar, file).isTrue();
        return match.group(1).trim();
    }

    @Configuration(proxyBeanMethods = false)
    @EnableConfigurationProperties(AppProperties.class)
    static class BoundProperties {
    }
}
