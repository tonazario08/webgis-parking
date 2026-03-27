from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("parking", "0003_remove_parkinglot_parking_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="area",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="area",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="parkinglot",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="parkinglot",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="parkinguser",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="parkinguser",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
