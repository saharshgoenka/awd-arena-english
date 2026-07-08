class AdminController < ApplicationController
  before_action :require_login
  # flag_1: before_action :require_admin intentionally omitted
  # any logged-in user reaches settings

  def settings
    # env, not the injectable flags table (only flag_4 lives in the DB)
    flag = ENV.fetch("FLAG_1", "FLAG{missing}")
    render json: { config: { maintenance: false, system_token: flag } }
  end

  def analytics
    unless current_user.role == "admin"
      render json: { error: "Admin access required" }, status: :forbidden
      return
    end
    # env, not the injectable flags table (only flag_4 lives in the DB)
    flag = ENV.fetch("FLAG_5", "FLAG{missing}")
    render json: {
      total_posts: Post.count,
      total_users: User.count,
      internal_ref: flag
    }
  end
end
