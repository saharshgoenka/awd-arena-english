class ApplicationController < ActionController::Base
  protect_from_forgery with: :exception

  helper_method :current_user, :logged_in?

  private

  def current_user
    @current_user ||= User.find_by(id: session[:user_id]) if session[:user_id]
  end

  def logged_in?
    current_user.present?
  end

  def require_login
    unless logged_in?
      render json: { error: "Login required" }, status: :unauthorized
    end
  end

  def require_admin
    unless logged_in? && current_user.role == "admin"
      render json: { error: "Admin access required" }, status: :forbidden
    end
  end
end
