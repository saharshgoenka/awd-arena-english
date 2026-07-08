class PostsController < ApplicationController
  before_action :require_login

  def index
    posts = Post.includes(:user).order(created_at: :desc).limit(20)
    render json: { posts: posts.as_json(only: [:id, :title, :status], include: { user: { only: [:username] } }) }
  end

  def show
    post = Post.find_by(id: params[:id])
    if post
      render json: post.as_json(only: [:id, :title, :body, :status])
    else
      render json: { error: "Not found" }, status: :not_found
    end
  end

  def search
    q = params[:q].to_s
    # flag_4: SQL injection via string interpolation in ActiveRecord .where
    @posts = Post.where("title LIKE '%#{q}%'")
    render json: { results: @posts.as_json(only: [:id, :title, :body]) }
  end
end
