import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from social_media_app import tasks
from social_media_app.database import database, user_table
from social_media_app.models.user import UserIn
from social_media_app.security import (
    authenticate_user,
    create_access_token,
    create_confirmation_token,
    get_password_hash,
    get_subject_for_token_type,
    get_user_by_email,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", status_code=201)
async def register_user(
    user_in: UserIn, background_tasks: BackgroundTasks, request: Request
):
    if await get_user_by_email(user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_password = get_password_hash(user_in.password)
    query = user_table.insert().values(email=user_in.email, password=hashed_password)
    logger.debug(f"Executing query: {query}")
    await database.execute(query)
    # await tasks.send_user_registration_email(
    #     user_in.email,
    #     confirmation_url=request.url_for(
    #         "confirm_email", token=create_confirmation_token(user_in.email)
    #     ),
    # )
    background_tasks.add_task(
        tasks.send_user_registration_email,
        user_in.email,
        confirmation_url=request.url_for(
            "confirm_email", token=create_confirmation_token(user_in.email)
        ),
    )
    return {
        "detail": "User registered successfully Please COnfirm your email",
    }


@router.post("/token")
async def login(user: UserIn):
    user = await authenticate_user(user.email, user.password)
    access_token = create_access_token(user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirm/{token}")
async def confirm_email(token: str):
    email = get_subject_for_token_type(token, "confirmation")
    query = (
        user_table.update().where(user_table.c.email == email).values(confirmed=True)
    )

    logger.debug(query)

    await database.execute(query)
    return {"detail": "User confirmed"}
