class CreateTables < ActiveRecord::Migration[7.1]
  def change
    create_table :users do |t|
      t.string :username, null: false
      t.string :password_digest
      t.string :role
      t.timestamps
    end
    add_index :users, :username, unique: true

    create_table :posts do |t|
      t.string :title
      t.text :body
      t.string :status
      t.references :user, foreign_key: true
      t.timestamps
    end

    create_table :flags do |t|
      t.string :name
      t.string :value
      t.timestamps
    end
  end
end
