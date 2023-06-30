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


# problem line/function does not like coroutine, accepts binary data instead

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


@app.post("/endpoint/", response_model=schemas.EndPoint)
def create_file_code(endpoint: schemas.EndPointCreate, db: Session = Depends(get_db)):
    # validate url
    if not validators.url(endpoint.url):
        raise HTTPException(detail="file endpoint does not exist", status_code=status.HTTP_404_NOT_FOUND)

    # check if name of file already exists
    ed_get = db.query(models.FileModel).filter(models.FileModel.name == endpoint.name).first()

    # if file doesn't exist

    if not ed_get:
        # generate qr_code data
        code_data = generate_qr_code(endpoint.url)

        ed_get = models.FileModel(name=endpoint.name, qr_code=code_data,
                                  url=endpoint.url, password=get_password_hash(endpoint.password))

        # commit changes to database
        db.add(ed_get)
        db.commit()
        db.refresh(ed_get)

        return endpoint

    else:
        raise HTTPException(detail="file already exists", status_code=status.HTTP_409_CONFLICT)

# learn how to use passwords and dependencies


@app.get('/endpoints/{ed_name}')
def return_file_code(ed_name: str,
                     form_data: schemas.PasswordForm = Depends(),
                     db: Session = Depends(get_db)):
    ed_get = db.query(models.FileModel).filter(models.FileModel.name == ed_name).first()
    # check if endpoint does not exist raise error if so
    if not ed_get:
        raise HTTPException(detail=f'{ed_name} does not exist', status_code=404)
    # check if file already exists
    #####
    #####
    #
    # check if the password is correct4
    # problem line of code
    if not verify_password(form_data.password, ed_get.password):
        raise HTTPException(status_code=400, detail='Invalid Password')

    qr_code = ed_get.qr_code

    return Response(content=qr_code, media_type='image/png')


# to allow databases to be read directly like this add orm_mode = True under class config in schemas
@app.get('/endpoints/', response_model=list[schemas.EndPoint])
def return_files(skip: int, limit: int, db: Session = Depends(get_db)):
    return db.query(models.FileModel).offset(skip).limit(limit).all()


@app.patch('/endpoint/{ed_name}', response_model=schemas.EndPoint)
async def update_file(ed_name: str, endpoint: schemas.EndpointUpdate, db: Session = Depends(get_db)):
    # find the stored file
    stored_ed = db.query(models.FileModel).filter(models.FileModel.name == ed_name).first()

    if stored_ed:  # if the endpoint is found
        stored_data_to_update = schemas.EndpointUpdate(name=stored_ed.name, url=stored_ed.url,
                                                       password=stored_ed.password)  # check the docs
        update_data = endpoint.dict(exclude_unset=True)
        updated_data = stored_data_to_update.copy(update=update_data)

        stored_ed.name = updated_data.name
        stored_ed.url = updated_data.url
        stored_ed.password = get_password_hash(updated_data.password)

        # update the database
        db.commit()
        db.refresh(stored_ed)

        return updated_data


# for deletion of selected database element
@app.delete('/endpoints/{ed_name}', response_model=schemas.EndPointBase)
async def delete_file(ed_name: str, form_data: schemas.PasswordForm = Depends(), db: Session = Depends(get_db)):
    # find stored file
    stored_ed = db.query(models.FileModel).filter(models.FileModel.name == ed_name).first()
    info_dict = {'name':  stored_ed.name, 'password':stored_ed.password, "url":stored_ed.url}
    # request password, if true:

    if not verify_password(form_data.password,stored_ed.password):
        raise HTTPException(detail="file endpoint does not exist", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    db.delete(stored_ed)
    db.commit()

    # return information about the item deleted
    # find a way to make this jsonable
    return jsonable_encoder(info_dict)


# raise a better request validation error for user requests
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # log the request body into the error
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({'detail': exc.errors(), 'body': exc.body})
    )
