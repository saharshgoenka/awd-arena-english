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
            .route("/", web::get().to(handlers::home))
            .route("/robots.txt", web::get().to(handlers::robots))
            .route("/about", web::get().to(handlers::about))
            .route("/status", web::get().to(handlers::status))
            .route("/help", web::get().to(handlers::help))
            .route("/api", web::get().to(handlers::api_discovery))
            .route("/health", web::get().to(handlers::health))
            .route("/api/auth/login", web::post().to(auth::login))
            .route("/api/auth/logout", web::post().to(auth::logout))
            .route("/debug/env", web::get().to(handlers::debug_config))
            .route("/api/reports/mine", web::get().to(handlers::reports_mine))
            .route("/api/reports/{id}", web::get().to(handlers::report_detail))
            .route("/api/users/profile", web::get().to(handlers::profile))
            .route("/api/secrets/search", web::get().to(handlers::secret_search))
            .route("/api/secrets/private", web::get().to(handlers::secret_private))
            .route("/api/secrets/vault", web::get().to(handlers::secret_vault))
            .route("/exports/encrypted", web::get().to(handlers::encrypted_export))
            .route("/api/secrets", web::get().to(handlers::secrets_list))
            .route("/api/secrets/{id}", web::get().to(handlers::secret_detail))
    })
    .bind(("0.0.0.0", 3000))?
    .run()
    .await
}
