from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from core_apps.accounts.models import BankAccount
from core_apps.common.models import TimeStampedModel
from core_apps.cards.utils import generate_cvv

User = get_user_model()


class VirtualCard(TimeStampedModel):
    class CardStatus(models.TextChoices):
        ACTIVE = ("active", _("Active"))
        INACTIVE = ("inactive", _("Inactive"))
        BLOCKED = ("blocked", _("Blocked"))

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="virtual_cards"
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="virtual_cards"
    )
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.DateTimeField()
    # CVV is never stored — computed on demand from card_number + expiry_date + secret key
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=10, choices=CardStatus.choices, default=CardStatus.ACTIVE
    )

    @property
    def cvv(self) -> str:
        return generate_cvv(self.card_number, self.expiry_date.strftime("%m%y"))

    def __str__(self):
        return f"Virtual Card {self.card_number} for {self.user.full_name}"
