import logging
from enum import Enum
from typing import Annotated

import sqlalchemy
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from social_media_app.database import comment_table, database, likes_table, post_table
from social_media_app.models.post import (
    Comment,
    CommentIn,
    PostLike,
    PostLikeIn,
    UserPost,
    UserPostIn,
    UserPostWithComments,
)
from social_media_app.models.user import User
from social_media_app.security import get_current_user
from social_media_app.tasks import generate_and_add_to_post

logger = logging.getLogger(__name__)

# BaseModel is used for data validation and serialization
router = APIRouter()


async def find_post(post_id: int):
    logger.info(f"Fetching post with id {post_id} from the database")
    query = post_table.select().where(post_table.c.id == post_id)
    logger.debug(query)
    return await database.fetch_one(query)


select_post_and_likes = (
    sqlalchemy.select(
        post_table, sqlalchemy.func.count(likes_table.c.id).label("likes")
    )
    .select_from(post_table.outerjoin(likes_table))
    .group_by(post_table.c.id)
)


class PostSorting(str, Enum):
    new = "new"
    old = "old"
    most_likes = "most_likes"


# response_model is used to define the shape of the response data
@router.post("/post", response_model=UserPost)
async def create_post(
    post: UserPostIn,
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    request: Request,
    prompt: str = None,
):
    logger.info("Creating a new post in the database")
    data = {**dict(post), "user_id": current_user.id}
    query = post_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)

    if prompt:
        background_tasks.add_task(
            generate_and_add_to_post,
            current_user.email,
            last_record_id,
            request.url_for("get_comments_for_post", post_id=last_record_id),
            database,
            prompt,
        )

    return {**data, "id": last_record_id}


@router.get("/post", response_model=list[UserPost])
async def get_posts(sorting: PostSorting = PostSorting.new):
    logger.info("Fetching all posts from the database")
    if sorting == PostSorting.new:
        query = select_post_and_likes.order_by(post_table.c.id.desc())
    elif sorting == PostSorting.old:
        query = select_post_and_likes.order_by(post_table.c.id.asc())
    elif sorting == PostSorting.most_likes:
        query = select_post_and_likes.order_by(sqlalchemy.desc("likes"))
    logger.debug(query)
    return await database.fetch_all(query)


@router.post("/comment", response_model=Comment)
async def create_comment(
    comment: CommentIn, current_user: Annotated[User, Depends(get_current_user)]
):
    post = await find_post(comment.post_id)
    if not post:
        logger.error(f"Post with id {comment.post_id} not found")
        raise HTTPException(status_code=404, detail="Post not found")
    data = {**dict(comment), "user_id": current_user.id}
    query = comment_table.insert().values(data)
    logger.debug(query)
    last_record_id = await database.execute(query)
    return {**data, "id": last_record_id}


@router.get("/posts/{post_id}/comments", response_model=list[Comment])
async def get_comments_for_post(post_id: int):
    logger.info(f"Fetching comments for post with id {post_id} from the database")
    post = await find_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    query = comment_table.select().where(comment_table.c.post_id == post_id)
    logger.debug(query)
    comments = await database.fetch_all(query)
    return comments


@router.get("/posts/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int):
    logger.info(
        f"Fetching post with id {post_id} along with its comments from the database"
    )

    query = select_post_and_likes.where(post_table.c.id == post_id)

    logger.debug(query)

    post = await database.fetch_one(query)
    if not post:
        logger.error(f"Post with id {post_id} not found")
        raise HTTPException(status_code=404, detail="Post not found")
    comments = await get_comments_for_post(post_id)
    return UserPostWithComments(post=post, comments=comments)


@router.post("/like", response_model=PostLike, status_code=201)
async def like_post(
    like: PostLikeIn, curren_user: Annotated[User, Depends(get_current_user)]
):
    logger.info("liking post")

    post = await find_post(like.post_id)
    if not post:
        raise HTTPException(status_code=401, detail="Post not found")

    data = {**dict(like), "user_id": curren_user.id}
    query = likes_table.insert().values(data)

    logger.debug(query)
    last_record_id = await database.execute(query)

    return {**data, "id": last_record_id}
