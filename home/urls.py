from django.urls import path

from . import views

urlpatterns = [
    path("policies", views.policy_list, name="policy-list"),
    path("policies/scraps", views.policy_scrap_list, name="policy-scrap-list"),
    path("policies/<int:policy_id>", views.policy_detail, name="policy-detail"),
    path("policies/<int:policy_id>/scrap", views.policy_scrap, name="policy-scrap"),
    path("policies/chatbot/query", views.policy_chatbot_query, name="policy-chatbot-query"),
    path("policies/<int:policy_id>/similar", views.policy_similar, name="policy-similar"),
    path("home/guest", views.home_guest, name="home-guest"),
    path("home/curation", views.home_curation, name="home-curation"),
]