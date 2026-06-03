class AdminController < ApplicationController
  before_action :require_login
  # flag_1: before_action :require_admin intentionally omitted
  # any logged-in user reaches settings

  def settings
    flag = Flag.find_by(name: "flag_1")&.value
    render json: { config: { maintenance: false, system_token: flag } }
  end

  def analytics
    unless current_user.role == "admin"
      render json: { error: "Admin access required" }, status: :forbidden
      return
    end
    flag = Flag.find_by(name: "flag_5")&.value
    render json: {
      total_posts: Post.count,
      total_users: User.count,
      internal_ref: flag
    }
  end
end
