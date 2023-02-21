from pydantic import BaseModel, UUID1
from fastapi.param_functions import Form


class FileBase(BaseModel):
    name: str
    url: str

    class Config:
        orm_mode = True


class FileCreate(FileBase):
    password: str


# you can modify even the password. Addition functionality to be added requiring editor to be creator
class FileUpdate(FileCreate):
    pass


class File(FileBase):
    pass


# this will change, leave it like this for now
class PasswordForm(BaseModel):
    password: str = Form(default="")


