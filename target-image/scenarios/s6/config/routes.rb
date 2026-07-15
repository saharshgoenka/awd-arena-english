Rails.application.routes.draw do
  get  "/",                 to: "discovery#home"
  get  "/status",           to: "discovery#status"
  get  "/help",             to: "discovery#help"
  get  "/about",            to: "discovery#about"
  get  "/api",              to: "discovery#api"
  get  "/robots.txt",       to: "discovery#robots"

  get  "/health",           to: "health#index"
  get  "/login",            to: "sessions#new"
  post "/login",            to: "sessions#create"
  delete "/logout",         to: "sessions#destroy"

  get "/dashboard",         to: "dashboard#index"

  get "/admin/analytics",   to: "admin#analytics"

  get "/debug/env",         to: "debug#runtime"

  get "/profile/token",     to: "profile#token"
  get "/profile/vault",     to: "profile#vault"

  get "/exports/encrypted", to: "exports#encrypted"

  get "/reports/mine",      to: "reports#mine"
  get "/reports/:id",       to: "reports#show"

  get "/posts",             to: "posts#index"
  get "/posts/search",      to: "posts#search"
  get "/posts/:id",         to: "posts#show"
end
