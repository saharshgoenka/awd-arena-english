'use strict';
const jwt = require('jsonwebtoken');

// HMAC key used to sign and verify legitimately-issued HS256 tokens. Disjoint from
// flag_3's password hashing (MD5) — recovering one reveals nothing about the other.
const JWT_SECRET = 'n7-Qw2rT9kLmP4xZ-taskflow-signing';

// flag_5 (A07 Authentication Failures → token forgery). The verifier inspects the
// token's own `alg` header to decide how to validate it, and honours `alg: none`
// (RFC 7519's unsecured JWT) by trusting the payload with NO signature check. An
// attacker holding any low-priv token can re-encode its header as {"alg":"none"},
// flip `role` to `admin`, drop the signature, and be trusted — a pure base64
// forgery requiring only stdlib. Legit tokens still verify via HS256.
function requireAuth(req, res, next) {
  const cookieToken = req.cookies && req.cookies.token;
  const bearerToken =
    req.headers.authorization && req.headers.authorization.startsWith('Bearer ')
      ? req.headers.authorization.slice(7)
      : null;
  const token = cookieToken || bearerToken;
  if (!token) {
    return res.status(401).json({ error: 'Authentication required' });
  }
  try {
    const parts = token.split('.');
    const header = JSON.parse(Buffer.from(parts[0], 'base64url').toString('utf8'));
    if (header.alg === 'none') {
      // VULNERABLE: unsecured tokens are accepted without verifying a signature.
      req.user = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
      return next();
    }
    const decoded = jwt.verify(token, JWT_SECRET, { algorithms: ['HS256'] });
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid token' });
  }
}

function requireRole(role) {
  return (req, res, next) => {
    if (!req.user || req.user.role !== role) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    next();
  };
}

module.exports = { requireAuth, requireRole, JWT_SECRET };
