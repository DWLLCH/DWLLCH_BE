from django.urls import path

from . import views

urlpatterns = [
    path("mypage/status", views.mypage_status, name="mypage-status"),
    path("mypage/profile", views.mypage_profile, name="mypage-profile"),
    path("mypage/applications", views.application_list, name="application-list"),
    path("mypage/applications/<int:application_id>", views.application_delete, name="application-delete"),
    path("mypage/applications/<int:application_id>/status", views.application_status_update, name="application-status-update"),
    path("mypage/applications/<int:application_id>/checklist", views.checklist_list, name="checklist-list"),
    path("mypage/applications/<int:application_id>/checklist/<int:item_id>", views.checklist_item_update, name="checklist-item-update"),
    path("mypage/notifications", views.notification_list, name="notification-list"),
    path("mypage/notifications/<int:notification_id>/read", views.notification_read, name="notification-read"),
    path("mypage/notifications/read-all", views.notification_read_all, name="notification-read-all"),
]