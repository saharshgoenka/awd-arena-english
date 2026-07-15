class AdminController < ApplicationController
  skip_before_action :verify_authenticity_token

  # flag_5 (A07 Authentication Failures → token/signature forgery).
  #
  # Authorization here is driven entirely by the JWT-style bearer token (NOT the
  # Rails session). The token verifier honours an `alg: none` header, so a low-priv
  # token can be re-forged with role=admin and no signature. Access is granted on
  # role == "admin" from the (unverified) token claims; a genuine low-priv token
  # gets 403.
  def analytics
    claims = TokenLite.verify(bearer_token)
    unless claims && claims["role"] == "admin"
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

  private

  def bearer_token
    auth = request.headers["Authorization"].to_s
    auth.start_with?("Bearer ") ? auth.split(" ", 2).last : nil
  end
end
