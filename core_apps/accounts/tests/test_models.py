"""
Tests for BankAccount, Transaction, and PendingTransaction models.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from core_apps.accounts.models import BankAccount, Transaction, PendingTransaction


@pytest.mark.django_db
class TestBankAccountStr:
    def test_str_includes_account_number(self, customer, make_bank_account):
        account = make_bank_account(customer)
        assert account.account_number in str(account)

    def test_str_includes_account_type(self, customer, make_bank_account):
        account = make_bank_account(customer, account_type="savings")
        assert "Savings" in str(account)


@pytest.mark.django_db
class TestBankAccountValidation:
    def test_negative_balance_raises_validation_error(self, customer, make_bank_account):
        account = make_bank_account(customer, balance=Decimal("0.00"))
        account.account_balance = Decimal("-1.00")
        with pytest.raises(ValidationError):
            account.clean()

    def test_zero_balance_is_valid(self, customer, make_bank_account):
        account = make_bank_account(customer, balance=Decimal("0.00"))
        account.clean()  # should not raise


@pytest.mark.django_db
class TestBankAccountIsPrimary:
    def test_setting_primary_clears_other_primary_accounts(
        self, customer, make_bank_account
    ):
        acc1 = make_bank_account(
            customer, account_type="savings", currency="us_dollar"
        )
        acc2 = make_bank_account(
            customer, account_type="current", currency="us_dollar"
        )
        acc1.is_primary = True
        acc1.save()
        acc2.is_primary = True
        acc2.save()
        acc1.refresh_from_db()
        assert acc1.is_primary is False
        assert acc2.is_primary is True


@pytest.mark.django_db
class TestAnnualInterestRate:
    def test_savings_low_balance_returns_0_50_pct(self, customer, make_bank_account):
        account = make_bank_account(
            customer, account_type="savings", balance=Decimal("50000")
        )
        assert account.annual_interest_rate == Decimal("0.0050")

    def test_savings_mid_balance_returns_1_00_pct(self, customer, make_bank_account):
        account = make_bank_account(
            customer, account_type="savings", balance=Decimal("200000")
        )
        assert account.annual_interest_rate == Decimal("0.0100")

    def test_savings_high_balance_returns_1_50_pct(self, customer, make_bank_account):
        account = make_bank_account(
            customer, account_type="savings", balance=Decimal("600000")
        )
        assert account.annual_interest_rate == Decimal("0.0150")

    def test_current_account_always_zero(self, customer, make_bank_account):
        account = make_bank_account(
            customer, account_type="current", balance=Decimal("999999")
        )
        assert account.annual_interest_rate == Decimal("0.0000")


@pytest.mark.django_db
class TestApplyDailyInterest:
    def test_savings_balance_increases_after_interest(self, customer, make_bank_account):
        account = make_bank_account(
            customer, account_type="savings", balance=Decimal("10000.00")
        )
        original = account.account_balance
        interest = account.apply_daily_interest()
        assert interest > Decimal("0")
        account.refresh_from_db()
        assert account.account_balance > original

    def test_current_account_no_interest(self, customer, make_bank_account):
        account = make_bank_account(
            customer, account_type="current", balance=Decimal("10000.00")
        )
        original = account.account_balance
        interest = account.apply_daily_interest()
        assert interest == Decimal("0.00")
        account.refresh_from_db()
        assert account.account_balance == original

    def test_interest_creates_transaction_record(self, customer, make_bank_account):
        account = make_bank_account(
            customer, account_type="savings", balance=Decimal("10000.00")
        )
        before_count = Transaction.objects.filter(
            receiver=customer,
            transaction_type=Transaction.TransactionType.INTEREST,
        ).count()
        account.apply_daily_interest()
        after_count = Transaction.objects.filter(
            receiver=customer,
            transaction_type=Transaction.TransactionType.INTEREST,
        ).count()
        assert after_count == before_count + 1


@pytest.mark.django_db
class TestPendingTransaction:
    def test_create_for_user_sets_15_minute_expiry(self, customer):
        pending = PendingTransaction.create_for_user(
            user=customer,
            flow_type=PendingTransaction.FlowType.WITHDRAWAL,
            payload={"account_number": "FFH001", "amount": "100.00"},
        )
        delta = pending.expires_at - timezone.now()
        # Should be ~15 minutes — allow 5 second buffer
        assert 14 * 60 < delta.total_seconds() <= 15 * 60 + 5

    def test_is_expired_returns_false_for_fresh_token(self, customer):
        pending = PendingTransaction.create_for_user(
            user=customer,
            flow_type=PendingTransaction.FlowType.TRANSFER,
            payload={"amount": "50.00"},
        )
        assert pending.is_expired() is False

    def test_is_expired_returns_true_for_old_token(self, customer):
        pending = PendingTransaction.create_for_user(
            user=customer,
            flow_type=PendingTransaction.FlowType.TRANSFER,
            payload={"amount": "50.00"},
        )
        pending.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        pending.save()
        assert pending.is_expired() is True

    def test_token_is_unique(self, customer):
        p1 = PendingTransaction.create_for_user(
            customer, PendingTransaction.FlowType.WITHDRAWAL, {}
        )
        p2 = PendingTransaction.create_for_user(
            customer, PendingTransaction.FlowType.WITHDRAWAL, {}
        )
        assert p1.token != p2.token

    def test_str_includes_flow_type_and_user(self, customer):
        pending = PendingTransaction.create_for_user(
            customer, PendingTransaction.FlowType.TRANSFER, {}
        )
        assert "transfer" in str(pending).lower()
