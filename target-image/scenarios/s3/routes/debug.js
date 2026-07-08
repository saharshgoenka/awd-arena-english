'use strict';
const express = require('express');
const router = express.Router();

// flag_2: bounded diagnostics leak
router.get('/diagnostics', (req, res) => {
  res.json({
    service: 'TaskFlow diagnostics preview',
    preview: {
      task_export_token: process.env.FLAG_2 || 'FLAG{missing}',
    },
    notes: [
      'Only the sanitized preview should be public.',
      'This endpoint still leaks one secret-bearing value.',
    ],
  });
});

router.get('/status', (req, res) => {
  res.json({
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    node: process.version,
  });
});

module.exports = router;
