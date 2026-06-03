Rails.application.routes.draw do
  get  "/health",           to: "health#index"
  get  "/login",            to: "sessions#new"
  post "/login",            to: "sessions#create"
  delete "/logout",         to: "sessions#destroy"

  get "/dashboard",         to: "dashboard#index"

  get "/admin/settings",    to: "admin#settings"
  get "/admin/analytics",   to: "admin#analytics"

  get "/debug/runtime",     to: "debug#runtime"

  get "/profile/token",     to: "profile#token"
  get "/profile/vault",     to: "profile#vault"

  get "/posts",             to: "posts#index"
  get "/posts/search",      to: "posts#search"
  get "/posts/:id",         to: "posts#show"
end
