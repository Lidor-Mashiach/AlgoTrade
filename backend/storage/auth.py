"""Registration & login. Passwords are HASHED — decryption is forbidden (and impossible)."""
from __future__ import annotations
import bcrypt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, stored_hash: str) -> bool:
    """Hash the typed password and compare to the stored hash. No decryption, ever."""
    return bcrypt.checkpw(plain.encode(), stored_hash.encode())


def register(conn, first, last, email, password) -> None:
    # TODO: insert user with hash_password(password); handle duplicate email
    raise NotImplementedError


def login(conn, email, password) -> dict | None:
    # TODO: fetch user by email, verify_password(...), return user dict or None
    raise NotImplementedError
