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

// GET /api/users/secret — flag_3 target: devuser-only endpoint
router.get('/secret', requireAuth, (req, res) => {
  if (req.user.username !== 'devuser') {
    return res.status(403).json({ error: 'Access restricted to devuser account' });
  }
  // Read from env, not the `flags` table (only flag_4 stays in the DB so the
  // flag_4 SQLi UNION cannot dump flag_3).
  const flag = { value: process.env.FLAG_3 || 'FLAG{missing}' };
  res.json({ secret: flag.value, message: 'Developer secrets access granted' });
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
