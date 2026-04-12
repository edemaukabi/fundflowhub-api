"""
Tests for custom DRF permission classes.
"""
import pytest
from unittest.mock import MagicMock
from core_apps.common.permissions import (
    IsAccountExecutive,
    IsTeller,
    IsBranchManager,
    IsAccountExecutiveOrBranchManager,
)


def _make_request(role=None, authenticated=True):
    """Build a minimal mock request with a user."""
    user = MagicMock()
    user.is_authenticated = authenticated
    user.role = role
    return MagicMock(user=user)


@pytest.mark.parametrize("perm_class,allowed_role,blocked_roles", [
    (IsAccountExecutive, "account_executive", ["customer", "teller", "branch_manager"]),
    (IsTeller, "teller", ["customer", "account_executive", "branch_manager"]),
    (IsBranchManager, "branch_manager", ["customer", "teller", "account_executive"]),
])
class TestRolePermissions:
    def test_correct_role_is_allowed(self, perm_class, allowed_role, blocked_roles):
        perm = perm_class()
        request = _make_request(role=allowed_role, authenticated=True)
        assert perm.has_permission(request, MagicMock()) is True

    def test_blocked_roles_are_denied(self, perm_class, allowed_role, blocked_roles):
        perm = perm_class()
        for role in blocked_roles:
            request = _make_request(role=role, authenticated=True)
            assert perm.has_permission(request, MagicMock()) is False, \
                f"{perm_class.__name__} should deny role '{role}'"

    def test_unauthenticated_is_denied(self, perm_class, allowed_role, blocked_roles):
        perm = perm_class()
        request = _make_request(role=allowed_role, authenticated=False)
        assert perm.has_permission(request, MagicMock()) is False


class TestIsAccountExecutiveOrBranchManager:
    def test_account_executive_is_allowed(self):
        perm = IsAccountExecutiveOrBranchManager()
        assert perm.has_permission(_make_request("account_executive"), MagicMock()) is True

    def test_branch_manager_is_allowed(self):
        perm = IsAccountExecutiveOrBranchManager()
        assert perm.has_permission(_make_request("branch_manager"), MagicMock()) is True

    def test_customer_is_denied(self):
        perm = IsAccountExecutiveOrBranchManager()
        assert perm.has_permission(_make_request("customer"), MagicMock()) is False

    def test_teller_is_denied(self):
        perm = IsAccountExecutiveOrBranchManager()
        assert perm.has_permission(_make_request("teller"), MagicMock()) is False

    def test_unauthenticated_is_denied(self):
        perm = IsAccountExecutiveOrBranchManager()
        assert perm.has_permission(_make_request("account_executive", authenticated=False), MagicMock()) is False
