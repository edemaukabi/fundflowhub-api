from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import VirtualCard
from .utils import generate_card_number


class UUIDField(serializers.Field):
    def to_representation(self, value) -> str:
        return str(value)


class VirtualCardSerializer(serializers.ModelSerializer):
    id = UUIDField(read_only=True)
    balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.1")
    )

    class Meta:
        model = VirtualCard
        # CVV is intentionally excluded — use the reveal-cvv endpoint
        fields = ["id", "card_number", "expiry_date", "balance", "status"]
        read_only_fields = ["id", "card_number", "expiry_date"]


class VirtualCardRevealCVVSerializer(serializers.ModelSerializer):
    """Returned only by the explicit reveal-cvv endpoint."""
    cvv = serializers.SerializerMethodField()

    class Meta:
        model = VirtualCard
        fields = ["id", "cvv"]

    def get_cvv(self, obj) -> str:
        return obj.cvv  # computed property — never stored


class VirtualCardCreateSerializer(serializers.ModelSerializer):
    bank_account_number = serializers.CharField(write_only=True)

    class Meta:
        model = VirtualCard
        fields = ["bank_account_number"]

    def validate(self, attrs):
        user = self.context["request"].user
        if user.virtual_cards.count() >= 3:
            raise serializers.ValidationError(
                "You can only have up to 3 virtual cards at a time"
            )
        return attrs

    def create(self, validated_data) -> VirtualCard:
        user = validated_data.get("user")
        bank_account_number = validated_data.pop("bank_account_number")
        bank_account = user.bank_accounts.get(account_number=bank_account_number)
        card_number = generate_card_number()
        expiry_date = timezone.now() + timezone.timedelta(days=365 * 3)

        return VirtualCard.objects.create(
            user=user,
            bank_account=bank_account,
            card_number=card_number,
            expiry_date=expiry_date,
            # cvv is not stored
        )
