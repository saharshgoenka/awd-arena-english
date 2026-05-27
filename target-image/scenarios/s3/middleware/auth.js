'use strict';
const jwt = require('jsonwebtoken');

// flag_5 — weak secret; also used in jwt.verify below
const JWT_SECRET = 'supersecret';

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
    // flag_5 vulnerability: explicitly accepts alg:none tokens without signature verification
    const rawHeader = JSON.parse(Buffer.from(token.split('.')[0], 'base64url').toString());
    if (rawHeader.alg === 'none') {
      const decoded = jwt.decode(token);
      if (!decoded) throw new Error('decode failed');
      req.user = decoded;
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
