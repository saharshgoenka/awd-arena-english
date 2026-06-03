require_relative "boot"
require "rails/all"

Bundler.require(*Rails.groups)

module ContentHub
  class Application < Rails::Application
    config.load_defaults 7.1
    config.session_store :cookie_store, key: "_contenthub_session"
  end
end
