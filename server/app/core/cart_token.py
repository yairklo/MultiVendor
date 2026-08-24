import hmac
import hashlib
import time
from app.core.config import settings

# A guest (unauthenticated) cart is looked up by Cart.id, a client-generated
# UUID with no secrecy of its own. Without this, anyone who obtains/guesses
# the UUID can read or mutate someone else's guest cart. The token below is a
# stateless capability: possession of it (not the bare UUID) is what proves
# the caller is the party the cart was created for.
GUEST_CART_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _sign(cart_id: str, exp: int) -> str:
    msg = f"{cart_id}:{exp}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def issue_guest_cart_token(cart_id: str) -> str:
    exp = int(time.time()) + GUEST_CART_TTL_SECONDS
    sig = _sign(cart_id, exp)
    return f"{exp}.{sig}"


def verify_guest_cart_token(token: str, cart_id: str) -> bool:
    try:
        exp_str, sig = token.split(".", 1)
        exp = int(exp_str)
    except (ValueError, AttributeError):
        return False

    if exp < int(time.time()):
        return False

    expected = _sign(cart_id, exp)
    return hmac.compare_digest(expected, sig)
