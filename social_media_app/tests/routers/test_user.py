import pytest
from fastapi import BackgroundTasks
from httpx import AsyncClient


async def register_user(async_client: AsyncClient, email: str, password: str) -> dict:
    return await async_client.post(
        "/register", json={"email": email, "password": password}
    )


@pytest.mark.anyio
async def test_register_user(async_client: AsyncClient):
    email = "test@example.com"
    password = "strongpassword"
    response = await register_user(async_client, email, password)
    assert response.status_code == 201
    assert "User registered successfully" in response.json().get("detail")


@pytest.mark.anyio
async def test_confirm_user(async_client: AsyncClient, mocker):
    spy = mocker.spy(BackgroundTasks, "add_task")
    await register_user(async_client, "test@example.com", "1234")
    confirmation_url = str(spy.call_args[1]["confirmation_url"])
    response = await async_client.get(confirmation_url)

    assert response.status_code == 200
    assert "User confirmed" in response.json()["detail"]


@pytest.mark.anyio
async def test_confirm_user_expired_token(async_client: AsyncClient, mocker):
    mocker.patch(
        "social_media_app.security.confirm_token_expire_minutes", return_value=-1
    )
    spy = mocker.spy(BackgroundTasks, "add_task")
    await register_user(async_client, "test@example.com", "1234")
    confirmation_url = str(spy.call_args[1]["confirmation_url"])
    response = await async_client.get(confirmation_url)

    assert response.status_code == 401
    assert "Token Has Expired" in response.json()["detail"]


@pytest.mark.anyio
async def test_confirm_user_invalid_token(async_client: AsyncClient):
    response = await async_client.get("/confirm/invalid_token")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_register_user_existing_email(
    async_client: AsyncClient, registered_user: dict
):
    email = registered_user["email"]
    password = "anotherpassword"
    response = await register_user(async_client, email, password)
    assert response.status_code == 400
    assert response.json().get("detail") == "Email already registered"


@pytest.mark.anyio
async def test_login_user_not_confirmed(
    async_client: AsyncClient, registered_user: dict
):
    response = await async_client.post(
        "/token",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 401


@pytest.mark.anyio
async def test_login_user_doesnt_exist(async_client: AsyncClient):
    response = await async_client.post(
        "/token", json={"email": "test@gmail.com", "password": "1234"}
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_login_user(async_client: AsyncClient, confirmed_user: dict):
    response = await async_client.post(
        "/token",
        json={
            "email": confirmed_user["email"],
            "password": confirmed_user["password"],
        },
    )
    assert response.status_code == 200
