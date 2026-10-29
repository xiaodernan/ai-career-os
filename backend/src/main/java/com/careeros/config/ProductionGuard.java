package com.careeros.config;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Refuses to start a production deployment on a credential this repository publishes.
 *
 * <p>{@code application.yml} interpolates each secret from an environment variable but
 * ships a working default, so a production boot that forgets one starts happily on a
 * value printed in this repository: access tokens anyone can sign, unsubscribe and
 * mail-settings links anyone can forge, and an {@code /internal/*} surface anyone can
 * call. The ai-service answers the same question in {@code app.ops.preflight}; the
 * backend has no preflight step before the context exists, so this bean is the
 * preflight. It names every offender at once, so one restart fixes all of them, and it
 * does nothing outside prod: the example secrets are exactly what a dev checkout runs on.
 */
@Component
public class ProductionGuard {

    static final String JWT_SECRET = "JWT_SECRET";
    static final String MAIL_LINK_SECRET = "APP_MAIL_LINK_SECRET";
    static final String INTERNAL_TOKEN = "INTERNAL_API_TOKEN";

    /** The literals the shipped files publish, so a copied example file is refused too. */
    private static final Map<String, Set<String>> PUBLISHED = Map.of(
            JWT_SECRET,
            Set.of("dev-only-secret-please-change-me-0123456789abcdef0123456789abcdef",
                    "generate-a-64+char-random-string"),
            MAIL_LINK_SECRET, Set.of("dev-only-mail-link-secret-please-change-me-0123456789abcdef"),
            INTERNAL_TOKEN, Set.of("shared-secret-between-backend-and-ai-service"));

    private static final String EXAMPLE_PLACEHOLDER = "CHANGE_ME";

    public ProductionGuard(AppProperties props, @Value("${app.mail.link-secret}") String mailLinkSecret) {
        List<String> offenders = offenders(props.getDeployment().getEnv(), props.getJwt().getSecret(),
                mailLinkSecret, props.getInternal().getToken());
        if (!offenders.isEmpty()) {
            throw new IllegalStateException("APP_ENV=prod but " + String.join(", ", offenders)
                    + " still hold a value this repository publishes, the examples' CHANGE_ME placeholder, "
                    + "or nothing at all. Set each to a random secret; docs/DEPLOYMENT.md lists the steps.");
        }
    }

    /** The credentials that cannot open a prod boot, in a fixed order; empty means the boot may proceed. */
    static List<String> offenders(String env, String jwtSecret, String mailLinkSecret, String internalToken) {
        if (env == null || !"prod".equalsIgnoreCase(env.trim())) {
            return List.of();
        }
        Map<String, String> values = new LinkedHashMap<>();
        values.put(JWT_SECRET, jwtSecret);
        values.put(MAIL_LINK_SECRET, mailLinkSecret);
        values.put(INTERNAL_TOKEN, internalToken);
        List<String> found = new ArrayList<>();
        values.forEach((envVar, value) -> {
            if (isPublished(envVar, value)) {
                found.add(envVar);
            }
        });
        return List.copyOf(found);
    }

    private static boolean isPublished(String envVar, String value) {
        return value == null || value.isBlank() || value.startsWith(EXAMPLE_PLACEHOLDER)
                || PUBLISHED.get(envVar).contains(value);
    }
}
