"""Password hashing utilities using bcrypt via passlib.

Never store or log plain-text passwords. Use hash_password() before persisting
and verify_password() for authentication checks.
"""

from passlib.context import CryptContext

_PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of *plain_password*.

    Args:
        plain_password: The user-supplied password in plain text.

    Returns:
        A bcrypt hash string safe to store in the database.
    """
    return _PWD_CONTEXT.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify *plain_password* against its stored *hashed_password*.

    Args:
        plain_password: Candidate password provided by the user.
        hashed_password: The bcrypt hash stored in the database.

    Returns:
        True if the password matches, False otherwise.
    """
    return bool(_PWD_CONTEXT.verify(plain_password, hashed_password))
