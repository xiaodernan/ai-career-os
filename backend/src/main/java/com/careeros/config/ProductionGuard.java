package com.careeros.config;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Refuses to start a production deployment on a credential this repository publishes,
 * or on a mail transport that keeps every letter in the log.
 *
 * <p>{@code application.yml} interpolates each secret from an environment variable but
 * ships a working default, so a production boot that forgets one starts happily on a
 * value printed in this repository: access tokens anyone can sign, unsubscribe and
 * mail-settings links anyone can forge, an {@code /internal/*} surface anyone can
 * call, and the database and object store the account's data lives in. The object
 * store pair is asked for unconditionally: four services inject a
 * {@code StorageService}, so a prod boot with the store switched off has no bean
 * to inject and fails anyway — the switch is the bean condition's to read, and
 * turning it off cannot dodge this check. The mail
 * transport has the same shape: {@code APP_EMAIL_PROVIDER} defaults to {@code console},
 * which logs each letter instead of sending it, so a production boot that forgets the
 * knob answers "check your email" to a password reset whose link goes into a log file
 * nobody is reading. The ai-service answers the same question in
 * {@code app.ops.preflight}; the backend has no preflight step before the context
 * exists, so this bean is the preflight. It names every offender at once, so one
 * restart fixes all of them, and it does nothing outside prod: the example secrets and
 * the console transport are exactly what a dev checkout runs on.
 */
@Component
public class ProductionGuard {

    static final String JWT_SECRET = "JWT_SECRET";
    static final String MAIL_LINK_SECRET = "APP_MAIL_LINK_SECRET";
    static final String INTERNAL_TOKEN = "INTERNAL_API_TOKEN";
    static final String POSTGRES_PASSWORD = "POSTGRES_PASSWORD";
    static final String MINIO_ACCESS_KEY = "MINIO_ACCESS_KEY";
    static final String MINIO_SECRET_KEY = "MINIO_SECRET_KEY";
    static final String EMAIL_PROVIDER = "APP_EMAIL_PROVIDER";

    /** The transport that logs instead of sending; EmailConfig resolves it from this name. */
    private static final String CONSOLE_TRANSPORT = "console";

    /**
     * The literals the shipped files publish, so a copied example file is refused too.
     * `MINIO_ACCESS_KEY` carries only the examples' `change-me`: an access key is the
     * account's user name, not its secret, and the shipped `careeros-minio-admin` is
     * one a deployment may keep — the pair is refused on the secret.
     */
    private static final Map<String, Set<String>> PUBLISHED = Map.of(
            JWT_SECRET,
            Set.of("dev-only-secret-please-change-me-0123456789abcdef0123456789abcdef",
                    "generate-a-64+char-random-string"),
            MAIL_LINK_SECRET, Set.of("dev-only-mail-link-secret-please-change-me-0123456789abcdef"),
            INTERNAL_TOKEN, Set.of("shared-secret-between-backend-and-ai-service"),
            POSTGRES_PASSWORD, Set.of("dev_pg_pass_9f3k", "change-me"),
            MINIO_ACCESS_KEY, Set.of("change-me"),
            MINIO_SECRET_KEY, Set.of("careeros_minio_dev_password", "change-me"));

    private static final String EXAMPLE_PLACEHOLDER = "CHANGE_ME";

    public ProductionGuard(AppProperties props, @Value("${app.mail.link-secret}") String mailLinkSecret,
            @Value("${app.email.provider:console}") String emailProvider,
            @Value("${spring.datasource.password:}") String databasePassword) {
        Map<String, String> credentials = new LinkedHashMap<>();
        credentials.put(JWT_SECRET, props.getJwt().getSecret());
        credentials.put(MAIL_LINK_SECRET, mailLinkSecret);
        credentials.put(INTERNAL_TOKEN, props.getInternal().getToken());
        credentials.put(POSTGRES_PASSWORD, databasePassword);
        credentials.put(MINIO_ACCESS_KEY, props.getStorage().getAccessKey());
        credentials.put(MINIO_SECRET_KEY, props.getStorage().getSecretKey());
        List<String> offenders = offenders(props.getDeployment().getEnv(), emailProvider, credentials);
        if (!offenders.isEmpty()) {
            throw new IllegalStateException("APP_ENV=prod but " + String.join(", ", offenders)
                    + " cannot open a production deployment: the guard refuses a credential this repository "
                    + "publishes, the examples' CHANGE_ME placeholder, an empty value, and the console mail "
                    + "transport, which logs every reset link instead of mailing it. Set each credential to a "
                    + "random secret and APP_EMAIL_PROVIDER=smtp with a relay; docs/DEPLOYMENT.md lists the steps.");
        }
    }

    /**
     * The configuration that cannot open a prod boot, in the order the credentials are
     * named; empty means the boot may proceed. The caller hands in every credential the
     * boot presents, so reordering the map is reordering the operator's fix list.
     */
    static List<String> offenders(String env, String emailProvider, Map<String, String> credentials) {
        if (env == null || !"prod".equalsIgnoreCase(env.trim())) {
            return List.of();
        }
        List<String> found = new ArrayList<>();
        credentials.forEach((envVar, value) -> {
            if (isPublished(envVar, value)) {
                found.add(envVar);
            }
        });
        if (isConsoleTransport(emailProvider)) {
            found.add(EMAIL_PROVIDER);
        }
        return List.copyOf(found);
    }

    /** An empty value is refused too: the interpolation's own default is the console transport. */
    private static boolean isConsoleTransport(String provider) {
        return provider == null || provider.isBlank()
                || CONSOLE_TRANSPORT.equals(provider.trim().toLowerCase(Locale.ROOT));
    }

    private static boolean isPublished(String envVar, String value) {
        return value == null || value.isBlank() || value.startsWith(EXAMPLE_PLACEHOLDER)
                || PUBLISHED.get(envVar).contains(value);
    }
}
