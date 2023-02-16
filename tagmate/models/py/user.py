from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator
import uuid

from tagmate.models.db import user


User = pydantic_model_creator(user.User)


class UserId(BaseModel):
    id: uuid.UUID


class UserEmail(BaseModel):
    email: str


class UserRegister(UserEmail):
    name: str = "Anoop"
    password: str
    is_admin: bool = False


class UserLogin(UserEmail):
    password: str


class UserToken(UserEmail):
    username: str
    access_token: str
    token_type: str = "bearer"