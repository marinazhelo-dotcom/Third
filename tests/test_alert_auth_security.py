from services.alert_auth.app.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("secret")
    assert hashed != "secret"
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip():
    token = create_access_token(42, "admin", "bob")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert payload["username"] == "bob"
