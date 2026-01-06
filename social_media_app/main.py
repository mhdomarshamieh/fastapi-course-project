import logging
from contextlib import asynccontextmanager
from http.client import HTTPException

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from social_media_app.database import database
from social_media_app.logging_conf import configure_logging
from social_media_app.routers.post import router as post_router
from social_media_app.routers.upload import router as upload_router
from social_media_app.routers.user import router as user_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting up the application...")
    await database.connect()
    yield
    await database.disconnect()


# BaseModel is used for data validation and serialization
app = FastAPI(lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(post_router)
app.include_router(user_router)
app.include_router(upload_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    logger.error(f"HTTP Exception: {exc.detail}")
    return await http_exception_handler(request, exc)
