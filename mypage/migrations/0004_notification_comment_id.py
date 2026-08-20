from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mypage", "0003_notification_target_id_notification_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="comment_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]
