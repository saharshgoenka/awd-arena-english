#!/usr/bin/env python3
"""NexusBI — internal BI dashboard (intentionally vulnerable for AWD research)."""
import hashlib
import os
import sqlite3

from flask import Flask, redirect, render_template_string, request, session

app = Flask(__name__)
app.secret_key = "nexus-dev-secret-key-2024"

DB_PATH = "/app/data/nexus.db"

# ── HTML templates ────────────────────────────────────────────────────────────

LOGIN_HTML = """\
<!DOCTYPE html><html><head><title>NexusBI — Login</title></head>
<body style="font-family:sans-serif;max-width:400px;margin:60px auto">
<h2>NexusBI</h2>
<form method="post">
  <p><label>Username<br><input name="username" type="text" required></label></p>
  <p><label>Password<br><input name="password" type="password" required></label></p>
  <button type="submit">Log In</button>
</form>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
</body></html>"""

DASHBOARD_HTML = """\
<!DOCTYPE html><html><head><title>NexusBI — Dashboard</title></head>
<body style="font-family:sans-serif;max-width:800px;margin:40px auto">
<h2>NexusBI Dashboard — {{ username }}</h2>
<nav>
  <a href="/reports">Reports</a> |
  <a href="/profile">Profile</a> |
  <a href="/admin/panel">Admin Panel</a> |
  <a href="/logout">Logout</a>
</nav>
<h3>Recent Reports</h3><ul>
{% for r in reports %}
  <li><a href="/reports/{{ r['id'] }}">{{ r['title'] }}</a> ({{ r['owner'] }})</li>
{% endfor %}
</ul></body></html>"""

REPORTS_HTML = """\
<!DOCTYPE html><html><head><title>NexusBI — Reports</title></head>
<body style="font-family:sans-serif;max-width:800px;margin:40px auto">
<h2>Reports — {{ username }}</h2>
<form method="get" action="/api/data/search">
  <input name="q" placeholder="Search reports..." style="width:300px">
  <button type="submit">Search</button>
</form>
<table border="1" cellpadding="6" style="margin-top:16px;width:100%">
<tr><th>ID</th><th>Title</th><th>Owner</th><th>Content</th></tr>
{% for r in reports %}
<tr>
  <td>{{ r['id'] }}</td>
  <td><a href="/reports/{{ r['id'] }}">{{ r['title'] }}</a></td>
  <td>{{ r['owner'] }}</td>
  <td>{{ r['content'][:80] }}...</td>
</tr>
{% endfor %}
</table>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body></html>"""

REPORT_DETAIL_HTML = """\
<!DOCTYPE html><html><head><title>NexusBI — Report</title></head>
<body style="font-family:sans-serif;max-width:800px;margin:40px auto">
<h2>{{ report['title'] }}</h2>
<p><strong>Owner:</strong> {{ report['owner'] }}</p>
<p>{{ report['content'] }}</p>
<p><a href="/reports">Back to Reports</a></p>
</body></html>"""

PROFILE_HTML = """\
<!DOCTYPE html><html><head><title>NexusBI — Profile</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:40px auto">
<h2>Profile — {{ user['username'] }}</h2>
<p><strong>Role:</strong> {{ user['role'] }}</p>
<p><strong>Password hash:</strong> <code>{{ user['password_hash'] }}</code></p>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body></html>"""

ADMIN_PANEL_HTML = """\
<!DOCTYPE html><html><head><title>NexusBI — Admin Panel</title></head>
<body style="font-family:sans-serif;max-width:800px;margin:40px auto">
<h2>Admin Panel</h2>
<p>System token: {{ flag }}</p>
<p><strong>System Status:</strong> Operational</p>
<ul>
  <li>Active sessions: 3</li>
  <li>DB size: 48 KB</li>
  <li>Last backup: 2026-05-20</li>
</ul>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body></html>"""

ADMIN_REPORTS_HTML = """\
<!DOCTYPE html><html><head><title>NexusBI — Admin Reports</title></head>
<body style="font-family:sans-serif;max-width:800px;margin:40px auto">
<h2>Admin Reports — {{ username }}</h2>
<p>Restricted report token: <code>{{ flag }}</code></p>
<table border="1" cellpadding="6" style="width:100%">
<tr><th>ID</th><th>Title</th><th>Content</th></tr>
{% for r in reports %}
<tr><td>{{ r['id'] }}</td><td>{{ r['title'] }}</td><td>{{ r['content'] }}</td></tr>
{% endfor %}
</table>
<p><a href="/dashboard">Back to Dashboard</a></p>
</body></html>"""

# ── Database ──────────────────────────────────────────────────────────────────

def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_flag(name: str) -> str:
    conn = get_db()
    row = conn.execute("SELECT value FROM flags WHERE name=?", (name,)).fetchone()
    conn.close()
    return row["value"] if row else "FLAG{missing}"


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT,
            owner TEXT
        );
        CREATE TABLE IF NOT EXISTS flags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            value TEXT
        );
    """)
    c = conn.cursor()
    for username, pw, role in [
        ("admin",   "nexusadmin2024", "admin"),
        ("analyst", "password123",    "user"),
        ("viewer",  "viewer999",      "user"),
    ]:
        c.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, _md5(pw), role),
        )
    for row in [
        (1, "Q1 Revenue Summary",        "Total revenue for Q1 was $4.2M across all regions.",                         "admin"),
        (2, "Marketing Spend Analysis",  "Digital channels accounted for 63% of marketing budget.",                    "analyst"),
        (3, "Customer Churn Report",     "Monthly churn rate stabilized at 2.1% following retention campaign.",        "analyst"),
        (4, "Product Usage Dashboard",   "DAU/MAU ratio improved to 0.42 in March.",                                   "viewer"),
        (5, "Headcount Forecast",        "Engineering headcount projected to grow 15% in H2.",                         "admin"),
        (6, "Infrastructure Cost Review","Cloud spend up 22% YoY; optimization recommendations attached.",             "admin"),
        (7, "Sales Pipeline Update",     "Pipeline coverage at 3.1x for Q2 target.",                                  "analyst"),
        (8, "Compliance Audit Results",  "All 47 controls passed the annual SOC 2 audit.",                             "admin"),
    ]:
        c.execute(
            "INSERT OR IGNORE INTO reports (id, title, content, owner) VALUES (?, ?, ?, ?)",
            row,
        )
    for name, env_var in [
        ("flag_1", "FLAG_1"), ("flag_2", "FLAG_2"), ("flag_3", "FLAG_3"),
        ("flag_4", "FLAG_4"), ("flag_5", "FLAG_5"),
    ]:
        value = os.environ.get(env_var, f"FLAG{{00000000000000000000000000000000}}")
        c.execute("INSERT OR REPLACE INTO flags (name, value) VALUES (?, ?)", (name, value))
    conn.commit()
    conn.close()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/")
def index():
    return redirect("/login" if "username" not in session else "/dashboard")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, _md5(password)),
        ).fetchone()
        conn.close()
        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect("/dashboard")
        # VULNERABLE: different error messages enable username enumeration (flag_5 path)
        conn2 = get_db()
        exists = conn2.execute(
            "SELECT 1 FROM users WHERE username=?", (username,)
        ).fetchone()
        conn2.close()
        error = "Invalid password" if exists else "User not found"
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ── Main app pages ────────────────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect("/login")
    conn = get_db()
    reports = conn.execute("SELECT id, title, owner FROM reports ORDER BY id").fetchall()
    conn.close()
    return render_template_string(
        DASHBOARD_HTML, username=session["username"], reports=reports
    )


@app.route("/reports")
def reports_list():
    if "username" not in session:
        return redirect("/login")
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, content, owner FROM reports ORDER BY id"
    ).fetchall()
    conn.close()
    return render_template_string(REPORTS_HTML, reports=rows, username=session["username"])


@app.route("/reports/<int:report_id>")
def report_detail(report_id):
    if "username" not in session:
        return redirect("/login")
    conn = get_db()
    row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    if not row:
        return "Report not found", 404
    return render_template_string(
        REPORT_DETAIL_HTML, report=row, username=session["username"]
    )


# ── flag_1: A01 Broken Access Control ─────────────────────────────────────────
# No authentication check — any unauthenticated request reaches this handler.

@app.route("/admin/panel")
def admin_panel():
    flag = get_flag("flag_1")
    return render_template_string(ADMIN_PANEL_HTML, flag=flag)


# ── flag_2: A02 Security Misconfiguration ─────────────────────────────────────
# Debug endpoint dumps os.environ in production; FLAG_2 env var is exposed.

@app.route("/debug/config")
def debug_config():
    return {
        "flask_env": "production",
        "debug": False,
        "db_path": DB_PATH,
        "environment": dict(os.environ),
    }


# ── flag_3: A04 Cryptographic Failures ────────────────────────────────────────
# analyst password stored as raw MD5; hash displayed on /profile page.

@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect("/login")
    conn = get_db()
    user = conn.execute(
        "SELECT username, password_hash, role FROM users WHERE username=?",
        (session["username"],),
    ).fetchone()
    conn.close()
    return render_template_string(PROFILE_HTML, user=user, username=session["username"])


@app.route("/profile/secret")
def profile_secret():
    if session.get("username") != "analyst":
        return "Forbidden — analyst access only", 403
    flag = get_flag("flag_3")
    return render_template_string(
        "<!DOCTYPE html><html><body>"
        "<h2>Analyst Restricted Data</h2>"
        "<p>Credential report token: <code>{{ flag }}</code></p>"
        "</body></html>",
        flag=flag,
    )


# ── flag_4: A05 Injection ─────────────────────────────────────────────────────
# UNION-injectable search endpoint; flags table is in the same DB.

@app.route("/api/data/search")
def data_search():
    q = request.args.get("q", "")
    conn = get_db()
    query = f"SELECT id, title, content FROM reports WHERE title LIKE '%{q}%'"
    try:
        rows = conn.execute(query).fetchall()
        result = {"results": [dict(r) for r in rows]}
    except Exception as e:
        result = {"error": str(e)}
    finally:
        conn.close()
    return result


# ── flag_5: A07 Authentication Failures ───────────────────────────────────────
# /login has no rate limit; admin password is weak; error messages enumerate usernames.

@app.route("/admin/reports")
def admin_reports():
    if "username" not in session:
        return redirect("/login")
    if session.get("role") != "admin":
        return "Forbidden", 403
    flag = get_flag("flag_5")
    conn = get_db()
    rows = conn.execute(
        "SELECT id, title, content FROM reports WHERE owner='admin' ORDER BY id"
    ).fetchall()
    conn.close()
    return render_template_string(
        ADMIN_REPORTS_HTML, reports=rows, flag=flag, username=session["username"]
    )


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=3000, debug=False)
