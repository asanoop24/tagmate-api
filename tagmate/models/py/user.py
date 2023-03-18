from pydantic import BaseModel
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise import Tortoise
import uuid

from tagmate.models.db.user import User as UserTable

# Tortoise.init_models(["tagmate.models.db.user", "tagmate.models.db.activity"], "models")
User = pydantic_model_creator(UserTable)


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