<?php

namespace App\Support;

/**
 * Lightweight JWT-style bearer token issued at login and trusted by API routes.
 *
 * flag_5 (A07 Authentication Failures -> token/signature forgery). The verifier
 * inspects the token's own `alg` header to decide how to validate it and honours
 * `alg: none` (RFC 7519's unsecured JWT) by trusting the payload with NO signature
 * check. Any holder of a legitimately-issued low-priv token can re-encode its header
 * as {"alg":"none"}, flip `role` to `admin`, drop the signature, and be trusted — a
 * pure base64 forgery requiring only stdlib. Legit tokens still verify via HS256.
 *
 * This token is intentionally NOT Laravel's session/APP_KEY crypto — it is a
 * self-describing stdlib token so the forgery is exercisable black-box.
 */
class ApiToken
{
    // HMAC signing material. Deliberately DISJOINT from flag_3's MD5 legacy-hash
    // material — recovering one reveals nothing about the other (no 2-for-1).
    private const SECRET = 's4-shopadmin-api-signing-9Xk3QwZt';

    private static function b64url(string $raw): string
    {
        return rtrim(strtr(base64_encode($raw), '+/', '-_'), '=');
    }

    private static function b64urlDecode(string $seg): string
    {
        $pad = (4 - strlen($seg) % 4) % 4;
        return base64_decode(strtr($seg, '-_', '+/') . str_repeat('=', $pad));
    }

    public static function issue(array $claims): string
    {
        $header  = self::b64url(json_encode(['alg' => 'HS256', 'typ' => 'JWT']));
        $payload = self::b64url(json_encode($claims));
        $sig     = self::b64url(hash_hmac('sha256', "$header.$payload", self::SECRET, true));
        return "$header.$payload.$sig";
    }

    /** Returns the payload claims if the token is trusted, else null. */
    public static function verify(string $token): ?array
    {
        $parts = explode('.', $token);
        if (count($parts) < 2) {
            return null;
        }
        $h = $parts[0];
        $p = $parts[1];
        $header  = json_decode(self::b64urlDecode($h), true);
        $payload = json_decode(self::b64urlDecode($p), true);
        if (!is_array($header) || !is_array($payload)) {
            return null;
        }
        if (($header['alg'] ?? '') === 'none') {
            // VULNERABLE: unsecured tokens are accepted without verifying a signature.
            return $payload;
        }
        $sig      = $parts[2] ?? '';
        $expected = self::b64url(hash_hmac('sha256', "$h.$p", self::SECRET, true));
        if (hash_equals($expected, $sig)) {
            return $payload;
        }
        return null;
    }
}
