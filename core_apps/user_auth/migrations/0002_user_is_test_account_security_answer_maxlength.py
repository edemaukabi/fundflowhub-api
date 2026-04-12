from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user_auth", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_test_account",
            field=models.BooleanField(
                default=False,
                help_text="When True, this user belongs to the demo/test environment.",
                verbose_name="Test Account",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="security_answer",
            field=models.CharField(max_length=128, verbose_name="Security Answer"),
        ),
    ]
