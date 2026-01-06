import pytest
from jose import jwt

from social_media_app import security


@pytest.mark.anyio
async def test_access_token_expire_minutes():
    assert security.access_token_expire_minutes() == 30


@pytest.mark.anyio
async def test_confirm_token_expire_minutes():
    assert security.confirm_token_expire_minutes() == 1440


@pytest.mark.anyio
async def test_create_access_token():
    token = security.create_access_token("123")
    assert {"sub": "123", "type": "access"}.items() <= jwt.decode(
        token, key=security.SECRET_KEY, algorithms=[security.ALGOTHIRTHM]
    ).items()


@pytest.mark.anyio
async def test_create_confirmation_token():
    token = security.create_confirmation_token("123")
    assert {"sub": "123", "type": "confirmation"}.items() <= jwt.decode(
        token, key=security.SECRET_KEY, algorithms=[security.ALGOTHIRTHM]
    ).items()


@pytest.mark.anyio
async def test_get_subject_for_token_type_valid_access():
    email = "test@gmail.com"
    token = security.create_access_token(email)
    assert email == security.get_subject_for_token_type(token, "access")


@pytest.mark.anyio
async def test_get_subject_for_token_type_expired(mocker):
    mocker.patch(
        "social_media_app.security.access_token_expire_minutes", return_value=-1
    )
    email = "test@gmail.com"
    token = security.create_access_token(email)
    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")

    assert "Token Has Expired" == exc_info.value.detail


@pytest.mark.anyio
async def test_get_subject_for_token_type_invalid():
    token = "invalid token"
    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")

    assert "Invalid Token" == exc_info.value.detail


@pytest.mark.anyio
async def test_get_subject_for_token_type_missing_sub():
    email = "test@gmail.com"
    token = security.create_access_token(email)
    payload = jwt.decode(
        token, key=security.SECRET_KEY, algorithms=[security.ALGOTHIRTHM]
    )
    del payload["sub"]
    token = jwt.encode(payload, key=security.SECRET_KEY, algorithm=security.ALGOTHIRTHM)

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")

    assert "Token missing sub field" == exc_info.value.detail


@pytest.mark.anyio
async def test_get_subject_for_token_type_wrong_type():
    email = "test@gmail.com"
    token = security.create_confirmation_token(email)

    with pytest.raises(security.HTTPException) as exc_info:
        security.get_subject_for_token_type(token, "access")

    assert "Token has incorrect type, expected 'access'" == exc_info.value.detail


@pytest.mark.anyio
async def test_password_hashing_and_verification():
    password = "securepassword"
    hashed_password = security.get_password_hash(password)
    assert hashed_password != password  # Ensure password is hashed

    is_verified = security.verify_password(password, hashed_password)
    assert is_verified  # Ensure the password verification works


@pytest.mark.anyio
async def test_get_user_by_email(registered_user: dict):
    user = await security.get_user_by_email(registered_user["email"])
    assert user is not None
    assert user.email == registered_user["email"]


@pytest.mark.anyio
async def test_get_user_by_email_not_found():
    user = await security.get_user_by_email("nonexistent@example.com")
    assert user is None


@pytest.mark.anyio
async def test_authenticate_user(confirmed_user: dict):
    user = await security.authenticate_user(
        confirmed_user["email"], confirmed_user["password"]
    )
    assert user.email == confirmed_user["email"]


@pytest.mark.anyio
async def test_authenticate_user_not_found():
    with pytest.raises(security.HTTPException):
        await security.authenticate_user("test@gmail.com", "1234")


@pytest.mark.anyio
async def test_authenticate_user_wrong_password(registered_user: dict):
    with pytest.raises(security.HTTPException):
        await security.authenticate_user(registered_user["email"], "wrong password")


@pytest.mark.anyio
async def test_get_current_user(registered_user: dict):
    token = security.create_access_token(registered_user["email"])
    user = await security.get_current_user(token)

    assert registered_user["email"] == user.email


@pytest.mark.anyio
async def test_get_current_user_with_invalid_token():
    token = security.create_access_token("test@gmail.com")
    with pytest.raises(security.HTTPException):
        await security.get_current_user(token)


@pytest.mark.anyio
async def test_get_current_user_wrong_tpye_token(registered_user: dict):
    token = security.create_confirmation_token(registered_user["email"])

    with pytest.raises(security.HTTPException):
        await security.get_current_user(token)
