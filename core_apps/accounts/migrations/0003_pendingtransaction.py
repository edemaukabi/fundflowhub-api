import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_bankaccount_interest_rate_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PendingTransaction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "token",
                    models.UUIDField(db_index=True, default=uuid.uuid4, unique=True),
                ),
                (
                    "flow_type",
                    models.CharField(
                        choices=[
                            ("withdrawal", "Withdrawal"),
                            ("transfer", "Transfer"),
                        ],
                        max_length=20,
                    ),
                ),
                ("payload", models.JSONField()),
                ("expires_at", models.DateTimeField()),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pending_transactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Pending Transaction",
                "verbose_name_plural": "Pending Transactions",
                "abstract": False,
            },
        ),
    ]
