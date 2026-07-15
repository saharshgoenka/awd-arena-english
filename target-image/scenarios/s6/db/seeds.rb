require "digest"

# Seed ONLY flag_4 (the SQLi-reachable flag). The others are served from env by
# their controllers so one UNION injection can't dump every flag at once.
%w[flag_4].each do |name|
  env_key = "FLAG_4"
  value = ENV.fetch(env_key, "FLAG{#{"0" * 32}}")
  Flag.find_or_initialize_by(name: name).tap do |f|
    f.value = value
    f.save!
  end
end

# Users: MD5 hashes (flag_3 vulnerability)
# MD5("cmsadmin2024") = 3a5b8e9f1c0d7a2e6b4f9c3d8a1e5b7f  (NOT the actual hash — computed below)
# MD5("editor456")    = ...
# MD5("storyDraft2024") = ...
[
  { username: "admin",  password: "cmsadmin2024", role: "admin"  },
  { username: "editor", password: "editor456",    role: "editor" },
  { username: "author", password: "storyDraft2024", role: "author" },
].each do |u|
  User.find_or_initialize_by(username: u[:username]).tap do |user|
    user.password_digest = Digest::MD5.hexdigest(u[:password])
    user.role = u[:role]
    user.save!
  end
end

# Sample posts
admin_user  = User.find_by(username: "admin")
editor_user = User.find_by(username: "editor")
author_user = User.find_by(username: "author")

posts = [
  { title: "Welcome to ContentHub",      body: "ContentHub is your new home for collaborative content.",          status: "published", user: admin_user  },
  { title: "Editorial Guidelines 2024",  body: "All submissions must follow AP style. Deadlines are firm.",       status: "published", user: editor_user },
  { title: "My First Draft",             body: "This post is still being refined. Stay tuned for the final cut.", status: "draft",     user: author_user },
  { title: "Q1 Content Calendar",        body: "Topics assigned for January through March are listed here.",      status: "published", user: editor_user },
  { title: "Site Relaunch Announcement", body: "We are thrilled to announce the ContentHub v2 relaunch.",         status: "published", user: admin_user  },
  { title: "Author Spotlight: Jane Doe", body: "Jane Doe has been writing for us since 2021. A true professional.", status: "published", user: editor_user },
  { title: "Behind the Scenes",          body: "A look at how our editorial team produces content at scale.",     status: "draft",     user: author_user },
  { title: "Trending Topics This Week",  body: "AI, climate policy, and space exploration top this week's list.", status: "published", user: editor_user },
]

posts.each do |p|
  Post.find_or_create_by(title: p[:title]) do |post|
    post.body   = p[:body]
    post.status = p[:status]
    post.user   = p[:user]
  end
end

# flag_1 (A01 IDOR/BOLA): per-user report objects.
# The editor's own report (readable via /reports/mine) references the admin
# escalation report #4021 by id. That escalation report carries the placeholder
# __FLAG_1__, substituted from ENV['FLAG_1'] at serve time (never persisted, so the
# flag_4 UNION SQLi cannot dump it). /reports/:id enforces auth but omits the
# per-object owner check, so the low-priv editor can read the admin's report.
reports = [
  { id: 3001, owner: "admin",  title: "Ops runbook index",
    body: "Links to on-call runbooks and deploy checklists.", escalation_ref: nil },
  { id: 3002, owner: "author", title: "Draft tracker",
    body: "Working notes for in-progress drafts. Nothing sensitive here.", escalation_ref: nil },
  { id: 3003, owner: "editor", title: "Q3 access review",
    body: "Reviewing privileged access grants for Q3. The approval record is tracked as escalation report #4021.",
    escalation_ref: 4021 },
  { id: 4021, owner: "admin",  title: "Access escalation grant",
    body: "Q3 privileged access escalation approved. Restricted operations token: __FLAG_1__",
    escalation_ref: nil },
]

reports.each do |r|
  Report.find_or_initialize_by(id: r[:id]).tap do |report|
    report.owner          = r[:owner]
    report.title          = r[:title]
    report.body           = r[:body]
    report.escalation_ref = r[:escalation_ref]
    report.save!
  end
end
