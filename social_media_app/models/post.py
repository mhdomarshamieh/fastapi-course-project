from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserPostIn(BaseModel):
    body: str


class UserPost(UserPostIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    image_url: Optional[str] = None


class UserPostWithLikes(UserPost):
    likes: int
    model_config = ConfigDict(from_attributes=True)


class CommentIn(BaseModel):
    post_id: int
    body: str


class Comment(CommentIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int


class UserPostWithComments(BaseModel):
    post: UserPostWithLikes
    comments: list[Comment]


class PostLikeIn(BaseModel):
    post_id: int


class PostLike(PostLikeIn):
    id: int
    user_id: int
