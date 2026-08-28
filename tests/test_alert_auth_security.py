from services.alert_auth.adapters.security.password import BcryptPasswordHasher
from services.alert_auth.adapters.security.jwt import PyJWTTokenService


def test_password_hash_roundtrip():
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash("secret")
    assert hashed != "secret"
    assert hasher.verify("secret", hashed)
    assert not hasher.verify("wrong", hashed)


def test_token_roundtrip():
    tokens = PyJWTTokenService()
    token = tokens.create_token(42, "admin", "bob")
    payload = tokens.decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"
    assert payload["username"] == "bob"
