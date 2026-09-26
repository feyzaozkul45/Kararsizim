import uuid

from django.conf import settings

VOTER_COOKIE = "kz_voter"
VOTER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # one year


def get_voter_token(request):
    """Return the visitor's token from the cookie, or None if missing/invalid."""
    value = request.COOKIES.get(VOTER_COOKIE, "")
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None


def new_voter_token():
    return str(uuid.uuid4())


def set_voter_cookie(response, token):
    response.set_cookie(
        VOTER_COOKIE,
        token,
        max_age=VOTER_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    return response
