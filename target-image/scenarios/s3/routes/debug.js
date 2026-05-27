'use strict';
const express = require('express');
const router = express.Router();

// flag_2: unauthenticated env dump — FLAG_2 is in process.env
router.get('/env', (req, res) => {
  res.json(process.env);
});

router.get('/status', (req, res) => {
  res.json({
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    node: process.version,
  });
});

module.exports = router;
