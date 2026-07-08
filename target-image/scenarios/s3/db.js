'use strict';
const Database = require('better-sqlite3');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function md5(text) {
  return crypto.createHash('md5').update(text).digest('hex');
}

const DATA_DIR = '/app/data';
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const db = new Database(path.join(DATA_DIR, 'taskflow.db'));

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    role TEXT
  );
  CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    title TEXT,
    description TEXT,
    assigned_to TEXT,
    project_id INTEGER
  );
  CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    value TEXT
  );
`);

// Seed users
const insertUser = db.prepare(
  'INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)'
);
insertUser.run('admin', md5('TaskFlow2025!'), 'admin');
insertUser.run('devuser', md5('shipit7'), 'user');
insertUser.run('manager', md5('manager456'), 'manager');

// Seed tasks
const insertTask = db.prepare(
  'INSERT OR IGNORE INTO tasks (id, title, description, assigned_to, project_id) VALUES (?, ?, ?, ?, ?)'
);
const tasks = [
  [1, 'Setup CI/CD pipeline', 'Configure Jenkins for automated deployments', 'devuser', 1],
  [2, 'Write unit tests for auth module', 'Cover login and JWT validation paths', 'devuser', 1],
  [3, 'Database migration script', 'Add index on users.username for faster lookups', 'manager', 2],
  [4, 'API documentation', 'Document all REST endpoints using OpenAPI spec', 'devuser', 2],
  [5, 'Security audit', 'Review authentication and authorization logic', 'admin', 3],
  [6, 'Frontend dashboard build', 'Build React dashboard for task overview', 'manager', 1],
  [7, 'Load testing', 'Run k6 load tests against staging environment', 'devuser', 3],
];
for (const t of tasks) {
  insertTask.run(...t);
}

// Seed flags from environment variables
const insertFlag = db.prepare(
  'INSERT OR REPLACE INTO flags (name, value) VALUES (?, ?)'
);
const placeholder = 'FLAG{00000000000000000000000000000000}';
// Only flag_4 is stored in the DB — it is the flag reachable via the
// /api/tasks SQLi UNION. The other flags are served from env by their own
// routes so one injection can no longer dump every flag at once.
insertFlag.run('flag_4', process.env.FLAG_4 || placeholder);

module.exports = db;
