from datetime import datetime, timedelta
from os import getenv as env
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext


# to get a string like this run:
# openssl rand -hex 32
JWT_SECRET = env("JWT_SECRET")
ALGORITHM = env("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(env("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=True)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_with_password(hashed_password: str, plain_password: str):
    is_authenticated = pwd_context.verify(plain_password, hashed_password)
    return is_authenticated


def generate_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_with_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except:
        return None
