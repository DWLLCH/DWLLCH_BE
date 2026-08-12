from django.urls import path

from chat import views

app_name = "chat"

urlpatterns = [
    path(
        "chat/risk-check/sessions",
        views.RiskCheckSessionCreateView.as_view(),
        name="session-create",
    ),
    path(
        "chat/risk-check/sessions/<int:session_id>",
        views.RiskCheckSessionDetailView.as_view(),
        name="session-detail",
    ),
    path(
        "chat/risk-check/sessions/<int:session_id>/messages",
        views.RiskCheckMessageView.as_view(),
        name="message-list-create",
    ),
    path(
        "chat/risk-check/messages/<int:message_id>/report",
        views.RiskCheckMessageReportView.as_view(),
        name="message-report",
    ),
    path(
        "chat/risk-check/messages/<int:message_id>/file",
        views.RiskCheckMessageFileView.as_view(),
        name="message-file",
    ),
    path(
        "chat/sos/sessions/<int:session_id>/structure",
        views.RiskCheckStructureView.as_view(),
        name="session-structure",
    ),
    path(
        "chat/sos/sessions/<int:session_id>/connect",
        views.RiskCheckConnectView.as_view(),
        name="session-connect",
    ),
]
