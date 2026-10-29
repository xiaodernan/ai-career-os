package com.careeros.push.service;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.AlgorithmParameters;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.Signature;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.security.spec.ECGenParameterSpec;
import java.security.spec.ECParameterSpec;
import java.security.spec.ECPoint;
import java.security.spec.ECPrivateKeySpec;
import java.security.spec.ECPublicKeySpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Base64;

/**
 * The deployment's VAPID identity, parsed once at boot (roadmap 33.2).
 *
 * <p>A VAPID key pair is an ordinary P-256 key pair, but the two halves travel in the formats
 * the ecosystem hands them over in, not as PEM. The public key is the uncompressed point --
 * 65 bytes beginning with {@code 0x04} -- base64url-encoded without padding, because that is
 * exactly what the browser passes to {@code pushManager.subscribe} as its
 * {@code applicationServerKey} and what the Authorization header echoes as {@code k}. The
 * private key is usually the raw 32-byte scalar (the {@code web-push} CLI's form), but a
 * PKCS#8 DER blob copied from an openssl or Java tool is accepted too, decoded by its leading
 * SEQUENCE tag; both are read as the same scalar.
 *
 * <p>Parsing is where a half-usable pair is refused: a wrong length, a point that is not on
 * P-256, a private key from another curve, or two halves that simply do not belong together.
 * The last check is a probe signature verified with the configured public key, because none of
 * the byte-length checks can tell a mismatched pair from a matched one -- and a mismatched pair
 * is every push refused with 401, one morning at a time, long after the boot looked fine.
 */
public final class VapidKeys {

    private static final int COORDINATE_BYTES = 32;
    private static final int PUBLIC_KEY_BYTES = 1 + 2 * COORDINATE_BYTES;
    private static final int PRIVATE_KEY_BYTES = 32;
    private static final ECParameterSpec P256 = p256();
    private static final byte[] PROBE = "careeros-vapid-key-check".getBytes(StandardCharsets.UTF_8);

    private final ECPrivateKey privateKey;
    private final ECPublicKey publicKey;
    private final String publicKeyBase64Url;

    private VapidKeys(ECPrivateKey privateKey, ECPublicKey publicKey, String publicKeyBase64Url) {
        this.privateKey = privateKey;
        this.publicKey = publicKey;
        this.publicKeyBase64Url = publicKeyBase64Url;
    }

    /**
     * The pair named by `app.push.vapid-public-key` and `app.push.vapid-private-key`.
     *
     * @throws IllegalStateException when either half is malformed or the two are not a pair
     */
    public static VapidKeys parse(String publicKeyBase64Url, String privateKeyBase64Url) {
        ECPublicKey publicKey = publicKey(publicKeyBase64Url);
        ECPrivateKey privateKey = privateKey(privateKeyBase64Url);
        if (privateKey.getParams() != null
                && privateKey.getParams().getCurve().getField().getFieldSize() != 256) {
            throw new IllegalStateException("app.push.vapid-private-key is not a P-256 key");
        }
        if (!verifies(privateKey, publicKey)) {
            throw new IllegalStateException("app.push.vapid-public-key and app.push.vapid-private-key "
                    + "are not a matching P-256 pair: the probe signature does not verify");
        }
        return new VapidKeys(privateKey, publicKey,
                Base64.getUrlEncoder().withoutPadding().encodeToString(uncompressed(publicKey)));
    }

    public ECPrivateKey privateKey() {
        return privateKey;
    }

    public ECPublicKey publicKey() {
        return publicKey;
    }

    /** The `k` half of the Authorization header: the same 65-byte point the browser subscribed with. */
    public String publicKeyBase64Url() {
        return publicKeyBase64Url;
    }

    private static ECPublicKey publicKey(String encoded) {
        byte[] bytes = decode(encoded, "app.push.vapid-public-key");
        if (bytes.length != PUBLIC_KEY_BYTES || bytes[0] != 0x04) {
            throw new IllegalStateException("app.push.vapid-public-key must be the base64url of an "
                    + "uncompressed P-256 point (65 bytes beginning 0x04)");
        }
        BigInteger x = new BigInteger(1, slice(bytes, 1, COORDINATE_BYTES));
        BigInteger y = new BigInteger(1, slice(bytes, 1 + COORDINATE_BYTES, COORDINATE_BYTES));
        try {
            return (ECPublicKey) KeyFactory.getInstance("EC")
                    .generatePublic(new ECPublicKeySpec(new ECPoint(x, y), P256));
        } catch (GeneralSecurityException | IllegalArgumentException e) {
            throw new IllegalStateException("app.push.vapid-public-key is not a point on P-256", e);
        }
    }

    private static ECPrivateKey privateKey(String encoded) {
        byte[] bytes = decode(encoded, "app.push.vapid-private-key");
        try {
            KeyFactory factory = KeyFactory.getInstance("EC");
            if (bytes.length == PRIVATE_KEY_BYTES) {
                return (ECPrivateKey) factory.generatePrivate(
                        new ECPrivateKeySpec(new BigInteger(1, bytes), P256));
            }
            if (bytes.length > 0 && bytes[0] == 0x30) {
                // A DER SEQUENCE: some tools hand the pair over as PKCS#8 instead of a raw scalar.
                return (ECPrivateKey) factory.generatePrivate(new PKCS8EncodedKeySpec(bytes));
            }
        } catch (GeneralSecurityException | IllegalArgumentException e) {
            throw new IllegalStateException("app.push.vapid-private-key is not a usable P-256 private key", e);
        }
        throw new IllegalStateException("app.push.vapid-private-key must be the base64url of a 32-byte "
                + "P-256 scalar or of a PKCS#8 DER blob");
    }

    /** The probe signature is the only check that can see two well-formed halves from different pairs. */
    private static boolean verifies(ECPrivateKey privateKey, ECPublicKey publicKey) {
        try {
            Signature signer = Signature.getInstance("SHA256withECDSA");
            signer.initSign(privateKey);
            signer.update(PROBE);
            byte[] signature = signer.sign();
            Signature verifier = Signature.getInstance("SHA256withECDSA");
            verifier.initVerify(publicKey);
            verifier.update(PROBE);
            return verifier.verify(signature);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("the VAPID key pair could not be exercised", e);
        }
    }

    private static byte[] decode(String encoded, String knob) {
        String value = encoded == null ? "" : encoded.trim();
        if (value.isEmpty()) {
            throw new IllegalStateException(knob + " is set to an empty value");
        }
        try {
            return Base64.getUrlDecoder().decode(value.replace("=", ""));
        } catch (IllegalArgumentException e) {
            throw new IllegalStateException(knob + " is not base64url", e);
        }
    }

    private static byte[] uncompressed(ECPublicKey key) {
        byte[] out = new byte[PUBLIC_KEY_BYTES];
        out[0] = 0x04;
        write(key.getW().getAffineX(), out, 1);
        write(key.getW().getAffineY(), out, 1 + COORDINATE_BYTES);
        return out;
    }

    private static void write(BigInteger coordinate, byte[] target, int offset) {
        byte[] raw = coordinate.toByteArray();
        int from = 0;
        int length = raw.length;
        if (length > COORDINATE_BYTES) {
            from = length - COORDINATE_BYTES;
            length = COORDINATE_BYTES;
        }
        System.arraycopy(raw, from, target, offset + COORDINATE_BYTES - length, length);
    }

    private static byte[] slice(byte[] source, int offset, int length) {
        byte[] out = new byte[length];
        System.arraycopy(source, offset, out, 0, length);
        return out;
    }

    private static ECParameterSpec p256() {
        try {
            AlgorithmParameters parameters = AlgorithmParameters.getInstance("EC");
            parameters.init(new ECGenParameterSpec("secp256r1"));
            return parameters.getParameterSpec(ECParameterSpec.class);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("P-256 parameters are not available in this JDK", e);
        }
    }

}
