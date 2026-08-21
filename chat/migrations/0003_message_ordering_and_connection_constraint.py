from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0002_alter_riskcheckmessage_file"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="riskcheckmessage",
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="supportconnection",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(consent=True)
                    | models.Q(forced_connection=True)
                ),
                name="support_connection_requires_consent_or_force",
            ),
        ),
    ]
