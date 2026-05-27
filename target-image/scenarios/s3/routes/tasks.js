'use strict';
const express = require('express');
const router = express.Router();
const db = require('../db');
const { requireAuth } = require('../middleware/auth');

// flag_4: SQL injection via template literal in search query
// Must be registered before /:id to avoid being swallowed by the param route
router.get('/search', requireAuth, (req, res) => {
  const q = req.query.q || '';
  const results = db
    .prepare(
      `SELECT id, title, description FROM tasks WHERE title LIKE '%${q}%'`
    )
    .all();
  res.json({ results });
});

// GET /api/tasks — list all tasks
router.get('/', requireAuth, (req, res) => {
  const tasks = db.prepare('SELECT * FROM tasks').all();
  res.json({ tasks });
});

// GET /api/tasks/:id — get single task
router.get('/:id', requireAuth, (req, res) => {
  const task = db.prepare('SELECT * FROM tasks WHERE id = ?').get(req.params.id);
  if (!task) return res.status(404).json({ error: 'Task not found' });
  res.json({ task });
});

// POST /api/tasks — create task (admin/manager only)
router.post('/', requireAuth, (req, res) => {
  if (req.user.role === 'user') {
    return res.status(403).json({ error: 'Insufficient permissions' });
  }
  const { title, description, assigned_to, project_id } = req.body;
  if (!title) return res.status(400).json({ error: 'Title required' });
  const stmt = db.prepare(
    'INSERT INTO tasks (title, description, assigned_to, project_id) VALUES (?, ?, ?, ?)'
  );
  const info = stmt.run(title, description || '', assigned_to || '', project_id || 1);
  res.status(201).json({ id: info.lastInsertRowid, title });
});

module.exports = router;
