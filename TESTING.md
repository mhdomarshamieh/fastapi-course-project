# Beginner's Guide to Testing in FastAPI

This guide explains how the testing setup works in this project. It is designed for someone with no prior testing experience.

## 1. The Big Picture

We are using **pytest** to run our tests. Think of `pytest` as a robot that:
1.  Looks for files starting with `test_`.
2.  Looks for functions starting with `test_`.
3.  Runs them one by one.
4.  Reports if they passed (worked) or failed (broke).

We are testing a **FastAPI** application. Since our app is "Async" (it can handle multiple things at once), our tests also need to be "Async".

---

## 2. Key Concepts

### Fixtures (`conftest.py`)
Fixtures are helper functions that run **before** and **after** your tests. They set up the environment so your tests don't have to repeat code.

Think of a fixture like a **Chef** preparing ingredients before cooking:
*   **Setup:** Chop vegetables (Prepare database, create client).
*   **Yield:** Hand ingredients to the cook (Run the test).
*   **Teardown:** Clean the kitchen (Delete data, close connections).

### Generators (`yield` vs `return`)
*   **`return`**: Gives a value and stops. (Like buying a DVD).
*   **`yield`**: Gives a value, **pauses**, and waits for the test to finish, then resumes. (Like streaming a movie, or borrowing a book).
    *   **Why use it?** It allows us to run "Cleanup" code after the test finishes.

### Async vs Sync
*   **Sync (Synchronous):** One thing at a time. (Like a phone call).
*   **Async (Asynchronous):** Multiple things at once. (Like sending text messages).
*   **`async def`**: Defines an async function.
*   **`await`**: Waits for an async task to finish without blocking the whole computer.

---

## 3. Understanding `conftest.py`

This file contains "Global Fixtures" available to all tests.

```python
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
```
*   **What:** Tells pytest to use `asyncio`, which is the standard Python engine for running async code.

```python
@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    post_table.clear()
    comment_table.clear()
    yield
```
*   **What:** Clears the "fake database" (dictionaries) before **every** test.
*   **`autouse=True`**: Runs automatically without being asked.
*   **Why:** Ensures Test A doesn't mess up Test B by leaving old data behind.

```python
@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=client.base_url) as ac:
        yield ac
```
*   **What:** Creates a "Fake Browser" (`AsyncClient`) that talks directly to your API code.
*   **`transport=ASGITransport(app=app)`**: Connects directly to the app in memory (no internet needed).
*   **`yield ac`**: Pauses, lets the test use the client, then closes it automatically when the test is done.

---

## 4. Understanding `test_post.py`

This file contains the actual tests for posts and comments.

### Helper Functions
These are shortcuts to make tests easier to read.
*   `create_post`: Sends a POST request to create a post.
*   `create_comment`: Sends a POST request to create a comment.

### Test Fixtures
*   `created_post`: Automatically creates a post before a test runs. Used when testing "Get Posts" or "Create Comment".

### The Tests

**1. `test_create_post`**
*   **Goal:** Verify we can create a new post.
*   **Steps:**
    1.  Send data: `{"body": "Hello"}`.
    2.  Check status: Should be `200 OK`.
    3.  Check data: Response should contain `id` and `body`.

**2. `test_create_post_without_body`**
*   **Goal:** Verify the API rejects bad data.
*   **Steps:**
    1.  Send empty data `{}`.
    2.  Check status: Should be `422 Unprocessable Entity` (Validation Error).

**3. `test_get_posts`**
*   **Goal:** Verify we can list all posts.
*   **Steps:**
    1.  Use `created_post` fixture (so one post already exists).
    2.  Get `/post`.
    3.  Check that the list contains the post we created.

---

## 5. How to Run Tests

Open your terminal in VS Code and run:

**Run all tests:**
```bash
pytest
```

**Run tests and show print output (Debug):**
```bash
pytest -s
```

**Run a specific test file:**
```bash
pytest social_media_app/tests/routers/test_post.py
```

**Run a specific test function:**
```bash
pytest -k "test_create_post"
```

## 6. Troubleshooting

**Error: `AsyncClient.__init__() got an unexpected keyword argument 'app'`**
*   **Cause:** Old code style.
*   **Fix:** Use `transport=ASGITransport(app=app)` instead of `app=app`.

**Error: `AssertionError: assert response.status_code == 200`**
*   **Cause:** The API returned an error (like 422 or 500).
*   **Fix:** Print `response.json()` to see the error message.

**Error: `RuntimeError: Event loop is closed`**
*   **Cause:** Async setup issue.
*   **Fix:** Ensure `anyio_backend` fixture is present in `conftest.py`.
