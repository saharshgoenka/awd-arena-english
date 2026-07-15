'use strict';
const express = require('express');
const router = express.Router();
const db = require('../db');
const { requireAuth, requireRole } = require('../middleware/auth');

// Administrative configuration view — admin role required (benign; no secret here).
// flag_1 now lives on a per-user report object reached via a missing object-level
// owner check (see routes/reports.js), not on this route.
router.get('/config', requireAuth, requireRole('admin'), (req, res) => {
  res.json({
    config: {
      maintenance: false,
      version: '2.1.0',
      log_level: 'info',
    },
  });
});

router.get('/users', requireAuth, requireRole('admin'), (req, res) => {
  const users = db.prepare('SELECT id, username, role FROM users').all();
  res.json({ users });
});

module.exports = router;
