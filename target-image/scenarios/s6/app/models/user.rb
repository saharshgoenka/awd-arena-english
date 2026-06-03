require "digest"

class User < ApplicationRecord
  # flag_3: password_digest column name implies has_secure_password (bcrypt),
  # but actually stores raw MD5 — NOT bcrypt
  def self.authenticate(username, password)
    user = find_by(username: username)
    return nil unless user
    user if user.password_digest == Digest::MD5.hexdigest(password)
  end
end
