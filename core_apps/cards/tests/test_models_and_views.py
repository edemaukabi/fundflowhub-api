"""
Tests for VirtualCard model (CVV generation) and card API endpoints.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch


# ─── CVV model property ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVirtualCardCVV:
    def test_cvv_is_3_digits(self, customer, make_bank_account, make_virtual_card):
        """CVV property returns a 3-digit string. Uses CVV_SECRET_KEY from test settings."""
        account = make_bank_account(customer)
        with patch("core_apps.cards.utils.getenv", return_value="test-secret"):
            card = make_virtual_card(customer, account)
            cvv = card.cvv
            assert len(cvv) == 3
            assert cvv.isdigit()

    def test_cvv_is_deterministic(self, customer, make_bank_account, make_virtual_card):
        """Same card always produces the same CVV — no random element."""
        account = make_bank_account(customer)
        with patch("core_apps.cards.utils.getenv", return_value="stable-key"):
            card = make_virtual_card(customer, account)
            cvv1 = card.cvv
            cvv2 = card.cvv
            assert cvv1 == cvv2

    def test_cvv_not_stored_in_db(self, customer, make_bank_account, make_virtual_card):
        """VirtualCard table must have no cvv column."""
        from core_apps.cards.models import VirtualCard
        account = make_bank_account(customer)
        make_virtual_card(customer, account)
        db_field_names = [f.name for f in VirtualCard._meta.get_fields()]
        assert "cvv" not in db_field_names

    def test_different_cards_produce_different_cvvs(
        self, customer, make_bank_account, make_virtual_card
    ):
        account = make_bank_account(customer)
        with patch("core_apps.cards.utils.getenv", return_value="stable-key"):
            card1 = make_virtual_card(customer, account)
            card2 = make_virtual_card(customer, account)
            assert card1.card_number != card2.card_number
            assert card1.cvv != card2.cvv


# ─── Card list / create ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVirtualCardListCreate:
    url = "/api/v1/cards/virtual-cards/"

    def test_user_sees_only_own_cards(
        self, auth_client, make_user, make_bank_account, make_virtual_card
    ):
        client, user = auth_client
        other_user = make_user()
        account = make_bank_account(user)
        other_account = make_bank_account(other_user)

        make_virtual_card(user, account)
        make_virtual_card(other_user, other_account)

        resp = client.get(self.url)
        assert resp.status_code == 200
        # Response may be a list or paginated — handle both
        results = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
        assert len(results) == 1

    def test_unauthenticated_cannot_list_cards(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code in (401, 403)

    def test_create_card_linked_to_own_account(
        self, auth_client, make_bank_account
    ):
        client, user = auth_client
        account = make_bank_account(user)
        resp = client.post(
            self.url, {"bank_account_number": account.account_number}
        )
        assert resp.status_code == 201

    def test_create_card_linked_to_other_users_account_is_forbidden(
        self, auth_client, make_user, make_bank_account
    ):
        client, _ = auth_client
        other_user = make_user()
        other_account = make_bank_account(other_user)
        resp = client.post(
            self.url, {"bank_account_number": other_account.account_number}
        )
        assert resp.status_code == 403

    def test_cannot_create_more_than_3_cards(
        self, auth_client, make_bank_account, make_virtual_card
    ):
        client, user = auth_client
        account = make_bank_account(user)
        for _ in range(3):
            make_virtual_card(user, account)

        resp = client.post(
            self.url, {"bank_account_number": account.account_number}
        )
        assert resp.status_code == 400
        assert "3" in resp.data.get("error", "")


# ─── Card deletion ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVirtualCardDelete:
    def _url(self, pk):
        return f"/api/v1/cards/virtual-cards/{pk}/"

    def test_delete_zero_balance_card_succeeds(
        self, auth_client, make_bank_account, make_virtual_card
    ):
        client, user = auth_client
        account = make_bank_account(user)
        card = make_virtual_card(user, account, balance=Decimal("0.00"))
        resp = client.delete(self._url(card.pk))
        assert resp.status_code == 200

    def test_delete_card_with_balance_returns_400(
        self, auth_client, make_bank_account, make_virtual_card
    ):
        client, user = auth_client
        account = make_bank_account(user)
        card = make_virtual_card(user, account, balance=Decimal("50.00"))
        resp = client.delete(self._url(card.pk))
        assert resp.status_code == 400

    def test_cannot_delete_another_users_card(
        self, auth_client, make_user, make_bank_account, make_virtual_card
    ):
        client, _ = auth_client
        other_user = make_user()
        other_account = make_bank_account(other_user)
        other_card = make_virtual_card(other_user, other_account)
        resp = client.delete(self._url(other_card.pk))
        assert resp.status_code == 404


# ─── Card top-up ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVirtualCardTopUp:
    def _url(self, pk):
        return f"/api/v1/cards/virtual-cards/{pk}/top-up/"

    def test_top_up_transfers_balance(
        self, auth_client, make_bank_account, make_virtual_card
    ):
        client, user = auth_client
        account = make_bank_account(user, balance=Decimal("500.00"))
        card = make_virtual_card(user, account, balance=Decimal("0.00"))

        resp = client.put(self._url(card.pk), {"amount": "100.00"})
        assert resp.status_code == 200

        account.refresh_from_db()
        card.refresh_from_db()
        assert account.account_balance == Decimal("400.00")
        assert card.balance == Decimal("100.00")

    def test_top_up_insufficient_funds_returns_400(
        self, auth_client, make_bank_account, make_virtual_card
    ):
        client, user = auth_client
        account = make_bank_account(user, balance=Decimal("10.00"))
        card = make_virtual_card(user, account)
        resp = client.put(self._url(card.pk), {"amount": "500.00"})
        assert resp.status_code == 400

    def test_top_up_zero_amount_returns_400(
        self, auth_client, make_bank_account, make_virtual_card
    ):
        client, user = auth_client
        account = make_bank_account(user, balance=Decimal("100.00"))
        card = make_virtual_card(user, account)
        resp = client.put(self._url(card.pk), {"amount": "0.00"})
        assert resp.status_code == 400
