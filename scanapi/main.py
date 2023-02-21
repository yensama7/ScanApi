from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
import qrcode
from io import BytesIO
from . import schemas, models
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from passlib.context import CryptContext
import validators

app = FastAPI()

models.Base.metadata.create_all(bind=engine)


# create dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# problem line/function does not like coroutine, accepts binarydata instead

# code to generate qr_code
def generate_qr_code(link):
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )
    qr.add_data(link)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')

    with BytesIO() as file:
        img.save(file, 'PNG')
        file.seek(0)
        binary_data = file.read()
    return binary_data


# code for generation and validation of password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)



def get_password_hash(password):
    return pwd_context.hash(password)


@app.get("/")
def home():
    return "File Sharing service"


@app.post("/file/", response_model=schemas.File)
def create_file_code(file: schemas.FileCreate, db: Session = Depends(get_db)):
    # validate url
    if not validators.url(file.url):
        raise HTTPException(detail="file endpoint does not exist")

    # check if name of file already exists
    file_get = db.query(models.FileModel).filter(models.FileModel.name == file.name).first()

    # if file doesn't exist

    if not file_get:
        # generate qr_code data
        code_data = generate_qr_code(file.url)

        file_get = models.FileModel(name=file.name, qr_code=code_data,
                                    url=file.url, password=get_password_hash(file.password))

        # commit changes to database
        db.add(file_get)
        db.commit()
        db.refresh(file_get)

    return file

# learn how to use passwords and dependecies


@app.get('/files/{file_name}')
def return_file_code(file_name: str,
                     form_data: schemas.PasswordForm = Depends(),
                     db: Session = Depends(get_db)):

    file_endpoint = db.query(models.FileModel).filter(models.FileModel.name == file_name).first()
    # check if endpoint does not exist raise error if so
    if not file_endpoint:
        raise HTTPException(detail=f'{file_name} does not exist', status_code=404)
    # check if file already exists
    #####
    #####
    #
    # check if the password is correct4
    # problem line of code
    if not verify_password(form_data.password, file_endpoint.password):
        raise HTTPException(status_code=400, detail='Invalid Password')

    qr_code = file_endpoint.qr_code

    return Response(content=qr_code, media_type='image/png')


# to allow databases to be read directly like this add orm_mode = True under class config in schemas
@app.get('/files/', response_model=list[schemas.File])
def return_files(skip: int, limit: int, db: Session = Depends(get_db)):
    return db.query(models.FileModel).offset(skip).limit(limit).all()


@app.patch('/file/{file_name}')
async def update_file(file_name: str, file: schemas.FileUpdate, db: Session = Depends(get_db)):

    # find the stored file
    stored_file = db.query(models.FileModel).filter(models.FileModel.name == file_name).first()

    # have to change this to make the code better later though, will give problems
    stored_file_dict = {
        'name': stored_file.name,
        'url': stored_file.url,
        'password': get_password_hash(stored_file.password)
    }

    stored_file_model = schemas.FileUpdate(**stored_file_dict)
    update_data = file.dict(exclude_unset=True)
    updated_file = stored_file_model.copy(update=update_data)


# raise a better request validation error for user requests
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # log the request body into the error
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({'detail': exc.errors(), 'body': exc.body})
    )


