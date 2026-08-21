from datetime import date

from django.core.management.base import BaseCommand, CommandError

from mypage.notification_services import create_scheduled_notifications


class Command(BaseCommand):
    help = "신청 마감 및 보호종료 예정 알림을 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            dest="run_date",
            help="알림 생성 기준일(YYYY-MM-DD). 기본값은 오늘입니다.",
        )

    def handle(self, *args, **options):
        run_date = None

        if options["run_date"]:
            try:
                run_date = date.fromisoformat(options["run_date"])
            except ValueError as error:
                raise CommandError(
                    "--date는 YYYY-MM-DD 형식이어야 합니다."
                ) from error

        created_counts = create_scheduled_notifications(today=run_date)
        self.stdout.write(
            self.style.SUCCESS(
                "알림 생성 완료: "
                f"신청 마감 {created_counts['deadline']}건, "
                f"보호종료 {created_counts['protection_end']}건"
            )
        )
