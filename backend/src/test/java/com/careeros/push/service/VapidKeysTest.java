package com.careeros.push.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.security.KeyPair;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import org.junit.jupiter.api.Test;

class VapidKeysTest {

    private final KeyPair pair = VapidTestKeys.generate();
    private final ECPublicKey publicKey = (ECPublicKey) pair.getPublic();
    private final ECPrivateKey privateKey = (ECPrivateKey) pair.getPrivate();
    private final String publicValue = VapidTestKeys.publicKey(publicKey);

    @Test
    void aRawScalarAndItsPublicPointAreOnePair() {
        VapidKeys keys = VapidKeys.parse(publicValue, VapidTestKeys.rawPrivateKey(privateKey));

        assertThat(keys.publicKeyBase64Url()).isEqualTo(publicValue);
        assertThat(keys.publicKeyBase64Url()).doesNotEndWith("=");
        assertThat(keys.privateKey().getS()).isEqualTo(privateKey.getS());
    }

    @Test
    void aPkcs8PrivateKeyIsTheSameScalar() {
        VapidKeys keys = VapidKeys.parse(publicValue, VapidTestKeys.pkcs8PrivateKey(privateKey));

        assertThat(keys.privateKey().getS()).isEqualTo(privateKey.getS());
    }

    @Test
    void paddingIsStrippedRatherThanRefused() {
        String padded = publicValue + "==";
        VapidKeys keys = VapidKeys.parse(padded, VapidTestKeys.rawPrivateKey(privateKey));

        assertThat(keys.publicKeyBase64Url()).isEqualTo(publicValue);
    }

    @Test
    void twoWellFormedHalvesFromDifferentPairsAreRefused() {
        KeyPair other = VapidTestKeys.generate();

        assertThatThrownBy(() -> VapidKeys.parse(VapidTestKeys.publicKey((ECPublicKey) other.getPublic()),
                VapidTestKeys.rawPrivateKey(privateKey)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("not a matching P-256 pair");
    }

    @Test
    void aPublicPointOfTheWrongLengthIsRefused() {
        String shortPoint = java.util.Base64.getUrlEncoder().withoutPadding()
                .encodeToString(new byte[64]);

        assertThatThrownBy(() -> VapidKeys.parse(shortPoint, VapidTestKeys.rawPrivateKey(privateKey)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("uncompressed P-256 point");
    }

    @Test
    void aValueThatIsNotBase64UrlIsRefused() {
        assertThatThrownBy(() -> VapidKeys.parse("not base64!", VapidTestKeys.rawPrivateKey(privateKey)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("not base64url");
    }

    @Test
    void aHalfPairIsRefusedByTheParserToo() {
        assertThatThrownBy(() -> VapidKeys.parse("", VapidTestKeys.rawPrivateKey(privateKey)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("app.push.vapid-public-key is set to an empty value");
    }

    @Test
    void aPrivateKeyThatIsNeitherAScalarNorPkcs8IsRefused() {
        String junk = java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(new byte[40]);

        assertThatThrownBy(() -> VapidKeys.parse(publicValue, junk))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("32-byte P-256 scalar");
    }
}
