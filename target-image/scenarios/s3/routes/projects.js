'use strict';
const express = require('express');
const router = express.Router();
const db = require('../db');
const { requireAuth } = require('../middleware/auth');

// GET /api/projects — list public projects
router.get('/', requireAuth, (req, res) => {
  res.json({
    projects: [
      { id: 1, name: 'TaskFlow Rewrite', status: 'active' },
      { id: 2, name: 'Security Overhaul', status: 'planning' },
      { id: 3, name: 'Mobile App', status: 'backlog' },
    ],
  });
});

// GET /api/projects/internal — flag_5: admin-only; exploitable via JWT alg:none
router.get('/internal', requireAuth, (req, res) => {
  if (req.user.role !== 'admin') {
    return res.status(403).json({ error: 'Forbidden' });
  }
  const flag = db.prepare("SELECT value FROM flags WHERE name = 'flag_5'").get();
  res.json({
    projects: [
      { id: 1, name: 'TaskFlow Rewrite', status: 'active', budget: 120000 },
      { id: 2, name: 'Security Overhaul', status: 'planning', budget: 45000 },
      { id: 3, name: 'Mobile App', status: 'backlog', budget: 80000 },
    ],
    internal_token: flag.value,
  });
});

module.exports = router;
