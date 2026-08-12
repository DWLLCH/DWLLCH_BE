from django.urls import path

from . import views

urlpatterns = [
    path("community/boards/<str:board_type>/posts", views.post_list, name="post-list"),
    path("community/posts/<int:post_id>", views.post_detail, name="post-detail"),
    path("community/posts/<int:post_id>/comments", views.comment_list, name="comment-list"),
    path("community/comments/<int:comment_id>", views.comment_detail, name="comment-detail"),
    path("community/posts/<int:post_id>/report", views.post_report, name="post-report"),
    path("community/comments/<int:comment_id>/report", views.comment_report, name="comment-report"),
]