class ReportsController < ApplicationController
  before_action :require_login

  # flag_1 (A01 Broken Access Control → IDOR/BOLA).
  #
  # Reports are per-user objects addressed by id. `/reports/mine` returns the
  # caller's own report, which references a related (escalation) report id owned by
  # a higher-privilege user. `/reports/:id` authenticates the caller but omits the
  # per-object owner check, so any logged-in user can read any report by id. The
  # flag lives on exactly one report (the admin escalation record) whose id is NOT
  # advertised — it must be derived from the reference in the caller's own report.
  # Unknown ids fail closed (404), so blind enumeration does not yield the flag.

  # GET /reports/mine — the caller's own report (references a related report id)
  def mine
    report = Report.where(owner: current_user.username).order(:id).first
    unless report
      render json: { error: "No report for this account" }, status: :not_found
      return
    end
    render json: { report: serialize(report) }
  end

  # GET /reports/:id — BOLA: auth is enforced, per-object ownership is NOT checked
  def show
    report = Report.find_by(id: params[:id])
    unless report
      render json: { error: "Report not found" }, status: :not_found
      return
    end
    # MISSING per-object authorization: should verify report.owner == current_user.username
    # (or an explicit share). Because it does not, any logged-in caller can read
    # another user's report — including the admin escalation record.
    render json: { report: serialize(report) }
  end

  private

  def serialize(report)
    # The escalation report stores a placeholder; the real flag is substituted from
    # the env at serve time so it is never persisted in SQLite (keeps it out of reach
    # of the flag_4 UNION SQLi, which can only dump table contents).
    body = report.body.to_s.sub("__FLAG_1__", ENV.fetch("FLAG_1", "FLAG{missing}"))
    {
      id: report.id,
      owner: report.owner,
      title: report.title,
      body: body,
      escalation_ref: report.escalation_ref
    }
  end
end
