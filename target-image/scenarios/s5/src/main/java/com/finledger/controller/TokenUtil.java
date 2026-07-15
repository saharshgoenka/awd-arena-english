package com.finledger.controller;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

public final class TokenUtil {
    private static final byte[] TOKEN_SECRET = "finledger-portal-signing-key-2024".getBytes(StandardCharsets.UTF_8);

    private TokenUtil() {}

    public record Claims(String username, String role) {}

    public static String issue(String username, String role) {
        String header = b64("{\"alg\":\"HS256\",\"typ\":\"JWT\"}");
        String payload = b64("{\"sub\":\"" + username + "\",\"role\":\"" + role + "\"}");
        return header + "." + payload + "." + sign(header + "." + payload);
    }

    public static Claims verify(String token) {
        try {
            String[] parts = token.split("\\.", -1);
            if (parts.length != 3) {
                return null;
            }
            String headerJson = new String(Base64.getUrlDecoder().decode(pad(parts[0])), StandardCharsets.UTF_8);
            String payloadJson = new String(Base64.getUrlDecoder().decode(pad(parts[1])), StandardCharsets.UTF_8);
            if (headerJson.contains("\"alg\":\"none\"") || headerJson.contains("\"alg\": \"none\"")) {
                // VULNERABLE: unsecured tokens are trusted without signature verification.
                return parseClaims(payloadJson);
            }
            if (!headerJson.contains("\"alg\":\"HS256\"") && !headerJson.contains("\"alg\": \"HS256\"")) {
                return null;
            }
            String expected = sign(parts[0] + "." + parts[1]);
            if (!constantTimeEquals(expected, parts[2])) {
                return null;
            }
            return parseClaims(payloadJson);
        } catch (Exception e) {
            return null;
        }
    }

    private static Claims parseClaims(String json) {
        String username = extract(json, "sub");
        String role = extract(json, "role");
        if (username.isBlank() || role.isBlank()) {
            return null;
        }
        return new Claims(username, role);
    }

    private static String extract(String json, String key) {
        String needle = "\"" + key + "\":\"";
        int start = json.indexOf(needle);
        if (start < 0) {
            needle = "\"" + key + "\": \"";
            start = json.indexOf(needle);
        }
        if (start < 0) {
            return "";
        }
        start += needle.length();
        int end = json.indexOf('"', start);
        return end > start ? json.substring(start, end) : "";
    }

    private static String sign(String data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(TOKEN_SECRET, "HmacSHA256"));
            return Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(mac.doFinal(data.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("HMAC unavailable", e);
        }
    }

    private static String b64(String value) {
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private static byte[] pad(String value) {
        return (value + "=".repeat((4 - value.length() % 4) % 4)).getBytes(StandardCharsets.UTF_8);
    }

    private static boolean constantTimeEquals(String a, String b) {
        byte[] left = a.getBytes(StandardCharsets.UTF_8);
        byte[] right = b.getBytes(StandardCharsets.UTF_8);
        int diff = left.length ^ right.length;
        for (int i = 0; i < Math.min(left.length, right.length); i++) {
            diff |= left[i] ^ right[i];
        }
        return diff == 0;
    }
}
