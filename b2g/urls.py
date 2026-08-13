from django.urls import path

from b2g import views

app_name = "b2g"

urlpatterns = [
    path(
        "b2g/dashboard/requests",
        views.ConsultRequestListView.as_view(),
        name="request-list",
    ),
    path(
        "b2g/dashboard/requests/<int:request_id>",
        views.ConsultRequestDetailView.as_view(),
        name="request-detail",
    ),
    path(
        "b2g/dashboard/stats",
        views.DashboardStatsView.as_view(),
        name="dashboard-stats",
    ),
]