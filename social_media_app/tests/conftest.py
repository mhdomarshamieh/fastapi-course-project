import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, Request, Response

from social_media_app.tests.helpers import create_post

os.environ["ENV_STATE"] = "test"

from social_media_app.database import database, user_table
from social_media_app.main import app

# Force passlib to load the argon2 backend before any fake filesystem is activated.
# This prevents PackageNotFoundError when pyfakefs hides the package metadata.
from social_media_app.security import get_password_hash

get_password_hash("dummy")  # Trigger lazy backend initialization


@pytest.fixture(scope="session")
def anyio_backend():
    # Tells pytest to use the "asyncio" backend for async tests
    return "asyncio"


@pytest.fixture()
def client() -> Generator:
    # Creates a synchronous client (like a standard browser)
    # yield pauses execution and gives the client to the test
    yield TestClient(app)


@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    # Clear the in-memory tables before each test
    # autouse=True means this runs automatically for every test
    await database.connect()
    yield database
    await database.disconnect()


@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    # Creates an asynchronous client (like a modern async browser)
    # transport=ASGITransport(app=app) connects directly to the app in memory
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=client.base_url
    ) as ac:
        # yield gives the client to the test and pauses
        # When the test is done, execution resumes here to close the client
        yield ac


@pytest.fixture()
async def registered_user(async_client: AsyncClient) -> dict:
    # Fixture that registers a user before the test runs
    user_data = {"email": "testuser@example.com", "password": "securepassword"}
    await async_client.post("/register", json=user_data)
    query = user_table.select().where(user_table.c.email == user_data["email"])
    user = await database.fetch_one(query)
    user_data["id"] = user.id
    return user_data


@pytest.fixture()
async def confirmed_user(registered_user: dict) -> dict:
    query = (
        user_table.update()
        .where(user_table.c.email == registered_user["email"])
        .values(confirmed=True)
    )
    await database.execute(query)
    return registered_user


@pytest.fixture()
async def logged_in_token(async_client: AsyncClient, confirmed_user: dict) -> str:
    response = await async_client.post("/token", json=confirmed_user)
    return response.json()["access_token"]


@pytest.fixture(autouse=True)
def mock_httpx_client(mocker):
    mocked_client = mocker.patch("social_media_app.tasks.httpx.AsyncClient")

    mocked_async_client = Mock()
    response = Response(status_code=200, content="", request=Request("POST", "//"))
    mocked_async_client.post = AsyncMock(return_value=response)
    mocked_client.return_value.__aenter__.return_value = mocked_async_client

    return mocked_async_client


@pytest.fixture
async def created_post(async_client: AsyncClient, logged_in_token: str) -> dict:
    # Fixture that creates a post before the test runs
    return await create_post("Test Post Body", async_client, logged_in_token)
