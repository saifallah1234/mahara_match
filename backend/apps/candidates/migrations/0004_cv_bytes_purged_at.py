from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("candidates", "0003_cv_deleted_at")]

    operations = [
        migrations.AddField(
            model_name="cv",
            name="bytes_purged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
