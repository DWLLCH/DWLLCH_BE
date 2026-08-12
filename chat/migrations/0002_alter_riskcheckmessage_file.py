import chat.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="riskcheckmessage",
            name="file",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to=chat.models.risk_check_upload_path,
            ),
        ),
    ]
