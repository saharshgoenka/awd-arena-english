class DebugController < ApplicationController
  # flag_2: no before_action — open to all, no auth required
  skip_before_action :verify_authenticity_token

  def runtime
    render json: {
      ruby_version: RUBY_VERSION,
      rails_env: Rails.env,
      environment: ENV.to_hash
    }
  end
end
