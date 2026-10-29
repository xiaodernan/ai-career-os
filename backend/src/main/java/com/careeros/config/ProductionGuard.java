package com.careeros.config;

import java.net.URI;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Refuses to start a production deployment on a credential this repository publishes,
 * on a link base the reader cannot open, on a cross-origin list the deployed shell is
 * not in, or on a mail transport that keeps every letter in the log.
 *
 * <p>The key that seals every enrolled authenticator seed ({@code app.security.mfa-secret},
 * roadmap 36.1) is on the same list: under the value this repository publishes, a database
 * dump is not a list of hashes but every account's second factor in clear.
 *
 * <p>{@code application.yml} interpolates each secret from an environment variable but
 * ships a working default, so a production boot that forgets one starts happily on a
 * value printed in this repository: access tokens anyone can sign, unsubscribe and
 * mail-settings links anyone can forge, an {@code /internal/*} surface anyone can
 * call, and the database and object store the account's data lives in. The object
 * store pair is asked for unconditionally: four services inject a
 * {@code StorageService}, so a prod boot with the store switched off has no bean
 * to inject and fails anyway — the switch is the bean condition's to read, and
 * turning it off cannot dodge this check. The base of every mailed link
 * ({@code app.web.base-url}) has its own two ways to be wrong: the shipped default
 * is loopback, so a forgotten knob mails password-reset, email-change and
 * unsubscribe links to a machine the reader does not have, and the production
 * example's {@code your-domain.com} is a domain the operator does not own, so a
 * boot that keeps it hands every token to whoever does. The cross-origin list has
 * the third way: it defaults to the dev shell, and entries are matched against the
 * browser's {@code Origin} header exactly, so a list that names loopback, the
 * example's domain, a bare host or any spelling with a path admits no deployed
 * shell — every API call from the real page fails CORS while the boot looks
 * healthy. The mail
 * transport has the same shape: {@code APP_EMAIL_PROVIDER} defaults to {@code console},
 * which logs each letter instead of sending it, so a production boot that forgets the
 * knob answers "check your email" to a password reset whose link goes into a log file
 * nobody is reading. The ai-service answers the same question in
 * {@code app.ops.preflight}; the backend has no preflight step before the context
 * exists, so this bean is the preflight. It names every offender at once, so one
 * restart fixes all of them, and it does nothing outside prod: the example secrets,
 * the loopback origins and the console transport are exactly what a dev checkout
 * runs on.
 */
@Component
public class ProductionGuard {

    static final String JWT_SECRET = "JWT_SECRET";
    static final String MAIL_LINK_SECRET = "APP_MAIL_LINK_SECRET";
    static final String MFA_SECRET = "APP_MFA_SECRET";
    static final String INTERNAL_TOKEN = "INTERNAL_API_TOKEN";
    static final String POSTGRES_PASSWORD = "POSTGRES_PASSWORD";
    static final String MINIO_ACCESS_KEY = "MINIO_ACCESS_KEY";
    static final String MINIO_SECRET_KEY = "MINIO_SECRET_KEY";
    static final String WEB_BASE_URL = "APP_WEB_BASE_URL";
    static final String CORS_ORIGINS = "APP_CORS_ORIGINS";
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
            MFA_SECRET, Set.of("dev-only-mfa-secret-please-change-me-0123456789abcdef"),
            INTERNAL_TOKEN, Set.of("shared-secret-between-backend-and-ai-service"),
            POSTGRES_PASSWORD, Set.of("dev_pg_pass_9f3k", "change-me"),
            MINIO_ACCESS_KEY, Set.of("change-me"),
            MINIO_SECRET_KEY, Set.of("careeros_minio_dev_password", "change-me"),
            WEB_BASE_URL, Set.of("http://localhost:3000", "https://your-domain.com"));

    /** The example domain; refused by host too, so a trailing slash or scheme change cannot smuggle it in. */
    private static final String EXAMPLE_HOST = "your-domain.com";

    private static final String EXAMPLE_PLACEHOLDER = "CHANGE_ME";

    public ProductionGuard(AppProperties props, @Value("${app.mail.link-secret}") String mailLinkSecret,
            @Value("${app.security.mfa-secret:}") String mfaSecret,
            @Value("${app.email.provider:console}") String emailProvider,
            @Value("${spring.datasource.password:}") String databasePassword,
            @Value("${app.web.base-url:http://localhost:3000}") String webBaseUrl) {
        Map<String, String> values = new LinkedHashMap<>();
        values.put(JWT_SECRET, props.getJwt().getSecret());
        values.put(MAIL_LINK_SECRET, mailLinkSecret);
        values.put(MFA_SECRET, mfaSecret);
        values.put(INTERNAL_TOKEN, props.getInternal().getToken());
        values.put(POSTGRES_PASSWORD, databasePassword);
        values.put(MINIO_ACCESS_KEY, props.getStorage().getAccessKey());
        values.put(MINIO_SECRET_KEY, props.getStorage().getSecretKey());
        values.put(WEB_BASE_URL, webBaseUrl);
        String corsOrigins = String.join(",", props.getCors().getAllowedOrigins());
        List<String> offenders = offenders(props.getDeployment().getEnv(), emailProvider, values, corsOrigins);
        if (!offenders.isEmpty()) {
            throw new IllegalStateException("APP_ENV=prod but " + String.join(", ", offenders)
                    + " cannot open a production deployment: the guard refuses a credential this repository "
                    + "publishes, the examples' CHANGE_ME, your-domain.com and localhost placeholders, an empty "
                    + "value, a link base that only the server or nobody can open, a CORS allow-list the deployed "
                    + "shell is not in, and the console mail transport, which logs every reset link instead of "
                    + "mailing it. Set each credential to a random secret, APP_WEB_BASE_URL to the public origin, "
                    + "APP_CORS_ORIGINS to the shell's origin, and APP_EMAIL_PROVIDER=smtp with a relay; "
                    + "docs/DEPLOYMENT.md lists the steps.");
        }
    }

    /** The presented values alone; the cross-origin list, when it is not part of a boot, is not judged. */
    static List<String> offenders(String env, String emailProvider, Map<String, String> values) {
        return offenders(env, emailProvider, values, null);
    }

    /**
     * The configuration that cannot open a prod boot, in the order the values are
     * named; empty means the boot may proceed. The caller hands in every value the
     * boot presents, so reordering the map is reordering the operator's fix list.
     *
     * <p>The cross-origin list is a list, not a credential, so it arrives beside the
     * map and is named after the map's values, where {@code APP_CORS_ORIGINS} sits in
     * the constructor's order. Its entries are matched against the browser's
     * {@code Origin} header exactly, which is stricter than a URL: a bare host, a
     * trailing slash, a path or a query never matches. When the link base is itself
     * an offender it is skipped here — the operator is about to change it, so judging
     * the list against a value that will move would only add noise.
     */
    static List<String> offenders(String env, String emailProvider, Map<String, String> values,
            String corsOrigins) {
        if (env == null || !"prod".equalsIgnoreCase(env.trim())) {
            return List.of();
        }
        List<String> found = new ArrayList<>();
        values.forEach((envVar, value) -> {
            if (isPublished(envVar, value)) {
                found.add(envVar);
            }
        });
        if (corsOrigins != null) {
            boolean refused = isUnacceptableOriginList(corsOrigins);
            if (!refused && !found.contains(WEB_BASE_URL)) {
                String base = values.get(WEB_BASE_URL);
                if (base != null) {
                    refused = !admitsOrigin(corsOrigins, base);
                }
            }
            if (refused) {
                found.add(CORS_ORIGINS);
            }
        }
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
        boolean generic = value == null || value.isBlank() || value.startsWith(EXAMPLE_PLACEHOLDER);
        if (WEB_BASE_URL.equals(envVar)) {
            return generic || PUBLISHED.get(envVar).contains(value) || isUnreachableBaseUrl(value);
        }
        return generic || PUBLISHED.get(envVar).contains(value);
    }

    /**
     * Whether a link base cannot be opened by the reader: not an http(s) URL at all,
     * a loopback host, or the example's own domain. The example literal is in
     * `PUBLISHED` too, but the host rule also catches its trailing-slash and scheme
     * variants, which a copying operator is just as likely to leave in place.
     */
    private static boolean isUnreachableBaseUrl(String value) {
        URI uri;
        try {
            uri = URI.create(value.trim());
        } catch (IllegalArgumentException e) {
            return true;
        }
        return !isPublicHttpUrl(uri);
    }

    /** An http(s) URL whose host is one a browser can reach from outside this machine. */
    private static boolean isPublicHttpUrl(URI uri) {
        String scheme = uri.getScheme();
        String host = uri.getHost();
        if (scheme == null || host == null
                || !(scheme.equalsIgnoreCase("http") || scheme.equalsIgnoreCase("https"))) {
            return false;
        }
        String name = host.toLowerCase(Locale.ROOT);
        return !(name.equals("localhost") || name.endsWith(".localhost") || name.startsWith("127.")
                || name.equals("::1") || name.equals("[::1]") || name.equals("0.0.0.0")
                || name.equals(EXAMPLE_HOST) || name.endsWith("." + EXAMPLE_HOST));
    }

    /** Every comma-separated entry must be a bare public http(s) origin; an empty list is refused. */
    private static boolean isUnacceptableOriginList(String origins) {
        for (String entry : origins.split(",", -1)) {
            if (!isBareWebOrigin(entry.trim())) {
                return true;
            }
        }
        return false;
    }

    /**
     * Whether the value is an origin the browser's `Origin` header can equal: scheme,
     * host and port only. Spring compares the header to the list literally, so a
     * trailing slash, a path, a query or the example's CHANGE_ME placeholder would
     * sit in the list and match nothing.
     */
    private static boolean isBareWebOrigin(String value) {
        if (value.isEmpty() || value.startsWith(EXAMPLE_PLACEHOLDER)) {
            return false;
        }
        URI uri;
        try {
            uri = URI.create(value);
        } catch (IllegalArgumentException e) {
            return false;
        }
        if (!isPublicHttpUrl(uri)) {
            return false;
        }
        boolean bare = uri.getRawPath() == null || uri.getRawPath().isEmpty();
        return bare && uri.getRawQuery() == null && uri.getRawFragment() == null && uri.getRawUserInfo() == null;
    }

    /** Whether the list names the origin the mailed links open, i.e. the deployed shell's own. */
    private static boolean admitsOrigin(String origins, String baseUrl) {
        String shell = normalizedOrigin(baseUrl);
        if (shell.isEmpty()) {
            return true;
        }
        return Arrays.stream(origins.split(",", -1))
                .map(String::trim)
                .map(ProductionGuard::normalizedOrigin)
                .anyMatch(shell::equals);
    }

    /** The origin the `Origin` header would carry: lowercased scheme and host, port only when given. */
    private static String normalizedOrigin(String value) {
        URI uri;
        try {
            uri = URI.create(value.trim());
        } catch (IllegalArgumentException e) {
            return "";
        }
        if (uri.getScheme() == null || uri.getHost() == null) {
            return "";
        }
        return uri.getScheme().toLowerCase(Locale.ROOT) + "://" + uri.getHost().toLowerCase(Locale.ROOT)
                + (uri.getPort() == -1 ? "" : ":" + uri.getPort());
    }
}
