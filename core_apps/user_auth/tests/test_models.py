"""
Tests for the User model: OTP flow, lockout logic, full_name, is_test_account.
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserFullName:
    def test_full_name_combines_first_and_last(self, customer):
        customer.first_name = "alice"
        customer.last_name = "smith"
        customer.save()
        assert customer.full_name == "Alice Smith"

    def test_full_name_strips_whitespace(self, customer):
        customer.first_name = " bob "
        customer.last_name = " jones "
        customer.save()
        assert customer.full_name == "Bob Jones"


@pytest.mark.django_db
class TestOTPFlow:
    def test_set_otp_stores_value_and_expiry(self, customer):
        customer.set_otp("123456")
        customer.refresh_from_db()
        assert customer.otp == "123456"
        assert customer.otp_expiry_time > timezone.now()

    def test_verify_otp_returns_true_and_clears(self, customer):
        customer.set_otp("654321")
        assert customer.verify_otp("654321") is True
        customer.refresh_from_db()
        assert customer.otp == ""
        assert customer.otp_expiry_time is None

    def test_verify_otp_wrong_code_returns_false(self, customer):
        customer.set_otp("111111")
        assert customer.verify_otp("999999") is False

    def test_verify_otp_expired_returns_false(self, customer):
        customer.set_otp("123456")
        # Force expiry into the past
        customer.otp_expiry_time = timezone.now() - timezone.timedelta(minutes=1)
        customer.save()
        assert customer.verify_otp("123456") is False


@pytest.mark.django_db
class TestLoginLockout:
    def test_failed_attempts_increment(self, customer, settings):
        settings.LOGIN_ATTEMPTS = 3
        settings.LOCKOUT_DURATION = timezone.timedelta(minutes=30)
        customer.handle_failed_login_attempts()
        customer.refresh_from_db()
        assert customer.failed_login_attempts == 1
        assert customer.account_status == "active"

    def test_account_locks_after_max_attempts(self, customer, settings, mailoutbox):
        settings.LOGIN_ATTEMPTS = 3
        settings.LOCKOUT_DURATION = timezone.timedelta(minutes=30)
        for _ in range(3):
            customer.handle_failed_login_attempts()
        customer.refresh_from_db()
        assert customer.account_status == "locked"
        assert customer.is_locked_out is True

    def test_reset_clears_all_lockout_state(self, customer, settings):
        settings.LOGIN_ATTEMPTS = 3
        settings.LOCKOUT_DURATION = timezone.timedelta(minutes=30)
        customer.handle_failed_login_attempts()
        customer.reset_failed_login_attempts()
        customer.refresh_from_db()
        assert customer.failed_login_attempts == 0
        assert customer.account_status == "active"
        assert customer.last_failed_login is None

    def test_unlock_account_clears_locked_status(self, customer, settings):
        settings.LOGIN_ATTEMPTS = 3
        settings.LOCKOUT_DURATION = timezone.timedelta(minutes=30)
        customer.account_status = "locked"
        customer.failed_login_attempts = 3
        customer.last_failed_login = timezone.now()
        customer.save()
        customer.unlock_account()
        customer.refresh_from_db()
        assert customer.account_status == "active"
        assert customer.failed_login_attempts == 0

    def test_is_locked_out_auto_unlocks_after_duration(self, customer, settings):
        settings.LOGIN_ATTEMPTS = 3
        settings.LOCKOUT_DURATION = timezone.timedelta(minutes=30)
        customer.account_status = "locked"
        customer.failed_login_attempts = 3
        # Set last_failed_login far in the past — exceeds LOCKOUT_DURATION
        customer.last_failed_login = timezone.now() - timezone.timedelta(hours=1)
        customer.save()
        assert customer.is_locked_out is False
        customer.refresh_from_db()
        assert customer.account_status == "active"


@pytest.mark.django_db
class TestIsTestAccount:
    def test_default_is_false(self, customer):
        assert customer.is_test_account is False

    def test_can_be_set_to_true(self, make_user):
        user = make_user(is_test_account=True)
        assert user.is_test_account is True

    def test_test_and_live_users_are_separate(self, make_user):
        live = make_user(is_test_account=False)
        test = make_user(is_test_account=True)
        live_users = User.objects.filter(is_test_account=False)
        test_users = User.objects.filter(is_test_account=True)
        assert live in live_users
        assert test not in live_users
        assert test in test_users


@pytest.mark.django_db
class TestHasRole:
    def test_has_role_returns_true_for_correct_role(self, teller):
        assert teller.has_role("teller") is True

    def test_has_role_returns_false_for_wrong_role(self, teller):
        assert teller.has_role("customer") is False

    def test_has_role_branch_manager(self, branch_manager):
        assert branch_manager.has_role("branch_manager") is True
