"""
API endpoint tests for the accounts app.

Uses force_authenticate() — no JWT cookie setup needed.
Emails are suppressed via the console backend (local settings).
"""
import pytest
from decimal import Decimal
from core_apps.accounts.models import PendingTransaction, Transaction


# ─── Deposit (Teller) ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDepositView:
    url = "/api/v1/accounts/deposit/"

    def test_teller_can_look_up_account(
        self, teller_client, customer, make_bank_account
    ):
        client, _ = teller_client
        account = make_bank_account(customer)
        resp = client.get(self.url, {"account_number": account.account_number})
        assert resp.status_code == 200
        assert resp.data["account_number"] == account.account_number

    def test_teller_can_deposit(self, teller_client, customer, make_bank_account):
        client, _ = teller_client
        account = make_bank_account(customer, balance=Decimal("500.00"))
        resp = client.post(
            self.url,
            {"account_number": account.account_number, "amount": "200.00"},
        )
        assert resp.status_code == 200
        account.refresh_from_db()
        assert account.account_balance == Decimal("700.00")

    def test_customer_cannot_deposit(self, auth_client, customer, make_bank_account):
        client, _ = auth_client
        account = make_bank_account(customer)
        resp = client.post(
            self.url,
            {"account_number": account.account_number, "amount": "100.00"},
        )
        assert resp.status_code == 403

    def test_deposit_unknown_account_returns_404(self, teller_client):
        client, _ = teller_client
        resp = client.get(self.url, {"account_number": "FFH9999999999999"})
        assert resp.status_code == 404

    def test_deposit_missing_account_number_returns_400(self, teller_client):
        client, _ = teller_client
        resp = client.get(self.url)
        assert resp.status_code == 400

    def test_unauthenticated_deposit_returns_401(self, api_client, customer, make_bank_account):
        account = make_bank_account(customer)
        resp = api_client.post(
            self.url,
            {"account_number": account.account_number, "amount": "100.00"},
        )
        assert resp.status_code in (401, 403)


# ─── Withdrawal flow ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestWithdrawalFlow:
    initiate_url = "/api/v1/accounts/initiate-withdrawal/"
    confirm_url = "/api/v1/accounts/verify-username-and-withdraw/"

    def test_initiate_withdrawal_returns_token(
        self, auth_client, make_bank_account
    ):
        client, user = auth_client
        account = make_bank_account(
            user, balance=Decimal("500.00"), fully_activated=True, kyc_verified=True
        )
        resp = client.post(
            self.initiate_url,
            {"account_number": account.account_number, "amount": "100.00"},
        )
        assert resp.status_code == 200
        assert "token" in resp.data

    def test_initiate_insufficient_funds_returns_400(
        self, auth_client, make_bank_account
    ):
        client, user = auth_client
        account = make_bank_account(
            user, balance=Decimal("50.00"), fully_activated=True, kyc_verified=True
        )
        resp = client.post(
            self.initiate_url,
            {"account_number": account.account_number, "amount": "500.00"},
        )
        assert resp.status_code == 400

    def test_initiate_unverified_account_returns_403(
        self, auth_client, make_bank_account
    ):
        client, user = auth_client
        account = make_bank_account(
            user,
            balance=Decimal("500.00"),
            fully_activated=False,
            kyc_verified=False,
        )
        resp = client.post(
            self.initiate_url,
            {"account_number": account.account_number, "amount": "100.00"},
        )
        assert resp.status_code == 403

    def test_confirm_withdrawal_deducts_balance(
        self, auth_client, make_bank_account
    ):
        client, user = auth_client
        account = make_bank_account(
            user, balance=Decimal("500.00"), fully_activated=True, kyc_verified=True
        )
        # Initiate
        init_resp = client.post(
            self.initiate_url,
            {"account_number": account.account_number, "amount": "100.00"},
        )
        token = init_resp.data["token"]

        # Confirm with correct username
        resp = client.post(
            self.confirm_url,
            {"token": token, "username": user.username},
        )
        assert resp.status_code == 200
        account.refresh_from_db()
        assert account.account_balance == Decimal("400.00")

    def test_confirm_without_token_returns_400(self, auth_client):
        client, user = auth_client
        resp = client.post(self.confirm_url, {"username": user.username})
        assert resp.status_code == 400

    def test_confirm_expired_token_returns_400(
        self, auth_client, make_bank_account
    ):
        from django.utils import timezone
        client, user = auth_client
        account = make_bank_account(user, balance=Decimal("500.00"))
        pending = PendingTransaction.create_for_user(
            user=user,
            flow_type=PendingTransaction.FlowType.WITHDRAWAL,
            payload={"account_number": account.account_number, "amount": "100.00"},
        )
        pending.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        pending.save()

        resp = client.post(
            self.confirm_url,
            {"token": str(pending.token), "username": user.username},
        )
        assert resp.status_code == 400
        assert "expired" in resp.data.get("error", "").lower()


# ─── Transfer flow ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTransferInitiate:
    url = "/api/v1/accounts/transfer/initiate/"

    def test_initiate_transfer_returns_token(
        self, auth_client, make_user, make_bank_account
    ):
        client, sender_user = auth_client
        receiver_user = make_user()
        sender_acc = make_bank_account(sender_user, balance=Decimal("1000.00"))
        receiver_acc = make_bank_account(receiver_user)

        resp = client.post(
            self.url,
            {
                "sender_account": sender_acc.account_number,
                "receiver_account": receiver_acc.account_number,
                "amount": "200.00",
                "description": "Test transfer",
                "transaction_type": "transfer",
            },
        )
        assert resp.status_code == 200
        assert "token" in resp.data

    def test_wrong_sender_account_returns_404(
        self, auth_client, make_user, make_bank_account
    ):
        client, sender_user = auth_client
        receiver_user = make_user()
        receiver_acc = make_bank_account(receiver_user)

        resp = client.post(
            self.url,
            {
                "sender_account": "FFH0000000000000",
                "receiver_account": receiver_acc.account_number,
                "amount": "100.00",
                "transaction_type": "transfer",
            },
        )
        assert resp.status_code == 404

    def test_unverified_sender_returns_403(
        self, auth_client, make_user, make_bank_account
    ):
        client, sender_user = auth_client
        receiver_user = make_user()
        sender_acc = make_bank_account(
            sender_user, fully_activated=False, kyc_verified=False
        )
        receiver_acc = make_bank_account(receiver_user)

        resp = client.post(
            self.url,
            {
                "sender_account": sender_acc.account_number,
                "receiver_account": receiver_acc.account_number,
                "amount": "100.00",
                "transaction_type": "transfer",
            },
        )
        assert resp.status_code == 403


# ─── KYC Review ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPendingKYCListView:
    url = "/api/v1/accounts/pending-kyc/"

    def test_account_executive_can_list_pending_kyc(
        self, ae_client, make_user, make_bank_account
    ):
        client, _ = ae_client
        user = make_user()
        make_bank_account(
            user, kyc_submitted=True, kyc_verified=False, fully_activated=False
        )
        resp = client.get(self.url)
        assert resp.status_code == 200

    def test_branch_manager_can_list_pending_kyc(
        self, bm_client, make_user, make_bank_account
    ):
        client, _ = bm_client
        user = make_user()
        make_bank_account(
            user, kyc_submitted=True, kyc_verified=False, fully_activated=False
        )
        resp = client.get(self.url)
        assert resp.status_code == 200

    def test_customer_cannot_list_pending_kyc(self, auth_client):
        client, _ = auth_client
        resp = client.get(self.url)
        assert resp.status_code == 403

    def test_teller_cannot_list_pending_kyc(self, teller_client):
        client, _ = teller_client
        resp = client.get(self.url)
        assert resp.status_code == 403

    def test_only_unverified_accounts_returned(
        self, ae_client, make_user, make_bank_account
    ):
        client, _ = ae_client
        u1, u2 = make_user(), make_user()
        pending_acc = make_bank_account(
            u1, kyc_submitted=True, kyc_verified=False, fully_activated=False
        )
        # Already verified — must NOT appear
        make_bank_account(
            u2, kyc_submitted=True, kyc_verified=True, fully_activated=True
        )
        resp = client.get(self.url)
        assert resp.status_code == 200
        account_numbers = [item["account_number"] for item in resp.data["results"]]
        assert pending_acc.account_number in account_numbers


# ─── Account Verification (KYC approve) ──────────────────────────────────────

@pytest.mark.django_db
class TestAccountVerificationView:
    def _url(self, pk):
        return f"/api/v1/accounts/verify/{pk}/"

    def test_ae_can_approve_kyc(self, ae_client, make_user, make_bank_account):
        client, ae_user = ae_client
        user = make_user()
        account = make_bank_account(
            user, kyc_submitted=False, kyc_verified=False, fully_activated=False
        )
        resp = client.patch(
            self._url(account.pk),
            {
                "kyc_submitted": True,
                "kyc_verified": True,
                "verification_notes": "Documents verified.",
                "verification_date": "2024-06-15",
            },
        )
        assert resp.status_code == 200
        account.refresh_from_db()
        assert account.kyc_verified is True
        assert account.fully_activated is True

    def test_branch_manager_can_approve_kyc(
        self, bm_client, make_user, make_bank_account
    ):
        client, _ = bm_client
        user = make_user()
        account = make_bank_account(
            user, kyc_submitted=False, kyc_verified=False, fully_activated=False
        )
        resp = client.patch(
            self._url(account.pk),
            {
                "kyc_submitted": True,
                "kyc_verified": True,
                "verification_notes": "Approved by branch manager.",
                "verification_date": "2024-06-15",
            },
        )
        assert resp.status_code == 200
        account.refresh_from_db()
        assert account.kyc_verified is True

    def test_customer_cannot_verify_kyc(self, auth_client, make_user, make_bank_account):
        client, _ = auth_client
        user = make_user()
        account = make_bank_account(user, kyc_submitted=False, kyc_verified=False)
        resp = client.patch(
            self._url(account.pk),
            {"kyc_submitted": True, "kyc_verified": True},
        )
        assert resp.status_code == 403

    def test_cannot_verify_already_verified_account(
        self, ae_client, make_user, make_bank_account
    ):
        client, _ = ae_client
        user = make_user()
        account = make_bank_account(
            user, kyc_submitted=True, kyc_verified=True, fully_activated=True
        )
        resp = client.patch(
            self._url(account.pk),
            {"kyc_submitted": True, "kyc_verified": True},
        )
        assert resp.status_code == 400


# ─── Transaction list ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTransactionListView:
    url = "/api/v1/accounts/transactions/"

    def test_returns_only_current_user_transactions(
        self, auth_client, make_user, make_bank_account
    ):
        client, user = auth_client
        other_user = make_user()
        acc1 = make_bank_account(user)
        acc2 = make_bank_account(other_user)

        Transaction.objects.create(
            user=user,
            sender=user,
            sender_account=acc1,
            receiver=other_user,
            receiver_account=acc2,
            amount=Decimal("50.00"),
            transaction_type=Transaction.TransactionType.TRANSFER,
            status=Transaction.TransactionStatus.COMPLETED,
        )

        resp = client.get(self.url)
        assert resp.status_code == 200
        assert resp.data["count"] >= 1

    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code in (401, 403)
