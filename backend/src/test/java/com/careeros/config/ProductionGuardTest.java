package com.careeros.config;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.NestedExceptionUtils;
import org.springframework.stereotype.Component;

class ProductionGuardTest {

    private static final String PUBLISHED_JWT = "dev-only-secret-please-change-me-0123456789abcdef0123456789abcdef";
    private static final String PUBLISHED_MAIL = "dev-only-mail-link-secret-please-change-me-0123456789abcdef";
    private static final String PUBLISHED_MFA = "dev-only-mfa-secret-please-change-me-0123456789abcdef";
    private static final String PUBLISHED_INTERNAL = "shared-secret-between-backend-and-ai-service";
    private static final String PUBLISHED_DB = "dev_pg_pass_9f3k";
    private static final String PUBLISHED_MINIO_USER = "careeros-minio-admin";
    private static final String PUBLISHED_MINIO_SECRET = "careeros_minio_dev_password";

    private static final String REAL_JWT = "f3c1a9e2b7d44058a6c9e1d2b3f4a5c6d7e8f901a2b3c4d5e6f708192a3b4c5d";
    private static final String REAL_MAIL = "b4e2c9d7a1f3e5c8b6d2a4f7e9c1b3d508a6c4e2f1d7b9a3c5e8f2d4b6a9c1e7";
    private static final String REAL_MFA = "mfa-2e7c4a9f1b6d8e3a0c5f7b9d2e4a6c8f1a3e5b7d";
    private static final String REAL_INTERNAL = "internal-7c1e9a3f5b8d2c6e4a0f9b7d5c3e1a8f";
    private static final String REAL_DB = "pg-4b8e1c7a9d2f6e0b3a5c8d1e4f7a0b2c";
    private static final String REAL_MINIO_USER = "careeros-ops-7c1e";
    private static final String REAL_MINIO_SECRET = "minio-9a3f5b8d2c6e4a0f9b7d5c3e1a8f";
    private static final String REAL_WEB = "https://career.example.org";
    private static final String REAL_CORS = "https://career.example.org,https://www.career.example.org";
    private static final String REAL_SMTP = "smtp";

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withUserConfiguration(BoundProperties.class)
            .withBean(ProductionGuard.class);

    @Test
    void aDevBootKeepsThePublishedDefaults() {
        Map<String, String> published = credentials(PUBLISHED_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL,
                "change-me", "change-me", "change-me");
        assertThat(ProductionGuard.offenders("dev", "console", published)).isEmpty();
        assertThat(ProductionGuard.offenders("test", "console", published)).isEmpty();
        assertThat(ProductionGuard.offenders(null, "console", published)).isEmpty();
        assertThat(ProductionGuard.offenders("dev", "console", published, "http://localhost:3000")).isEmpty();
    }

    @Test
    void aProdBootNamesEveryCredentialStillOnAPublishedValue() {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(PUBLISHED_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL, REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);
    }

    @Test
    void aLoneOverrideStillLeavesTheOthersNamed() {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, PUBLISHED_MAIL, PUBLISHED_INTERNAL, REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .containsExactly(ProductionGuard.MAIL_LINK_SECRET, ProductionGuard.INTERNAL_TOKEN);
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, PUBLISHED_INTERNAL, REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .containsExactly(ProductionGuard.INTERNAL_TOKEN);
    }

    @Test
    void theExamplesChangeMePlaceholdersAndEmptyValuesAreRefusedToo() {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials("CHANGE_ME_64_PLUS_RANDOM_CHARS", "CHANGE_ME_MAIL_LINK_SECRET",
                        "CHANGE_ME_STRONG_INTERNAL_TOKEN", "CHANGE_ME_STRONG_PASSWORD",
                        "CHANGE_ME_STRONG_MINIO_USER", "CHANGE_ME_STRONG_MINIO_PASSWORD")))
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN, ProductionGuard.POSTGRES_PASSWORD,
                        ProductionGuard.MINIO_ACCESS_KEY, ProductionGuard.MINIO_SECRET_KEY);
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(" ", "", null, " ", null, "")))
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN, ProductionGuard.POSTGRES_PASSWORD,
                        ProductionGuard.MINIO_ACCESS_KEY, ProductionGuard.MINIO_SECRET_KEY);
    }

    @Test
    void aProdBootWithRealSecretsHasNoOffenders() {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .isEmpty();
    }

    @Test
    void theProdSwitchIgnoresCaseAndSurroundingSpace() {
        assertThat(ProductionGuard.offenders(" PROD ", REAL_SMTP,
                credentials(PUBLISHED_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .containsExactly(ProductionGuard.JWT_SECRET);
    }

    @Test
    void theConsoleTransportCannotOpenAProdBoot() {
        Map<String, String> real = credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER,
                REAL_MINIO_SECRET);
        assertThat(ProductionGuard.offenders("prod", "console", real))
                .containsExactly(ProductionGuard.EMAIL_PROVIDER);
        assertThat(ProductionGuard.offenders("prod", " CONSOLE ", real))
                .containsExactly(ProductionGuard.EMAIL_PROVIDER);
        assertThat(ProductionGuard.offenders("prod", " ", real))
                .containsExactly(ProductionGuard.EMAIL_PROVIDER);
        assertThat(ProductionGuard.offenders("prod", null, real))
                .containsExactly(ProductionGuard.EMAIL_PROVIDER);
    }

    @Test
    void aDevBootOnTheConsoleTransportIsUntouched() {
        assertThat(ProductionGuard.offenders("dev", "console",
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .isEmpty();
    }

    @Test
    void theDatabaseAndObjectStoreDefaultsArePublished() {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, PUBLISHED_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .as("application.yml's database default")
                .containsExactly(ProductionGuard.POSTGRES_PASSWORD);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, PUBLISHED_MINIO_USER,
                        PUBLISHED_MINIO_SECRET)))
                .as("application.yml's object-store defaults")
                .containsExactly(ProductionGuard.MINIO_SECRET_KEY);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, "change-me", REAL_MINIO_SECRET)))
                .as("a dev example's placeholder access key")
                .containsExactly(ProductionGuard.MINIO_ACCESS_KEY);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, PUBLISHED_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .as("a published user name over a real secret is not a credential leak")
                .isEmpty();
    }

    @Test
    void thePublishedLiteralsAgreeWithTheShippedFiles() throws IOException {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(ymlDefault("JWT_SECRET"), ymlDefault("APP_MAIL_LINK_SECRET"),
                        ymlDefault("INTERNAL_API_TOKEN"), REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .as("application.yml's own defaults")
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);

        Path devExample = Path.of("..", ".env.example");
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(envValue(devExample, "JWT_SECRET"), envValue(devExample, "APP_MAIL_LINK_SECRET"),
                        envValue(devExample, "INTERNAL_API_TOKEN"), REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .as("a dev example copied into prod")
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);

        Path prodExample = Path.of("..", ".env.prod.example");
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(envValue(prodExample, "JWT_SECRET"), envValue(prodExample, "APP_MAIL_LINK_SECRET"),
                        envValue(prodExample, "INTERNAL_API_TOKEN"), REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .as("a prod example booted before its CHANGE_ME values were filled in")
                .containsExactly(ProductionGuard.JWT_SECRET, ProductionGuard.MAIL_LINK_SECRET,
                        ProductionGuard.INTERNAL_TOKEN);
    }

    @Test
    void theShippedMailDefaultsAgreeWithTheGuardToo() throws IOException {
        assertThat(ProductionGuard.offenders("prod", ymlDefault("APP_EMAIL_PROVIDER"),
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .as("application.yml's own mail default")
                .containsExactly(ProductionGuard.EMAIL_PROVIDER);

        assertThat(ProductionGuard.offenders("prod",
                envValue(Path.of("..", ".env.example"), "APP_EMAIL_PROVIDER"),
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .as("a dev example copied into prod")
                .containsExactly(ProductionGuard.EMAIL_PROVIDER);

        assertThat(ProductionGuard.offenders("prod",
                envValue(Path.of("..", ".env.prod.example"), "APP_EMAIL_PROVIDER"),
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .as(".env.prod.example's transport")
                .isEmpty();
    }

    @Test
    void theShippedMfaSeedKeyAgreesWithTheGuardToo() throws IOException {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, PUBLISHED_MFA, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .as("the literal this repository publishes")
                .containsExactly(ProductionGuard.MFA_SECRET);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, ymlDefault("APP_MFA_SECRET"), REAL_INTERNAL, REAL_DB,
                        REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .as("application.yml's own default")
                .containsExactly(ProductionGuard.MFA_SECRET);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, envValue(Path.of("..", ".env.example"), "APP_MFA_SECRET"),
                        REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .as("a dev example copied into prod")
                .containsExactly(ProductionGuard.MFA_SECRET);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL,
                        envValue(Path.of("..", ".env.prod.example"), "APP_MFA_SECRET"),
                        REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET)))
                .as("a prod example booted before its CHANGE_ME value was filled in")
                .containsExactly(ProductionGuard.MFA_SECRET);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, " ", REAL_INTERNAL, REAL_DB, REAL_MINIO_USER,
                        REAL_MINIO_SECRET)))
                .as("an empty seed key")
                .containsExactly(ProductionGuard.MFA_SECRET);
    }

    @Test
    void theShippedDatabaseAndStoreSecretsAgreeWithTheGuardToo() throws IOException {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, ymlDefault("POSTGRES_PASSWORD"),
                        ymlDefault("MINIO_ACCESS_KEY"), ymlDefault("MINIO_SECRET_KEY"))))
                .as("application.yml's own defaults")
                .containsExactly(ProductionGuard.POSTGRES_PASSWORD, ProductionGuard.MINIO_SECRET_KEY);

        Path devExample = Path.of("..", ".env.example");
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, envValue(devExample, "POSTGRES_PASSWORD"),
                        envValue(devExample, "MINIO_ACCESS_KEY"), envValue(devExample, "MINIO_SECRET_KEY"))))
                .as("a dev example copied into prod")
                .containsExactly(ProductionGuard.POSTGRES_PASSWORD, ProductionGuard.MINIO_ACCESS_KEY,
                        ProductionGuard.MINIO_SECRET_KEY);

        Path prodExample = Path.of("..", ".env.prod.example");
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, envValue(prodExample, "POSTGRES_PASSWORD"),
                        envValue(prodExample, "MINIO_ROOT_USER"), envValue(prodExample, "MINIO_ROOT_PASSWORD"))))
                .as("a prod example booted before its CHANGE_ME values were filled in")
                .containsExactly(ProductionGuard.POSTGRES_PASSWORD, ProductionGuard.MINIO_SECRET_KEY);
    }

    @Test
    void aProdBootOnALoopbackLinkBaseIsRefused() {
        for (String loopback : List.of("http://localhost:3000", "http://localhost:8080",
                "http://127.0.0.1:3000", "http://127.9.9.9", "http://[::1]:3000", "http://0.0.0.0:3000",
                "https://app.localhost")) {
            assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                    withBaseUrl(realSettings(), loopback)))
                    .as("a link base at %s", loopback)
                    .containsExactly(ProductionGuard.WEB_BASE_URL);
        }
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP, withBaseUrl(realSettings(), REAL_WEB)))
                .as("the public origin the deployment actually owns")
                .isEmpty();
    }

    @Test
    void aLinkBaseThatIsNotAnHttpUrlIsRefused() {
        for (String broken : List.of("", "   ", "career.example.org", "ftp://career.example.org",
                "not a url", "http://")) {
            assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                    withBaseUrl(realSettings(), broken)))
                    .as("a link base spelled %s", broken)
                    .containsExactly(ProductionGuard.WEB_BASE_URL);
        }
    }

    @Test
    void theExamplesOwnDomainIsRefusedWithAnySpelling() {
        for (String placeholder : List.of("https://your-domain.com", "https://your-domain.com/",
                "http://your-domain.com", "https://www.your-domain.com")) {
            assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                    withBaseUrl(realSettings(), placeholder)))
                    .as("the example domain spelled %s", placeholder)
                    .containsExactly(ProductionGuard.WEB_BASE_URL);
        }
    }

    @Test
    void theShippedLinkBaseAgreesWithTheGuardToo() throws IOException {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), ymlDefault("APP_WEB_BASE_URL"))))
                .as("application.yml's own default")
                .containsExactly(ProductionGuard.WEB_BASE_URL);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), envValue(Path.of("..", ".env.example"), "APP_WEB_BASE_URL"))))
                .as("a dev example copied into prod")
                .containsExactly(ProductionGuard.WEB_BASE_URL);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(),
                        envValue(Path.of("..", ".env.prod.example"), "APP_WEB_BASE_URL"))))
                .as("a prod example booted before its your-domain.com value was replaced")
                .containsExactly(ProductionGuard.WEB_BASE_URL);
    }

    @Test
    void theDevCorsListCannotOpenAProdBoot() {
        for (String refused : List.of("http://localhost:3000", "http://localhost:8080",
                "https://your-domain.com", "https://www.your-domain.com", "", "   ",
                "CHANGE_ME_ORIGIN", "career.example.org", "ftp://career.example.org", "not a url",
                "https://career.example.org/", "https://career.example.org/app",
                "https://career.example.org?x=1", REAL_CORS + ",http://127.0.0.1:3000")) {
            assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                    withBaseUrl(realSettings(), REAL_WEB), refused))
                    .as("a CORS list spelled %s", refused)
                    .containsExactly(ProductionGuard.CORS_ORIGINS);
        }
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), REAL_WEB), REAL_CORS))
                .as("the shell's own origin plus a second public spelling")
                .isEmpty();
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), REAL_WEB), "https://CAREER.EXAMPLE.ORG"))
                .as("host case is not part of an origin")
                .isEmpty();
    }

    @Test
    void aCorsListThatDoesNotAdmitTheShellIsRefused() {
        for (String elsewhere : List.of("https://www.career.example.org", "https://career.example.org:8443",
                "http://career.example.org")) {
            assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                    withBaseUrl(realSettings(), REAL_WEB), elsewhere))
                    .as("a public origin that is not the shell's: %s", elsewhere)
                    .containsExactly(ProductionGuard.CORS_ORIGINS);
        }
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), REAL_WEB), "http://localhost:3000"))
                .as("the dev default while the base is real")
                .containsExactly(ProductionGuard.CORS_ORIGINS);
    }

    @Test
    void theShippedCorsListsAgreeWithTheGuardToo() throws IOException {
        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), REAL_WEB), ymlDefault("APP_CORS_ORIGINS")))
                .as("application.yml's own default")
                .containsExactly(ProductionGuard.CORS_ORIGINS);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), REAL_WEB),
                envValue(Path.of("..", ".env.example"), "APP_CORS_ORIGINS")))
                .as("a dev example copied into prod")
                .containsExactly(ProductionGuard.CORS_ORIGINS);

        assertThat(ProductionGuard.offenders("prod", REAL_SMTP,
                withBaseUrl(realSettings(), REAL_WEB),
                envValue(Path.of("..", ".env.prod.example"), "APP_CORS_ORIGINS")))
                .as("a prod example booted before its your-domain.com origins were replaced")
                .containsExactly(ProductionGuard.CORS_ORIGINS);
    }

    @Test
    void aProdContextRefusesToRefreshAndNamesEveryOffender() {
        runner.withPropertyValues("app.deployment.env=prod", "app.jwt.secret=" + PUBLISHED_JWT,
                        "app.mail.link-secret=" + PUBLISHED_MAIL, "app.internal.token=" + PUBLISHED_INTERNAL)
                .run(context -> {
                    assertThat(context).hasFailed();
                    assertThat(NestedExceptionUtils.getMostSpecificCause(context.getStartupFailure()).getMessage())
                            .contains("APP_ENV=prod but JWT_SECRET, APP_MAIL_LINK_SECRET, APP_MFA_SECRET, "
                                    + "INTERNAL_API_TOKEN, "
                                    + "POSTGRES_PASSWORD, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, APP_WEB_BASE_URL, "
                                    + "APP_CORS_ORIGINS, APP_EMAIL_PROVIDER cannot open")
                            .contains("docs/DEPLOYMENT.md");
                });
    }

    @Test
    void aProdContextOnTheConsoleTransportIsRefusedEvenWithRealSecrets() {
        runner.withPropertyValues(prodProperties("console")).run(context -> {
            assertThat(context).hasFailed();
            assertThat(NestedExceptionUtils.getMostSpecificCause(context.getStartupFailure()).getMessage())
                    .contains("APP_ENV=prod but APP_EMAIL_PROVIDER cannot open")
                    .doesNotContain("JWT_SECRET");
        });
    }

    @Test
    void aProdContextOnALoopbackLinkBaseIsRefusedEvenWithRealSecrets() {
        runner.withPropertyValues("app.deployment.env=prod", "app.jwt.secret=" + REAL_JWT,
                        "app.mail.link-secret=" + REAL_MAIL, "app.security.mfa-secret=" + REAL_MFA,
                        "app.internal.token=" + REAL_INTERNAL,
                        "spring.datasource.password=" + REAL_DB,
                        "app.storage.access-key=" + REAL_MINIO_USER,
                        "app.storage.secret-key=" + REAL_MINIO_SECRET,
                        "app.email.provider=" + REAL_SMTP,
                        "app.web.base-url=http://localhost:3000",
                        "app.cors.allowed-origins=" + REAL_CORS)
                .run(context -> {
                    assertThat(context).hasFailed();
                    assertThat(NestedExceptionUtils.getMostSpecificCause(context.getStartupFailure()).getMessage())
                            .contains("APP_ENV=prod but APP_WEB_BASE_URL cannot open")
                            .doesNotContain("JWT_SECRET");
                });
    }

    @Test
    void aProdContextOnTheDevCorsListIsRefusedEvenWithRealSecrets() {
        runner.withPropertyValues(prodProperties(REAL_SMTP))
                .withPropertyValues("app.cors.allowed-origins=http://localhost:3000")
                .run(context -> {
                    assertThat(context).hasFailed();
                    assertThat(NestedExceptionUtils.getMostSpecificCause(context.getStartupFailure()).getMessage())
                            .contains("APP_ENV=prod but APP_CORS_ORIGINS cannot open")
                            .doesNotContain("JWT_SECRET");
                });
    }

    @Test
    void aProdContextStartsOnceEveryCredentialIsReal() {
        runner.withPropertyValues(prodProperties(REAL_SMTP)).run(context -> {
            assertThat(context).hasNotFailed();
            assertThat(context).hasSingleBean(ProductionGuard.class);
        });
    }

    @Test
    void aProdBootCannotSilenceTheStoreCheckByDisablingStorage() {
        runner.withPropertyValues("app.deployment.env=prod", "app.jwt.secret=" + REAL_JWT,
                        "app.mail.link-secret=" + REAL_MAIL, "app.security.mfa-secret=" + REAL_MFA,
                        "app.internal.token=" + REAL_INTERNAL,
                        "spring.datasource.password=" + REAL_DB, "app.email.provider=" + REAL_SMTP,
                        "app.web.base-url=" + REAL_WEB, "app.cors.allowed-origins=" + REAL_CORS,
                        "app.storage.enabled=false")
                .run(context -> {
                    assertThat(context).hasFailed();
                    assertThat(NestedExceptionUtils.getMostSpecificCause(context.getStartupFailure()).getMessage())
                            .as("the switch is the bean condition's; four services still need a StorageService")
                            .contains("APP_ENV=prod but MINIO_ACCESS_KEY, MINIO_SECRET_KEY cannot open")
                            .doesNotContain("JWT_SECRET");
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

    private static String[] prodProperties(String provider) {
        return new String[] {
            "app.deployment.env=prod",
            "app.jwt.secret=" + REAL_JWT,
            "app.mail.link-secret=" + REAL_MAIL,
            "app.security.mfa-secret=" + REAL_MFA,
            "app.internal.token=" + REAL_INTERNAL,
            "spring.datasource.password=" + REAL_DB,
            "app.storage.access-key=" + REAL_MINIO_USER,
            "app.storage.secret-key=" + REAL_MINIO_SECRET,
            "app.email.provider=" + provider,
            "app.web.base-url=" + REAL_WEB,
            "app.cors.allowed-origins=" + REAL_CORS,
        };
    }

    private static Map<String, String> realSettings() {
        return credentials(REAL_JWT, REAL_MAIL, REAL_INTERNAL, REAL_DB, REAL_MINIO_USER, REAL_MINIO_SECRET);
    }

    private static Map<String, String> withBaseUrl(Map<String, String> values, String baseUrl) {
        values.put(ProductionGuard.WEB_BASE_URL, baseUrl);
        return values;
    }

    private static Map<String, String> credentials(String jwt, String mailLink, String internal,
            String database, String minioAccess, String minioSecret) {
        return credentials(jwt, mailLink, REAL_MFA, internal, database, minioAccess, minioSecret);
    }

    private static Map<String, String> credentials(String jwt, String mailLink, String mfa, String internal,
            String database, String minioAccess, String minioSecret) {
        Map<String, String> values = new LinkedHashMap<>();
        values.put(ProductionGuard.JWT_SECRET, jwt);
        values.put(ProductionGuard.MAIL_LINK_SECRET, mailLink);
        values.put(ProductionGuard.MFA_SECRET, mfa);
        values.put(ProductionGuard.INTERNAL_TOKEN, internal);
        values.put(ProductionGuard.POSTGRES_PASSWORD, database);
        values.put(ProductionGuard.MINIO_ACCESS_KEY, minioAccess);
        values.put(ProductionGuard.MINIO_SECRET_KEY, minioSecret);
        return values;
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
