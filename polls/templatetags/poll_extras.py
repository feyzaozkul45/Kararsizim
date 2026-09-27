import hashlib

from django import template

register = template.Library()

AVATAR_TINT_COUNT = 5


@register.filter
def avatar_tint(username):
    """Stable color index for a username's avatar, independent of pk."""
    digest = hashlib.md5(username.encode()).hexdigest()
    return int(digest, 16) % AVATAR_TINT_COUNT


@register.filter
def initial(username):
    return username[:1].upper() if username else "?"
