from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parking", "0004_add_trash_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="parkinguser",
            name="email_verified",
            field=models.BooleanField(default=False, verbose_name="Email da xac thuc"),
        ),
        migrations.AddField(
            model_name="parkinguser",
            name="email_verification_token",
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name="Email token"),
        ),
        migrations.AddField(
            model_name="parkinguser",
            name="email_verification_sent_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Thoi gian gui xac thuc"),
        ),
    ]
