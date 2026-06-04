mod auth;
mod db;
mod handlers;

use actix_web::{web, App, HttpServer};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let pool = db::init_db();
    let data = web::Data::new(pool);

    println!("VaultGate listening on 0.0.0.0:3000");
    HttpServer::new(move || {
        App::new()
            .app_data(data.clone())
            .route("/health", web::get().to(handlers::health))
            .route("/api/auth/login", web::post().to(auth::login))
            .route("/api/auth/logout", web::post().to(auth::logout))
            .route("/api/admin/keys", web::get().to(handlers::admin_keys))
            .route("/api/debug/config", web::get().to(handlers::debug_config))
            .route("/api/users/profile", web::get().to(handlers::profile))
            .route("/api/secrets/search", web::get().to(handlers::secret_search))
            .route("/api/secrets/private", web::get().to(handlers::secret_private))
            .route("/api/secrets/vault", web::get().to(handlers::secret_vault))
            .route("/api/secrets", web::get().to(handlers::secrets_list))
            .route("/api/secrets/{id}", web::get().to(handlers::secret_detail))
    })
    .bind(("0.0.0.0", 3000))?
    .run()
    .await
}
