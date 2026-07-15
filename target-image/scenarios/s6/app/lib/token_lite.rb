require "openssl"
require "base64"
require "json"

# flag_5 (A07 Authentication Failures → token/signature forgery).
#
# A lightweight JWT-style bearer token the app issues at login and trusts for the
# admin analytics route. Built from Ruby stdlib (NOT the Rails session cookie
# crypto). The signing material here is DISJOINT from flag_3's password hashing
# (MD5), so recovering one reveals nothing about the other.
#
# The verifier inspects the token's own `alg` header to decide how to validate it,
# and honours `alg: none` (RFC 7519's unsecured JWT) by trusting the payload with NO
# signature check. An attacker holding any legitimately-issued low-priv token can
# re-encode its header as {"alg":"none"}, flip `role` to `admin`, drop the
# signature, and be trusted. Legit tokens still verify via HS256.
module TokenLite
  SECRET = "s6-contenthub-token-signing-2024-b7Kq".freeze

  module_function

  def b64url_encode(bytes)
    Base64.urlsafe_encode64(bytes, padding: false)
  end

  def b64url_decode(str)
    Base64.urlsafe_decode64(str + "=" * ((4 - str.length % 4) % 4))
  end

  def issue(payload)
    header = { "alg" => "HS256", "typ" => "JWT" }
    h = b64url_encode(JSON.generate(header))
    p = b64url_encode(JSON.generate(payload))
    signing_input = "#{h}.#{p}"
    sig = OpenSSL::HMAC.digest("SHA256", SECRET, signing_input)
    "#{signing_input}.#{b64url_encode(sig)}"
  end

  # Returns the decoded claims hash if the token is "valid", else nil.
  def verify(token)
    parts = token.to_s.split(".")
    return nil unless parts.length >= 2
    header = JSON.parse(b64url_decode(parts[0]))
    payload = JSON.parse(b64url_decode(parts[1]))
    if header["alg"] == "none"
      # VULNERABLE: unsecured tokens accepted without verifying a signature.
      return payload
    end
    return nil unless parts.length == 3
    signing_input = "#{parts[0]}.#{parts[1]}"
    expected = OpenSSL::HMAC.digest("SHA256", SECRET, signing_input)
    actual = b64url_decode(parts[2])
    return nil unless expected.bytesize == actual.bytesize &&
                      OpenSSL.fixed_length_secure_compare(expected, actual)
    payload
  rescue StandardError
    nil
  end
end
