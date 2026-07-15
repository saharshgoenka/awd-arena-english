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
      # flag_5: issue a JWT-style bearer token the admin route trusts. The verifier
      # honours alg:none, so this low-priv token can be re-forged into an admin one.
      token = TokenLite.issue(
        "sub" => user.id,
        "username" => user.username,
        "role" => user.role
      )
      render json: { message: "Login successful", role: user.role, token: token }
    else
      render json: { error: "Invalid credentials" }, status: :unauthorized
    end
  end

  def destroy
    session.delete(:user_id)
    render json: { message: "Logged out" }
  end
end
