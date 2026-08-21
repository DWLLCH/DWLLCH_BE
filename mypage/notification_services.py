from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Application, Notification

User = get_user_model()

DEADLINE_OFFSETS = (7, 1)
PROTECTION_END_OFFSETS = (30, 7, 1, 0)


def create_scheduled_notifications(today=None):
    today = today or timezone.localdate()
    created_counts = {
        "deadline": 0,
        "protection_end": 0,
    }

    active_applications = Application.objects.filter(
        status__in=[
            Application.Status.PLANNED,
            Application.Status.IN_PROGRESS,
        ],
    ).select_related("policy", "user")

    for days_left in DEADLINE_OFFSETS:
        deadline = today + timedelta(days=days_left)
        applications = active_applications.filter(
            policy__application_end=deadline,
        )

        for application in applications:
            _, created = Notification.objects.get_or_create(
                event_key=(
                    f"deadline:{application.id}:"
                    f"{deadline.isoformat()}:{days_left}"
                ),
                defaults={
                    "user": application.user,
                    "message": (
                        f"{application.policy.title} 신청 마감이 "
                        f"{days_left}일 남았습니다."
                    ),
                    "type": Notification.Type.DEADLINE,
                    "target_id": application.policy_id,
                },
            )
            created_counts["deadline"] += int(created)

    scheduled_users = User.objects.filter(
        protection_status=User.ProtectionStatus.SCHEDULED,
    )

    for days_left in PROTECTION_END_OFFSETS:
        protection_end_date = today + timedelta(days=days_left)
        users = scheduled_users.filter(
            protection_end_date=protection_end_date,
        )

        for user in users:
            message = (
                "오늘은 보호 종료 예정일입니다."
                if days_left == 0
                else f"보호 종료 예정일까지 {days_left}일 남았습니다."
            )
            _, created = Notification.objects.get_or_create(
                event_key=(
                    f"protection_end:{user.id}:"
                    f"{protection_end_date.isoformat()}:{days_left}"
                ),
                defaults={
                    "user": user,
                    "message": message,
                    "type": Notification.Type.PROTECTION_END,
                },
            )
            created_counts["protection_end"] += int(created)

    return created_counts
