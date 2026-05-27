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

// GET /api/users/secret — flag_3 target: devuser-only endpoint
router.get('/secret', requireAuth, (req, res) => {
  if (req.user.username !== 'devuser') {
    return res.status(403).json({ error: 'Access restricted to devuser account' });
  }
  const flag = db.prepare("SELECT value FROM flags WHERE name = 'flag_3'").get();
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
