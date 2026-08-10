from django.urls import path

from . import views

urlpatterns = [
    path("policies", views.policy_list, name="policy-list"),
    path("policies/<int:policy_id>", views.policy_detail, name="policy-detail"),
    path("home/guest", views.home_guest, name="home-guest"),
    path("home/curation", views.home_curation, name="home-curation"),
    path("policies/chatbot/query", views.policy_chatbot_query, name="policy-chatbot-query"),
]