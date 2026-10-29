package com.careeros.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.push.entity.PushSubscription;
import com.careeros.push.service.NoopPushSender;
import com.careeros.push.service.PushSender;
import com.careeros.push.service.VapidTestKeys;
import com.careeros.push.service.VapidWebPushSender;
import java.security.KeyPair;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class PushConfigTest {

    private static final String WEB = "https://career.example.org";

    private final PushConfig config = new PushConfig();
    private final KeyPair pair = VapidTestKeys.generate();
    private final String publicKey = VapidTestKeys.publicKey((ECPublicKey) pair.getPublic());
    private final String privateKey = VapidTestKeys.rawPrivateKey((ECPrivateKey) pair.getPrivate());

    @Test
    void noKeysMeansANoopThatReportsWhyNothingLeft() {
        PushSender sender = config.pushSender(props(), WEB);

        assertThat(sender).isInstanceOf(NoopPushSender.class);
        assertThat(sender.send(subscription())).isEqualTo(PushSender.Outcome.NOT_CONFIGURED);
    }

    @Test
    void halfAPairIsABootRefusalInEitherDirection() {
        assertThatThrownBy(() -> config.pushSender(props(publicKey, "", ""), WEB))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.push.vapid-private-key")
                .hasMessageContaining("both VAPID keys or neither");
        assertThatThrownBy(() -> config.pushSender(props("", privateKey, ""), WEB))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.push.vapid-public-key");
    }

    @Test
    void aRealPairBuildsTheVapidTransport() {
        PushSender sender = config.pushSender(props(publicKey, privateKey, ""), WEB);

        assertThat(sender).isInstanceOf(VapidWebPushSender.class);
    }

    @Test
    void theSubjectIsTheConfiguredContactOrThePublicOrigin() {
        assertThat(PushConfig.subject("mailto:ops@career.example.org", WEB))
                .isEqualTo("mailto:ops@career.example.org");
        assertThat(PushConfig.subject("   ", WEB)).isEqualTo(WEB);
        assertThat(PushConfig.subject(null, " https://career.example.org ")).isEqualTo(WEB);
        assertThat(PushConfig.subject("", "")).isEmpty();
    }

    @Test
    void aTtlOutsideTheRfcRangeIsABootRefusal() {
        AppProperties props = props(publicKey, privateKey, "");
        props.getPush().setTtlSeconds(0);
        assertThatThrownBy(() -> config.pushSender(props, WEB))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.push.ttl-seconds");

        props.getPush().setTtlSeconds(VapidWebPushSender.MAX_TTL_SECONDS + 1);
        assertThatThrownBy(() -> config.pushSender(props, WEB))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.push.ttl-seconds");
    }

    @Test
    void aMalformedOrMismatchedPairIsABootRefusal() {
        KeyPair other = VapidTestKeys.generate();
        String otherPrivate = VapidTestKeys.rawPrivateKey((ECPrivateKey) other.getPrivate());

        assertThatThrownBy(() -> config.pushSender(props("not base64!", privateKey, ""), WEB))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.push.vapid-public-key");
        assertThatThrownBy(() -> config.pushSender(props(publicKey, otherPrivate, ""), WEB))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("not a matching P-256 pair");
    }

    private static AppProperties props() {
        return props("", "", "");
    }

    private static AppProperties props(String publicKey, String privateKey, String subject) {
        AppProperties props = new AppProperties();
        props.getPush().setVapidPublicKey(publicKey);
        props.getPush().setVapidPrivateKey(privateKey);
        props.getPush().setContact(subject);
        return props;
    }

    private static PushSubscription subscription() {
        PushSubscription row = new PushSubscription();
        row.setUserId(UUID.randomUUID());
        row.setEndpointUrl("https://push.example.com/f/privacy");
        row.setP256dh("BP-public-key-placeholder");
        row.setAuth("auth-placeholder");
        return row;
    }
}
