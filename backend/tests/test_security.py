from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.schemas.auth import ResetPasswordRequest


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


def test_password_reset_schema_accepts_generated_token() -> None:
    token = create_password_reset_token("1d239e5b-f046-485c-95f6-56fc6c716e7c")

    payload = ResetPasswordRequest(
        token=token,
        password_nueva="UnaClaveNueva123",
    )

    assert payload.token == token
    assert decode_token(payload.token, "password_reset")["type"] == "password_reset"
