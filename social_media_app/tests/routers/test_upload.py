import contextlib
import pathlib
import sys
import tempfile

import pytest
from httpx import AsyncClient
from pyfakefs.fake_filesystem_unittest import Patcher


@pytest.fixture()
def fs():
    """Custom pyfakefs fixture that includes site-packages for package metadata access."""
    with Patcher() as patcher:
        # Add site-packages to allow package metadata to be found (for argon2-cffi, passlib, etc.)
        for path in sys.path:
            if "site-packages" in path and pathlib.Path(path).exists():
                patcher.fs.add_real_directory(path, read_only=True)
                break
        yield patcher.fs


@pytest.fixture()
def sample_image(fs) -> pathlib.Path:
    img_path = pathlib.Path(tempfile.gettempdir()) / "sample_image.png"
    fs.create_file(str(img_path), contents=b"fake image data")
    return img_path


@pytest.fixture(autouse=True)
def mock_b2_upload_file(mocker):
    mocker.patch(
        "social_media_app.routers.upload.b2_upload_file",
        return_value="https://fake-b2-url.com/sample_image.png",
    )


@pytest.fixture(autouse=True)
def aiofiles_mock_open(mocker, fs):
    mock_open = mocker.patch("aiofiles.open")

    @contextlib.asynccontextmanager
    async def mock_aiofiles_open(fname, mode: str = "r"):
        out_fs_mock = mocker.AsyncMock(name=f"async_file_open:{fname!r}/{mode!r}")
        with open(fname, mode) as fin:
            out_fs_mock.read.side_effect = fin.read
            out_fs_mock.write.side_effect = fin.write
            yield out_fs_mock

    mock_open.side_effect = mock_aiofiles_open
    return mock_open


async def call_upload_endpoint(
    async_client: AsyncClient, token: str, sample_image: pathlib.Path
):
    return await async_client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": open(sample_image, "rb")},
    )


@pytest.mark.anyio
async def test_upload_file_success(
    async_client: AsyncClient, logged_in_token: str, sample_image: pathlib.Path
):
    response = await call_upload_endpoint(async_client, logged_in_token, sample_image)

    assert response.status_code == 201
    assert response.json() == {
        "detail": f"successfully uploaded {sample_image.name}",
        "file_url": "https://fake-b2-url.com/sample_image.png",
    }
