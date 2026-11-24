from .models import AccountProfile


def _active_profile(user):
    if not user.is_authenticated or not user.is_active:
        return None
    return getattr(user, "account_profile", None)


def is_customer(user):
    profile = _active_profile(user)
    return profile is not None and profile.role == AccountProfile.Role.CUSTOMER


def get_merchant_for_user(user):
    profile = _active_profile(user)
    if profile is not None and profile.role == AccountProfile.Role.MERCHANT:
        return profile.merchant
    return None
