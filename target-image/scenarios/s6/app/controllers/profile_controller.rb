class ProfileController < ApplicationController
  before_action :require_login

  def token
    lookup = params[:username].presence || current_user.username
    user = User.find_by(username: lookup)
    return render json: { error: "User not found" }, status: :not_found unless user

    # flag_3: authenticated users can read another user's legacy hash.
    render json: {
      username: user.username,
      legacy_token: user.password_digest
    }
  end

  def vault
    unless current_user.username == "author"
      render json: { error: "Author access only" }, status: :forbidden
      return
    end
    # env, not the injectable flags table (only flag_4 lives in the DB)
    flag = ENV.fetch("FLAG_3", "FLAG{missing}")
    render json: { message: "Author vault", secret: flag }
  end
end
