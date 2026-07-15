'use strict';
const express = require('express');
const router = express.Router();
const db = require('../db');
const { requireAuth } = require('../middleware/auth');

// flag_1 (A01 Broken Access Control → IDOR/BOLA)
//
// Reports are per-user objects addressed by id. `/mine` returns the caller's own
// report, which references a related (escalation) report id owned by another user.
// `/:id` authenticates the caller but omits the per-object owner check, so any
// authenticated user can read any report by id. The flag lives on exactly one
// report (the admin escalation record) whose id is NOT advertised — it must be
// derived from the reference in the caller's own report. Unknown ids fail closed
// (404), so blind enumeration of the large id space does not yield the flag.

function serialize(row) {
  // The escalation report stores a placeholder; the real flag is injected from the
  // env at serve time so it is never persisted in SQLite (keeps it out of reach of
  // the flag_4 UNION SQLi, which can only dump table contents).
  const body = row.body.replace('__FLAG_1__', process.env.FLAG_1 || 'FLAG{missing}');
  return {
    id: row.id,
    owner: row.owner,
    title: row.title,
    body,
    escalation_ref: row.escalation_ref,
  };
}

// GET /api/reports/mine — the caller's own report (references a related report id)
router.get('/mine', requireAuth, (req, res) => {
  const row = db
    .prepare('SELECT * FROM reports WHERE owner = ? ORDER BY id LIMIT 1')
    .get(req.user.username);
  if (!row) return res.status(404).json({ error: 'No report for this account' });
  res.json({ report: serialize(row) });
});

// GET /api/reports/:id — BOLA: auth is enforced, per-object ownership is NOT checked
router.get('/:id', requireAuth, (req, res) => {
  const row = db.prepare('SELECT * FROM reports WHERE id = ?').get(req.params.id);
  if (!row) return res.status(404).json({ error: 'Report not found' });
  // MISSING per-object authorization: should verify row.owner === req.user.username
  // (or an explicit share). Because it does not, any authenticated caller can read
  // another user's report — including the admin escalation record.
  res.json({ report: serialize(row) });
});

module.exports = router;
