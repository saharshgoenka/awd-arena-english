class DebugController < ApplicationController
  # flag_2: no before_action — open to all, no auth required
  skip_before_action :verify_authenticity_token

  def runtime
    render json: {
      ruby_version: RUBY_VERSION,
      rails_env: Rails.env,
      # A02 BOUNDED leak: only FLAG_2, not the whole flag set (dumping every
      # FLAG_* handed an attacker all 5 flags in one request).
      environment: ENV.to_hash.reject { |k, _| k.start_with?("FLAG_") && k != "FLAG_2" }
    }
  end
end
