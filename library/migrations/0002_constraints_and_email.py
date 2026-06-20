from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0001_initial"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="borrowing",
            constraint=models.UniqueConstraint(
                "book_id",
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_borrowing_per_book",
            ),
        ),
        migrations.RunSQL(
            sql=[
                "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique "
                "ON auth_user (email) WHERE email != '';",
            ],
            reverse_sql=[
                "DROP INDEX IF EXISTS auth_user_email_unique;",
            ],
        ),
    ]