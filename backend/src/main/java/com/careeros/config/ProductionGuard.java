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
 * mail-settings links anyone can forge, and an {@code /internal/*} surface anyone can
 * call. The mail transport has the same shape: {@code APP_EMAIL_PROVIDER} defaults to
 * {@code console}, which logs each letter instead of sending it, so a production boot
 * that forgets the knob answers "check your email" to a password reset whose link goes
 * into a log file nobody is reading. The ai-service answers the same question in
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
    static final String EMAIL_PROVIDER = "APP_EMAIL_PROVIDER";

    /** The transport that logs instead of sending; EmailConfig resolves it from this name. */
    private static final String CONSOLE_TRANSPORT = "console";

    /** The literals the shipped files publish, so a copied example file is refused too. */
    private static final Map<String, Set<String>> PUBLISHED = Map.of(
            JWT_SECRET,
            Set.of("dev-only-secret-please-change-me-0123456789abcdef0123456789abcdef",
                    "generate-a-64+char-random-string"),
            MAIL_LINK_SECRET, Set.of("dev-only-mail-link-secret-please-change-me-0123456789abcdef"),
            INTERNAL_TOKEN, Set.of("shared-secret-between-backend-and-ai-service"));

    private static final String EXAMPLE_PLACEHOLDER = "CHANGE_ME";

    public ProductionGuard(AppProperties props, @Value("${app.mail.link-secret}") String mailLinkSecret,
            @Value("${app.email.provider:console}") String emailProvider) {
        List<String> offenders = offenders(props.getDeployment().getEnv(), props.getJwt().getSecret(),
                mailLinkSecret, props.getInternal().getToken(), emailProvider);
        if (!offenders.isEmpty()) {
            throw new IllegalStateException("APP_ENV=prod but " + String.join(", ", offenders)
                    + " cannot open a production deployment: the guard refuses a credential this repository "
                    + "publishes, the examples' CHANGE_ME placeholder, an empty value, and the console mail "
                    + "transport, which logs every reset link instead of mailing it. Set each credential to a "
                    + "random secret and APP_EMAIL_PROVIDER=smtp with a relay; docs/DEPLOYMENT.md lists the steps.");
        }
    }

    /** The configuration that cannot open a prod boot, in a fixed order; empty means the boot may proceed. */
    static List<String> offenders(String env, String jwtSecret, String mailLinkSecret, String internalToken,
            String emailProvider) {
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
