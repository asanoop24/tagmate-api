from fastapi import HTTPException, status


class UserAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="username already exists")


class InvalidUsername(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid username")


class InvalidPassword(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid password")


class InvalidToken(HTTPException):
    def __init__(self):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token", headers={"WWW-Authenticate": "Bearer"})
