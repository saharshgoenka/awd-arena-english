-- Users: MD5 hashes (flag_3 vulnerability)
-- MD5("finmanager2024") = df7e676eec2fc4242b394e6ad2b960e6
-- MD5("ledgerTemp42")   = c7a503b5a6f57caabd4cf7eb846f99dc
-- MD5("finance789")     = db38907195096e06de36c583d2534482
INSERT OR IGNORE INTO users (id, username, password_hash, role) VALUES
  (1, 'admin',   'df7e676eec2fc4242b394e6ad2b960e6', 'ADMIN'),
  (2, 'analyst', 'c7a503b5a6f57caabd4cf7eb846f99dc', 'USER'),
  (3, 'finance', 'db38907195096e06de36c583d2534482', 'USER');

-- Ledger entries
INSERT OR IGNORE INTO ledger_entries (id, description, amount, category) VALUES
  (1,  'Q1 office supplies reconciliation packet for finance analyst review and export testing', 1250.00, 'OPERATING'),
  (2,  'Q1 Cloud Infrastructure',       8400.50,   'TECHNOLOGY'),
  (3,  'Q1 Travel and Lodging',         3200.75,   'TRAVEL'),
  (4,  'Q1 Software Licenses',          4950.00,   'TECHNOLOGY'),
  (5,  'Q2 Contractor Payments',       22000.00,   'PERSONNEL'),
  (6,  'Q2 Marketing Campaign',         6800.00,   'MARKETING'),
  (7,  'Q2 Legal Fees',                 5500.00,   'LEGAL'),
  (8,  'Q3 Hardware Procurement',      14300.00,   'TECHNOLOGY'),
  (9,  'Q3 Training and Development',   2100.00,   'PERSONNEL'),
  (10, 'Q4 Audit Services',             7200.00,   'LEGAL');

CREATE TABLE IF NOT EXISTS access_reports (
  id INTEGER PRIMARY KEY,
  owner TEXT,
  title TEXT,
  body TEXT,
  escalation_ref INTEGER
);

INSERT OR IGNORE INTO access_reports (id, owner, title, body, escalation_ref) VALUES
  (21004, 'admin', 'Operations runbook index', 'Links to payment operations runbooks and deploy checklists.', NULL),
  (21005, 'analyst', 'Monthly close notes', 'Analyst close notes and reconciliation reminders for the current cycle.', NULL),
  (21006, 'finance', 'Q3 access review', 'Finance review references escalation_ref 91772 for privileged approval follow-up.', 91772),
  (91772, 'admin', 'Privileged finance approval', 'Q3 privileged approval packet. Restricted finance token: __FLAG_1__', NULL);
