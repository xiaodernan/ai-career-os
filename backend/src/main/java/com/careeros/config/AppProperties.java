package com.careeros.config;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Binds every `app.*` key from application.yml. */
@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private final Cors cors = new Cors();
    private final Jwt jwt = new Jwt();
    private final Internal internal = new Internal();
    private final Storage storage = new Storage();
    private final AiService aiService = new AiService();
    private final Ratelimit ratelimit = new Ratelimit();
    private final Upload upload = new Upload();
    private final Retention retention = new Retention();
    private final Http http = new Http();
    private final Deployment deployment = new Deployment();
    private final Push push = new Push();

    public Cors getCors() {
        return cors;
    }

    public Jwt getJwt() {
        return jwt;
    }

    public Internal getInternal() {
        return internal;
    }

    public Storage getStorage() {
        return storage;
    }

    public AiService getAiService() {
        return aiService;
    }

    public Ratelimit getRatelimit() {
        return ratelimit;
    }

    public Upload getUpload() {
        return upload;
    }

    public Retention getRetention() {
        return retention;
    }

    public Http getHttp() {
        return http;
    }

    public Deployment getDeployment() {
        return deployment;
    }

    public Push getPush() {
        return push;
    }

    public static class Push {
        /**
         * The browser's `applicationServerKey`: base64url of an uncompressed P-256 point.
         * Empty together with the private key means push is off (PushConfig ships a no-op).
         */
        private String vapidPublicKey = "";
        /** The raw 32-byte scalar or a PKCS#8 blob, base64url. Never leaves the server. */
        private String vapidPrivateKey = "";
        /** RFC 8292's `sub` contact claim; empty falls back to the deployment's public web origin. */
        private String contact = "";
        /** How long a push service may hold a wake (RFC 8030), in seconds; half a day. */
        private int ttlSeconds = 43200;

        public String getVapidPublicKey() {
            return vapidPublicKey;
        }

        public void setVapidPublicKey(String vapidPublicKey) {
            this.vapidPublicKey = vapidPublicKey;
        }

        public String getVapidPrivateKey() {
            return vapidPrivateKey;
        }

        public void setVapidPrivateKey(String vapidPrivateKey) {
            this.vapidPrivateKey = vapidPrivateKey;
        }

        public String getContact() {
            return contact;
        }

        public void setContact(String contact) {
            this.contact = contact;
        }

        public int getTtlSeconds() {
            return ttlSeconds;
        }

        public void setTtlSeconds(int ttlSeconds) {
            this.ttlSeconds = ttlSeconds;
        }
    }

    public static class Deployment {
        /**
         * {@code dev} unless the deployment declares {@code APP_ENV=prod}. A prod boot
         * refuses the credentials this repository publishes (see ProductionGuard).
         */
        private String env = "dev";

        public String getEnv() {
            return env;
        }

        public void setEnv(String env) {
            this.env = env;
        }
    }

    public static class Http {
        /**
         * Whether X-Forwarded-For was written by a trusted reverse proxy. Off by
         * default: a service reached directly must count the socket's address, or a
         * client can rotate the header to buy a fresh login bucket per request.
         */
        private boolean trustForwardedFor = false;

        public boolean isTrustForwardedFor() {
            return trustForwardedFor;
        }

        public void setTrustForwardedFor(boolean trustForwardedFor) {
            this.trustForwardedFor = trustForwardedFor;
        }
    }

    public static class Cors {
        private List<String> allowedOrigins = List.of("http://localhost:3000");

        public List<String> getAllowedOrigins() {
            return allowedOrigins;
        }

        public void setAllowedOrigins(List<String> allowedOrigins) {
            this.allowedOrigins = allowedOrigins;
        }
    }

    public static class Jwt {
        private String secret;
        private int accessTtlMinutes = 15;
        private int refreshTtlDays = 30;

        public String getSecret() {
            return secret;
        }

        public void setSecret(String secret) {
            this.secret = secret;
        }

        public int getAccessTtlMinutes() {
            return accessTtlMinutes;
        }

        public void setAccessTtlMinutes(int accessTtlMinutes) {
            this.accessTtlMinutes = accessTtlMinutes;
        }

        public int getRefreshTtlDays() {
            return refreshTtlDays;
        }

        public void setRefreshTtlDays(int refreshTtlDays) {
            this.refreshTtlDays = refreshTtlDays;
        }
    }

    public static class Internal {
        private String token;

        public String getToken() {
            return token;
        }

        public void setToken(String token) {
            this.token = token;
        }
    }

    public static class Storage {
        private boolean enabled = true;
        private String endpoint;
        private String accessKey;
        private String secretKey;
        private String bucket;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public String getEndpoint() {
            return endpoint;
        }

        public void setEndpoint(String endpoint) {
            this.endpoint = endpoint;
        }

        public String getAccessKey() {
            return accessKey;
        }

        public void setAccessKey(String accessKey) {
            this.accessKey = accessKey;
        }

        public String getSecretKey() {
            return secretKey;
        }

        public void setSecretKey(String secretKey) {
            this.secretKey = secretKey;
        }

        public String getBucket() {
            return bucket;
        }

        public void setBucket(String bucket) {
            this.bucket = bucket;
        }
    }

    public static class AiService {
        private String baseUrl = "http://localhost:8000";

        public String getBaseUrl() {
            return baseUrl;
        }

        public void setBaseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
        }
    }

    public static class Ratelimit {
        private boolean enabled = true;
        private int authPerMinute = 10;
        private int aiPerMinute = 30;
        private int mailPerMinute = 5;

        public boolean isEnabled() {
            return enabled;
        }

        public void setEnabled(boolean enabled) {
            this.enabled = enabled;
        }

        public int getAuthPerMinute() {
            return authPerMinute;
        }

        public void setAuthPerMinute(int authPerMinute) {
            this.authPerMinute = authPerMinute;
        }

        public int getAiPerMinute() {
            return aiPerMinute;
        }

        public void setAiPerMinute(int aiPerMinute) {
            this.aiPerMinute = aiPerMinute;
        }

        public int getMailPerMinute() {
            return mailPerMinute;
        }

        public void setMailPerMinute(int mailPerMinute) {
            this.mailPerMinute = mailPerMinute;
        }
    }

    public static class Upload {
        private long maxFileSizeBytes = 20L * 1024 * 1024;
        private int presignedUrlTtlSeconds = 600;

        public long getMaxFileSizeBytes() {
            return maxFileSizeBytes;
        }

        public void setMaxFileSizeBytes(long maxFileSizeBytes) {
            this.maxFileSizeBytes = maxFileSizeBytes;
        }

        public int getPresignedUrlTtlSeconds() {
            return presignedUrlTtlSeconds;
        }

        public void setPresignedUrlTtlSeconds(int presignedUrlTtlSeconds) {
            this.presignedUrlTtlSeconds = presignedUrlTtlSeconds;
        }
    }

    public static class Retention {
        /** Days past expiry an expired credential row is kept before the nightly sweep. */
        private int expiredTokenDays = 30;

        public int getExpiredTokenDays() {
            return expiredTokenDays;
        }

        public void setExpiredTokenDays(int expiredTokenDays) {
            this.expiredTokenDays = expiredTokenDays;
        }
    }
}
