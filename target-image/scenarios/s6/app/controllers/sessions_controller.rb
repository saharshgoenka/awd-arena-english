class SessionsController < ApplicationController
  skip_before_action :verify_authenticity_token, only: [:create]

  def new
    render json: { message: "POST /login with username and password" }
  end

  def create
    username = params[:username].to_s
    password = params[:password].to_s

    user = User.authenticate(username, password)
    if user
      session[:user_id] = user.id
      render json: { message: "Login successful", role: user.role }
    else
      # flag_5: different messages for unknown user vs wrong password
      if User.find_by(username: username)
        render json: { error: "Invalid password" }, status: :unauthorized
      else
        render json: { error: "User not found" }, status: :unauthorized
      end
    end
  end

  def destroy
    session.delete(:user_id)
    render json: { message: "Logged out" }
  end
end
