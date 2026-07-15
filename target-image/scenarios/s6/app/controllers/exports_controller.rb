require "digest"

class ExportsController < ApplicationController
  before_action :require_login

  # flag_3 (A02 Cryptographic Failures → reused-keystream / many-time pad).
  #
  # Every encrypted export is XORed with the SAME fixed keystream — there is no
  # per-message nonce/IV, so the keystream is reused across all items. This is a
  # many-time pad: recover the keystream from any known (plaintext, ciphertext)
  # pair and use it to decrypt the vault ciphertext. Both the target and an
  # attacker need only stdlib XOR — no crypto library, no cracking.
  #
  #   item=<report id> → XORs that report's plaintext content (the SAME content a
  #                      low-priv user can already read at /reports/:id), giving a
  #                      known (plaintext, ciphertext) pair.
  #   item=vault       → XORs FLAG_3, read from ENV at serve time (never persisted,
  #                      so the flag_4 UNION SQLi cannot dump it).
  KEYSTREAM = (Digest::SHA256.digest("contenthub-export-key-2024") * 8).bytes.freeze  # 256 bytes, fixed

  def encrypted
    item = params[:item].to_s
    if item == "vault"
      plaintext = ENV.fetch("FLAG_3", "FLAG{missing}")
    else
      report = Report.find_by(id: item)
      unless report
        render json: { error: "unknown item" }, status: :not_found
        return
      end
      # Same substitution as ReportsController#serialize so the export plaintext
      # matches exactly what the caller reads at /reports/:id.
      plaintext = report.body.to_s.sub("__FLAG_1__", ENV.fetch("FLAG_1", "FLAG{missing}"))
    end
    resp = { item: item, cipher_hex: xor_hex(plaintext) }
    # self-contained crib for the reused-keystream recovery
    resp[:plaintext] = plaintext unless item == "vault"
    render json: resp
  end

  private

  def xor_hex(plaintext)
    plaintext.bytes.each_with_index.map { |b, i| b ^ KEYSTREAM[i] }.pack("C*").unpack1("H*")
  end
end
