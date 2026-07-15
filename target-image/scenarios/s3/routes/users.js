'use strict';
const express = require('express');
const router = express.Router();
const db = require('../db');
const { requireAuth } = require('../middleware/auth');

// GET /api/users/me — flag_3: returns full user object including password_hash
router.get('/me', requireAuth, (req, res) => {
  const user = db.prepare('SELECT * FROM users WHERE id = ?').get(req.user.userId);
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json(user);
});

// GET /api/users/lookup/:username — any authenticated user can read legacy hashes
router.get('/lookup/:username', requireAuth, (req, res) => {
  const user = db.prepare('SELECT * FROM users WHERE username = ?').get(req.params.username);
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json(user);
});

// GET /api/users/secret — devuser-only endpoint. flag_3 moved to the encrypted
// export vault (A02 keystream-reuse recovery); no plaintext secret is served here.
router.get('/secret', requireAuth, (req, res) => {
  if (req.user.username !== 'devuser') {
    return res.status(403).json({ error: 'Access restricted to devuser account' });
  }
  res.json({
    message: 'Developer report tokens are no longer stored in plaintext here; '
      + 'retrieve them from the encrypted export vault (/exports/encrypted?item=vault).',
  });
});

// GET /api/users — list users (admin only)
router.get('/', requireAuth, (req, res) => {
  if (req.user.role !== 'admin') {
    return res.status(403).json({ error: 'Forbidden' });
  }
  const users = db.prepare('SELECT id, username, role FROM users').all();
  res.json({ users });
});

module.exports = router;
