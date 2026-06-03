require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.cache_classes = true
  config.eager_load = true
  # flag_2: intentionally wrong for production — exposes debug info
  config.consider_all_requests_local = true
  config.action_controller.perform_caching = true
  config.public_file_server.enabled = true
  config.log_level = :info
  config.log_tags = [:request_id]
  config.force_ssl = false

  config.cache_store = :memory_store
  config.active_support.report_deprecations = false
end
