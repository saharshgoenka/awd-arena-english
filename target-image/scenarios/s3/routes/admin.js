'use strict';
const express = require('express');
const router = express.Router();
const db = require('../db');
const { requireAuth, requireRole } = require('../middleware/auth');

// flag_1: authentication exists, but the admin role check is intentionally missing
router.get('/config', requireAuth, (req, res) => {
  // Read from env, not the `flags` table: only flag_4 lives in the DB (the
  // SQLi-reachable flag). Keeping flag_1 here let the flag_4 UNION dump it too.
  const flag = { value: process.env.FLAG_1 || 'FLAG{missing}' };
  res.json({
    config: {
      maintenance: false,
      version: '2.1.0',
      log_level: 'info',
      token: flag.value,
    },
  });
});

router.get('/users', requireAuth, requireRole('admin'), (req, res) => {
  const users = db.prepare('SELECT id, username, role FROM users').all();
  res.json({ users });
});

module.exports = router;
