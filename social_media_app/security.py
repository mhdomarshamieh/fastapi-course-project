import datetime
import logging
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from social_media_app.database import database, user_table

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGOTHIRTHM = "HS256"
SECRET_KEY = "124zdfgfmfjjfdlgnfsdjfsdfhsdfsdfnnfjfkdfl3504fnfms4322jgkdnjdkdngjfjdjd"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_creadentials_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def access_token_expire_minutes() -> int:
    return 30


def confirm_token_expire_minutes() -> int:
    return 1440


def create_access_token(email: str) -> str:
    logger.debug("creating access token", extra={"email": email})
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=access_token_expire_minutes()
    )
    jwt_data = {"sub": email, "exp": expire, "type": "access"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGOTHIRTHM)
    return encoded_jwt


def create_confirmation_token(email: str) -> str:
    logger.debug("creating access token", extra={"email": email})
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=confirm_token_expire_minutes()
    )
    jwt_data = {"sub": email, "exp": expire, "type": "confirmation"}
    encoded_jwt = jwt.encode(jwt_data, key=SECRET_KEY, algorithm=ALGOTHIRTHM)
    return encoded_jwt


def get_subject_for_token_type(
    token: str, type: Literal["access", "confirmation"]
) -> str:
    try:
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGOTHIRTHM])
    except ExpiredSignatureError as e:
        raise create_creadentials_exception("Token Has Expired") from e
    except JWTError as e:
        raise create_creadentials_exception("Invalid Token") from e

    email = payload.get("sub")
    if email is None:
        raise create_creadentials_exception("Token missing sub field")

    token_type = payload.get("type")
    if token_type is None or token_type != type:
        raise create_creadentials_exception(
            f"Token has incorrect type, expected '{type}'"
        )

    return email


def get_password_hash(password: str) -> str:
    logger.debug("Hashing password")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    logger.debug("Verifying password")
    return pwd_context.verify(plain_password, hashed_password)


async def get_user_by_email(email: str):
    logger.debug("Fetching user by email", extra={"email": email})
    query = user_table.select().where(user_table.c.email == email)
    result = await database.fetch_one(query)
    if result:
        logger.debug("User found", extra={"email": email})
        return result


async def authenticate_user(email: str, password: str):
    logger.debug("authenticating user", extra={"email": email})
    user = await get_user_by_email(email)
    if not user:
        raise create_creadentials_exception("Invalid Email or Password")
    if not verify_password(password, user.password):
        raise create_creadentials_exception("Invalid Email or Password")
    if not user.confirmed:
        raise create_creadentials_exception("User has not confirmed email")

    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    email = get_subject_for_token_type(token, "access")
    user = await get_user_by_email(email)
    if user is None:
        raise create_creadentials_exception("Could not find user for this token")

    return user
