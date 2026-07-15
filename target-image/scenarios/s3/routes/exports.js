'use strict';
const express = require('express');
const router = express.Router();
const crypto = require('crypto');
const db = require('../db');
const { requireAuth } = require('../middleware/auth');

// flag_3 (A02 Cryptographic Failures → reused-keystream RECOVERY / many-time pad):
// every encrypted export is XORed with the SAME fixed keystream — there is no
// per-message nonce/IV, so the reuse IS the vulnerability. Recover the keystream
// from any known (plaintext, ciphertext) pair and decrypt the vault. Both the
// target and an attacker need only a stdlib XOR — no crypto library, no cracking.
const EXPORT_KEYSTREAM = Buffer.concat(
  Array(8).fill(crypto.createHash('sha256').update('taskflow-export-key-2024').digest())
); // 256 bytes, fixed

function xorExport(pt) {
  const out = Buffer.alloc(pt.length);
  for (let i = 0; i < pt.length; i++) {
    out[i] = pt[i] ^ EXPORT_KEYSTREAM[i];
  }
  return out.toString('hex');
}

// GET /exports/encrypted?item=<task id|vault>
// item=<task id> encrypts that task's description (also readable in plaintext via
// /api/tasks/:id); item=vault encrypts the flag_3 secret. Same keystream for every
// item -> recover it from the known pair and decrypt the vault.
router.get('/', requireAuth, (req, res) => {
  const item = req.query.item || '';
  let pt;
  if (item === 'vault') {
    // Read from env at serve time (never persisted, so the flag_4 SQLi UNION on
    // the `flags` table cannot dump it).
    pt = Buffer.from(process.env.FLAG_3 || 'FLAG{missing}', 'utf8');
  } else {
    const task = db.prepare('SELECT description FROM tasks WHERE id = ?').get(item);
    if (!task) return res.status(404).json({ error: 'unknown item' });
    pt = Buffer.from(task.description, 'utf8');
  }
  const resp = { item, cipher_hex: xorExport(pt) };
  // self-contained crib for the reused-keystream recovery
  if (item !== 'vault') resp.plaintext = pt.toString('utf8');
  res.json(resp);
});

module.exports = router;
