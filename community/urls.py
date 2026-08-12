from django.urls import path

from . import views

urlpatterns = [
    path("community/posts", views.post_list, name="post-list"),
    path("community/posts/<int:post_id>", views.post_detail, name="post-detail"),
]
