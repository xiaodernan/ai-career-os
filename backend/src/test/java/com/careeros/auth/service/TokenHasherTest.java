package com.careeros.auth.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class TokenHasherTest {

    @Test
    void sha256MatchesKnownVector() {
        assertEquals("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                TokenHasher.sha256Hex("abc"));
    }

    @Test
    void sha256IsDeterministicAndDistinct() {
        assertEquals(TokenHasher.sha256Hex("token-a"), TokenHasher.sha256Hex("token-a"));
        assertNotEquals(TokenHasher.sha256Hex("token-a"), TokenHasher.sha256Hex("token-b"));
    }

    @Test
    void opaqueTokensAreUrlSafeAndUnique() {
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < 1000; i++) {
            String token = TokenHasher.generateOpaqueToken();
            assertTrue(token.length() >= 40, "token must carry >= 256 bits of entropy");
            assertTrue(token.matches("[A-Za-z0-9_-]+"), "url-safe charset only");
            assertTrue(seen.add(token), "tokens must never collide");
        }
    }
}
