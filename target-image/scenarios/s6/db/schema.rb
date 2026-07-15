ActiveRecord::Schema[7.1].define(version: 2024_01_01_000000) do
  create_table :users, force: :cascade do |t|
    t.string :username, null: false
    t.string :password_digest
    t.string :role
    t.timestamps
    t.index :username, unique: true
  end

  create_table :posts, force: :cascade do |t|
    t.string :title
    t.text :body
    t.string :status
    t.references :user, foreign_key: true
    t.timestamps
  end

  create_table :flags, force: :cascade do |t|
    t.string :name
    t.string :value
    t.timestamps
  end

  create_table :reports, force: :cascade do |t|
    t.string  :owner
    t.string  :title
    t.text    :body
    t.integer :escalation_ref
    t.timestamps
  end
end
