from tortoise import exceptions as TortoiseExceptions

from tagmate.exceptions import activity as ActivityExceptions
from tagmate.exceptions import auth as AuthExceptions
from tagmate.models.db.activity import Activity as ActivityTable
from tagmate.models.db.user import User as UserTable
from tagmate.models.py.activity import Activity
from tagmate.models.py.user import User


async def validate_user_exists(email: str) -> User:
    """checks if the user exists in the database

    Args:
        email (str): email of the user

    Raises:
        AuthExceptions.InvalidUsername: username/email does not exist in the database

    Returns:
        User: user details
    """

    try:
        user = await UserTable.get(email=email)
        return user
    except TortoiseExceptions.DoesNotExist:
        raise AuthExceptions.InvalidUsername()


async def validate_activity_exists(user_id: str, activity_id: str) -> Activity:
    """checks if the given activity exists for the given user

    Args:
        user_id (str): uuid of the user
        activity_id (str): uuid of the activity

    Raises:
        ActivityExceptions.ActivityDoesNotExist: activity does not exist for the given user

    Returns:
        Activity: activity details
    """
    try:
        activity = await ActivityTable.get(user_id=user_id, id=activity_id)
        return activity
    except TortoiseExceptions.DoesNotExist as exc:
        raise ActivityExceptions.ActivityDoesNotExist(exception=exc)
