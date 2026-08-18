from django.urls import path

from . import views

urlpatterns = [
    path("community/boards/<str:board_type>/posts", views.post_list, name="post-list"),
    path("community/posts/mine", views.my_posts, name="my-posts"),
    path("community/comments/mine", views.my_comments, name="my-comments"),
    path("community/posts/<int:post_id>", views.post_detail, name="post-detail"),
    path("community/posts/<int:post_id>/comments", views.comment_list, name="comment-list"),
    path("community/comments/<int:comment_id>", views.comment_detail, name="comment-detail"),
    path("community/posts/<int:post_id>/report", views.post_report, name="post-report"),
    path("community/comments/<int:comment_id>/report", views.comment_report, name="comment-report"),
    path("community/posts/<int:post_id>/scrap", views.post_scrap, name="post-scrap"),
    path("community/scraps", views.scrap_list, name="scrap-list"),
    path("community/posts/<int:post_id>/like", views.post_like, name="post-like"),
    path("community/comments/<int:comment_id>/like", views.comment_like, name="comment-like"),
    path("community/posts/<int:post_id>/pin", views.post_pin,name="post-pin"),
    path("community/posts", views.latest_post_list, name="latest-post-list"),
]