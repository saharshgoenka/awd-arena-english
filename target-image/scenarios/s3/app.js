'use strict';
const express = require('express');
const cookieParser = require('cookie-parser');
const fs = require('fs');
const path = require('path');

// Initialize database (creates tables and seeds data)
require('./db');

const app = express();
const PORT = 3000;

// Write .env file so the misconfigured static middleware exposes FLAG_2 via GET /.env
const flag2Val = process.env.FLAG_2 || 'FLAG{00000000000000000000000000000000}';
fs.writeFileSync(path.join(__dirname, '.env'), `FLAG_2=${flag2Val}\n`);

app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());

// flag_2: static misconfiguration — serves entire /app/ directory instead of /app/public/
// This exposes .env, app.js, db.js, etc. via HTTP.  Patch changes __dirname to path.join(__dirname, 'public')
app.use(express.static(__dirname));

// Routes
app.use('/auth', require('./routes/auth'));
app.use('/api/admin', require('./routes/admin'));
// flag_2: debug routes mounted — remove this line in patch
app.use('/api/debug', require('./routes/debug'));
app.use('/api/tasks', require('./routes/tasks'));
app.use('/api/users', require('./routes/users'));
app.use('/api/projects', require('./routes/projects'));

// Simple dashboard page
app.get('/dashboard', (req, res) => {
  res.send(`<!DOCTYPE html>
<html>
<head><title>TaskFlow</title></head>
<body>
<h1>TaskFlow Dashboard</h1>
<p>Project and task management portal.</p>
<nav>
  <a href="/api/tasks">Tasks</a> |
  <a href="/api/projects">Projects</a> |
  <a href="/api/users/me">Profile</a>
</nav>
</body>
</html>`);
});

// Health check — no auth, no DB dependency
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`TaskFlow listening on :${PORT}`);
});
