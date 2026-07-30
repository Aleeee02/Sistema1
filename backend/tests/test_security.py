from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verification() -> None:
    hashed = hash_password("UnaClaveSegura123")
    assert hashed != "UnaClaveSegura123"
    assert verify_password("UnaClaveSegura123", hashed)
    assert not verify_password("ClaveIncorrecta123", hashed)


def test_token_types() -> None:
    access = create_access_token("user-id", {"empresa_id": "empresa-id"})
    refresh = create_refresh_token("user-id", {"empresa_id": "empresa-id"})
    assert decode_token(access, "access")["type"] == "access"
    assert decode_token(refresh, "refresh")["type"] == "refresh"
