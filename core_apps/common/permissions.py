from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import View


class IsAccountExecutive(permissions.BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        is_authenticated = request.user.is_authenticated
        has_role_attr = hasattr(request.user, "role")
        return (
            is_authenticated
            and has_role_attr
            and request.user.role == "account_executive"
        )


class IsTeller(permissions.BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        is_authenticated = request.user.is_authenticated
        has_role_attr = hasattr(request.user, "role")
        return is_authenticated and has_role_attr and request.user.role == "teller"


class IsBranchManager(permissions.BasePermission):
    def has_permission(self, request: Request, view: View) -> bool:
        is_authenticated = request.user.is_authenticated
        has_role_attr = hasattr(request.user, "role")
        return (
            is_authenticated and has_role_attr and request.user.role == "branch_manager"
        )


class IsAccountExecutiveOrBranchManager(permissions.BasePermission):
    """Grants access to both Account Executives and Branch Managers.

    Used for endpoints that both roles need: KYC review list, KYC approval,
    and the full customer profile list.
    """

    def has_permission(self, request: Request, view: View) -> bool:
        return (
            request.user.is_authenticated
            and hasattr(request.user, "role")
            and request.user.role in ("account_executive", "branch_manager")
        )
