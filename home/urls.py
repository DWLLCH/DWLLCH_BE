from django.urls import path

from . import views

urlpatterns = [
    path("policies", views.policy_list, name="policy-list"),
    path("policies/<int:policy_id>", views.policy_detail, name="policy-detail"),
]