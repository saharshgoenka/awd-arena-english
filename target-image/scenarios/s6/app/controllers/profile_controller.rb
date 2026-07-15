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
    # flag_3 no longer lives here. The secret is only recoverable via the reused
    # export keystream (A02 many-time pad) at /exports/encrypted?item=vault.
    render json: { message: "Author vault", notes: "No stored secrets. See export tooling." }
  end
end
