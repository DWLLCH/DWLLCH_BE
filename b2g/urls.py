from django.urls import path

from b2g import views

app_name = "b2g"

urlpatterns = [
    path("dashboard/requests", views.ConsultRequestListView.as_view(),name="request-list",),
    path("dashboard/requests/<int:request_id>", views.ConsultRequestDetailView.as_view(), name="request-detail",),
    path("dashboard/stats", views.DashboardStatsView.as_view(), name="dashboard-stats",),
]