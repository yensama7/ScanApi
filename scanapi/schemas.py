from pydantic import BaseModel, UUID1
from fastapi.param_functions import Form


class EndPointBase(BaseModel):
    name: str
    url: str

    class Config:
        orm_mode = True


class EndPointCreate(EndPointBase):
    password: str


# you can modify even the password. Addition functionality to be added requiring editor to be creator
class EndpointUpdate(EndPointCreate):
    pass


class EndPoint(EndPointBase):
    pass


# this will change, leave it like this for now
class PasswordForm(BaseModel):
    password: str = Form(default="")


