package com.careeros.config;

import com.careeros.push.service.NoopPushSender;
import com.careeros.push.service.PushSender;
import com.careeros.push.service.VapidKeys;
import com.careeros.push.service.VapidWebPushSender;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * The one outbound Web Push bean, chosen by whether a VAPID key pair is configured (roadmap
 * 33.2).
 *
 * <p>Both keys or neither. With neither, push is simply off: registrations are still accepted,
 * because an install may opt browsers in before the operator generates keys and bringing the
 * keys later has to reach browsers that already opted in, but every wake answers "not
 * configured" and this boot line is where the operator learns why the bell is silent. With one
 * key, the operator meant to turn push on and did not finish -- a boot that runs is a deployment
 * whose pushes all fail, so it is refused here, in the same place the mail transport refuses a
 * relay without a host.
 */
@Configuration
public class PushConfig {

    private static final Logger log = LoggerFactory.getLogger(PushConfig.class);

    @Bean
    PushSender pushSender(AppProperties props,
            @Value("${app.web.base-url:http://localhost:3000}") String webBaseUrl) {
        String publicKey = clean(props.getPush().getVapidPublicKey());
        String privateKey = clean(props.getPush().getVapidPrivateKey());
        if (publicKey.isEmpty() && privateKey.isEmpty()) {
            log.warn("push is not configured: app.push.vapid-public-key and app.push.vapid-private-key "
                    + "are unset, so browsers can register but no wake will leave");
            return new NoopPushSender();
        }
        if (publicKey.isEmpty() || privateKey.isEmpty()) {
            throw new IllegalStateException("app.push needs both VAPID keys or neither: "
                    + (publicKey.isEmpty() ? "app.push.vapid-public-key" : "app.push.vapid-private-key")
                    + " is unset while the other half is configured");
        }
        String subject = subject(props.getPush().getContact(), webBaseUrl);
        if (subject.isEmpty()) {
            throw new IllegalStateException("a VAPID sender needs a subject: set app.push.contact "
                    + "or app.web.base-url");
        }
        return new VapidWebPushSender(VapidKeys.parse(publicKey, privateKey), subject,
                props.getPush().getTtlSeconds());
    }

    /**
     * RFC 8292 wants a contact in `sub`; an https URL is allowed, and the public origin is
     * the one address every deployment already has to configure.
     */
    static String subject(String configured, String webBaseUrl) {
        String value = clean(configured);
        return value.isEmpty() ? clean(webBaseUrl) : value;
    }

    private static String clean(String value) {
        return value == null ? "" : value.trim();
    }
}
