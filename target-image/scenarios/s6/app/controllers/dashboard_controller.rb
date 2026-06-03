class DashboardController < ApplicationController
  before_action :require_login

  def index
    render json: {
      message: "Welcome, #{current_user.username}",
      role: current_user.role,
      recent_posts: Post.order(created_at: :desc).limit(5).as_json(only: [:id, :title, :status])
    }
  end
end
