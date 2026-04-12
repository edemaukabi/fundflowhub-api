from django.db import migrations


class Migration(migrations.Migration):
    """Remove stored CVV from VirtualCard.
    CVV is now computed on-demand via HMAC-SHA256 from card_number + expiry_date.
    It is never persisted to the database."""

    dependencies = [
        ("cards", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="virtualcard",
            name="cvv",
        ),
    ]
