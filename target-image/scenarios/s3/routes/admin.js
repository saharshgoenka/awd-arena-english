'use strict';
const express = require('express');
const router = express.Router();
const db = require('../db');
const { requireAuth, requireRole } = require('../middleware/auth');

// flag_1: no auth middleware on /config — any unauthenticated request can read it
router.get('/config', (req, res) => {
  const flag = db.prepare("SELECT value FROM flags WHERE name = 'flag_1'").get();
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
