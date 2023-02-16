from fastapi import HTTPException, status


class ActivityDoesNotExist(HTTPException):
    def __init__(
        self,
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No activity exists for this user",
    ):
        super().__init__(status_code=status_code, detail=detail)


class ActivityAlreadyExists(HTTPException):
    def __init__(
        self,
        status_code=status.HTTP_409_CONFLICT,
        detail="An activity already exists by this name",
    ):
        super().__init__(status_code=status_code, detail=detail)


class FileUploadError(HTTPException):
    def __init__(
        self,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not upload file to storage",
    ):
        super().__init__(status_code=status_code, detail=detail)


class FileDownloadError(HTTPException):
    def __init__(
        self,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not download file from storage",
    ):
        super().__init__(status_code=status_code, detail=detail)
