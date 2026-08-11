from django.urls import path

from chat import views

app_name = "chat"

urlpatterns = [
    path("risk-check/sessions", views.RiskCheckSessionCreateView.as_view(), name="session-create"),
    path("risk-check/sessions/<int:session_id>", views.RiskCheckSessionDetailView.as_view(), name="session-detail"),
    path("risk-check/sessions/<int:session_id>/messages", views.RiskCheckMessageCreateView.as_view(), name="message-create"),
]