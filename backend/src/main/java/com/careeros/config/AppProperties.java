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
