class ProfileController < ApplicationController
  before_action :require_login

  def token
    # flag_3: exposes the stored MD5 hash as "legacy_token"
    render json: {
      username: current_user.username,
      legacy_token: current_user.password_digest
    }
  end

  def vault
    unless current_user.username == "author"
      render json: { error: "Author access only" }, status: :forbidden
      return
    end
    flag = Flag.find_by(name: "flag_3")&.value
    render json: { message: "Author vault", secret: flag }
  end
end
