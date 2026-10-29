package com.careeros.push.service;

import java.math.BigInteger;
import java.security.GeneralSecurityException;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.ECPrivateKey;
import java.security.interfaces.ECPublicKey;
import java.security.spec.ECGenParameterSpec;
import java.util.Base64;

/** P-256 fixtures for the VAPID tests, in the two formats the deployment accepts. */
public final class VapidTestKeys {

    private VapidTestKeys() {
    }

    public static KeyPair generate() {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("EC");
            generator.initialize(new ECGenParameterSpec("secp256r1"));
            return generator.generateKeyPair();
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException(e);
        }
    }

    /** The browser's `applicationServerKey`: uncompressed point, base64url, no padding. */
    public static String publicKey(ECPublicKey key) {
        byte[] out = new byte[65];
        out[0] = 0x04;
        write(key.getW().getAffineX(), out, 1);
        write(key.getW().getAffineY(), out, 33);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(out);
    }

    /** The raw 32-byte scalar, as the `web-push` CLI generates it. */
    public static String rawPrivateKey(ECPrivateKey key) {
        byte[] out = new byte[32];
        write(key.getS(), out, 0);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(out);
    }

    /** The same scalar in PKCS#8 DER, as openssl and Java key stores hand it over. */
    public static String pkcs8PrivateKey(ECPrivateKey key) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(key.getEncoded());
    }

    private static void write(BigInteger coordinate, byte[] target, int offset) {
        byte[] raw = coordinate.toByteArray();
        int from = raw.length > 32 ? raw.length - 32 : 0;
        int length = raw.length - from;
        System.arraycopy(raw, from, target, offset + 32 - length, length);
    }
}
