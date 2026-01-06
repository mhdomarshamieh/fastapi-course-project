import pytest
from httpx import AsyncClient

from social_media_app import security
from social_media_app.tests.helpers import create_comment, create_post, like_post


@pytest.fixture
async def created_comment(
    created_post: dict, async_client: AsyncClient, logged_in_token: str
) -> dict:
    # Fixture that creates a comment on the 'created_post'
    return await create_comment(
        "Test Comment Body", created_post["id"], async_client, logged_in_token
    )


@pytest.fixture
async def mock_generate_cute_creature_api(mocker):
    return mocker.patch(
        "social_media_app.tasks._generate_cute_creature_api",
        return_value={"output_url": "https://example.net/image.png"},
    )


@pytest.mark.anyio
async def test_create_post(
    async_client: AsyncClient, logged_in_token: str, confirmed_user: dict
):
    body = "Hello, this is a test post!"

    # 1. Send POST request
    response = await async_client.post(
        "/post",
        json={"body": body},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    # 2. Check status code is 200 OK
    assert response.status_code == 200

    # 3. Check response contains expected data
    # We check if expected items are a subset of the response items
    assert {
        "id": 1,
        "body": body,
        "user_id": confirmed_user["id"],
        "image_url": None,
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_create_post_with_prompt(
    async_client: AsyncClient, logged_in_token: str, mock_generate_cute_creature_api
):
    body = "Test post"
    response = await async_client.post(
        "/post?prompt=A cat",
        json={"body": body},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    assert {
        "id": 1,
        "body": body,
        "image_url": None,
    }.items() <= response.json().items()
    mock_generate_cute_creature_api.assert_called()


@pytest.mark.anyio
async def test_create_post_without_body(
    async_client: AsyncClient, logged_in_token: str
):
    # 1. Send POST request with empty body
    response = await async_client.post(
        "/post",
        json={},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    # 2. Check status code is 422 (Validation Error)
    assert response.status_code == 422

    # 3. Verify the error is about the missing 'body' field
    assert response.json()["detail"][0]["loc"] == ["body", "body"]


@pytest.mark.anyio
async def test_create_post_expired_token(
    async_client: AsyncClient, confirmed_user: dict, mocker
):
    mocker.patch(
        "social_media_app.security.access_token_expire_minutes", return_value=-1
    )
    token = security.create_access_token(confirmed_user["email"])
    response = await async_client.post(
        "/post",
        json={"body": "test body"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert "Token Has Expired" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_posts(async_client: AsyncClient, created_post: dict):
    # 1. Send GET request
    response = await async_client.get("/post")

    # 2. Check status code is 200 OK
    assert response.status_code == 200

    # 3. Verify the list contains the post created by the fixture
    assert created_post.items() <= response.json()[0].items()


@pytest.mark.anyio
@pytest.mark.parametrize("sorting, expected_order", [("new", [2, 1]), ("old", [1, 2])])
async def test_get_posts_sorting(
    async_client: AsyncClient,
    logged_in_token: str,
    sorting: str,
    expected_order: list[int],
):
    await create_post("Test Post 1", async_client, logged_in_token)
    await create_post("Test Post 2", async_client, logged_in_token)

    response = await async_client.get("/post", params={"sorting": sorting})
    assert response.status_code == 200

    data = response.json()
    post_ids = [post["id"] for post in data]
    assert post_ids == expected_order


@pytest.mark.anyio
async def test_get_posts_sorting_likes(
    async_client: AsyncClient,
    logged_in_token: str,
):
    await create_post("Test Post 1", async_client, logged_in_token)
    await create_post("Test Post 2", async_client, logged_in_token)
    await like_post(1, async_client, logged_in_token)
    response = await async_client.get("/post", params={"sorting": "most_likes"})
    assert response.status_code == 200

    data = response.json()
    excepted_order = [1, 2]
    post_ids = [post["id"] for post in data]
    assert post_ids == excepted_order


@pytest.mark.anyio
async def test_get_all_posts_wrong_sorting(async_client: AsyncClient):
    response = await async_client.get("/post", params={"sorting": "wrong"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_comment(
    async_client: AsyncClient,
    created_post: dict,
    logged_in_token: str,
    confirmed_user: dict,
):
    body = "This is a test comment."

    # 1. Send POST request to create comment
    response = await async_client.post(
        "/comment",
        json={"body": body, "post_id": created_post["id"]},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    # 2. Check status code is 200 OK
    assert response.status_code == 200

    # 3. Verify response data
    assert {
        "id": 1,
        "body": body,
        "post_id": created_post["id"],
        "user_id": confirmed_user["id"],
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_get_comments_for_post(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    # 1. Send GET request for comments of a specific post
    response = await async_client.get(f"/posts/{created_post['id']}/comments")

    # 2. Check status code is 200 OK
    assert response.status_code == 200

    # 3. Verify the list contains the comment created by the fixture
    assert response.json() == [created_comment]


@pytest.mark.anyio
async def test_get_comments_on_post_empty(
    async_client: AsyncClient, created_post: dict
):
    # 1. Send GET request for a post with no comments
    response = await async_client.get(f"/posts/{created_post['id']}/comments")

    # 2. Check status code is 200 OK
    assert response.status_code == 200

    # 3. Verify the list is empty
    assert response.json() == []


@pytest.mark.anyio
async def test_get_post_with_comments(
    async_client: AsyncClient, created_post: dict, created_comment: dict
):
    # 1. Send GET request for a post (assuming endpoint returns comments too)
    response = await async_client.get(f"/posts/{created_post['id']}")

    # 2. Check status code is 200 OK
    assert response.status_code == 200

    # 3. Verify response contains both post and comments
    expected_response = {
        "post": {**created_post, "likes": 0},
        "comments": [created_comment],
    }
    assert response.json() == expected_response


@pytest.mark.anyio
async def test_like_post(
    async_client: AsyncClient, created_post: dict, logged_in_token: str
):
    response = await async_client.post(
        "/like",
        json={"post_id": created_post["id"]},
        headers={"Authorization": f"Bearer {logged_in_token}"},
    )

    assert response.status_code == 201
