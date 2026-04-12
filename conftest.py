"""
Root conftest — shared fixtures and factories for all backend tests.
"""
import pytest
from decimal import Decimal
from django.contrib.auth.hashers import make_password
from rest_framework.test import APIClient


# ─── Factories ────────────────────────────────────────────────────────────────

@pytest.fixture
def make_user(db):
    """Return a factory function that creates User instances."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    _counter = [0]

    def _make(
        role="customer",
        is_test_account=False,
        account_status="active",
        **kwargs,
    ):
        _counter[0] += 1
        n = _counter[0]
        defaults = dict(
            email=f"user{n}@example.com",
            # username is NOT passed — UserManager.generate_username() sets it
            first_name="Test",
            last_name="User",
            id_no=1000000 + n,
            security_question="maiden_name",
            security_answer=make_password("fluffy"),
            role=role,
            is_test_account=is_test_account,
            account_status=account_status,
        )
        defaults.update(kwargs)
        password = defaults.pop("password", "testpass123!")
        user = User.objects.create_user(password=password, **defaults)
        return user

    return _make


@pytest.fixture
def customer(make_user):
    return make_user(role="customer")


@pytest.fixture
def teller(make_user):
    return make_user(role="teller")


@pytest.fixture
def account_executive(make_user):
    return make_user(role="account_executive")


@pytest.fixture
def branch_manager(make_user):
    return make_user(role="branch_manager")


@pytest.fixture
def make_bank_account(db):
    """Return a factory function that creates BankAccount instances."""
    from core_apps.accounts.models import BankAccount

    _counter = [0]

    def _make(
        user,
        account_type="savings",
        currency="us_dollar",
        balance=Decimal("1000.00"),
        fully_activated=True,
        kyc_verified=True,
        kyc_submitted=True,
        account_status="active",
        **kwargs,
    ):
        _counter[0] += 1
        n = _counter[0]
        return BankAccount.objects.create(
            user=user,
            account_number=f"FFH{n:013}",
            account_type=account_type,
            currency=currency,
            account_balance=balance,
            fully_activated=fully_activated,
            kyc_verified=kyc_verified,
            kyc_submitted=kyc_submitted,
            account_status=account_status,
            **kwargs,
        )

    return _make


@pytest.fixture
def make_virtual_card(db):
    """Return a factory function that creates VirtualCard instances."""
    from core_apps.cards.models import VirtualCard
    from django.utils import timezone

    _counter = [0]

    def _make(user, bank_account, balance=Decimal("0.00"), **kwargs):
        _counter[0] += 1
        n = _counter[0]
        return VirtualCard.objects.create(
            user=user,
            bank_account=bank_account,
            card_number=f"4{n:015}",
            expiry_date=timezone.now() + timezone.timedelta(days=365 * 3),
            balance=balance,
            **kwargs,
        )

    return _make


# ─── API clients ──────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(customer):
    """Authenticated API client for a customer user."""
    client = APIClient()
    client.force_authenticate(user=customer)
    return client, customer


@pytest.fixture
def teller_client(teller):
    client = APIClient()
    client.force_authenticate(user=teller)
    return client, teller


@pytest.fixture
def ae_client(account_executive):
    client = APIClient()
    client.force_authenticate(user=account_executive)
    return client, account_executive


@pytest.fixture
def bm_client(branch_manager):
    client = APIClient()
    client.force_authenticate(user=branch_manager)
    return client, branch_manager
