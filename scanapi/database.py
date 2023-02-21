# this file contains information about the database connection
# in essence the database engine
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


engine = create_engine("sqlite:///./databases/shortener.db", connect_args={"check_same_thread": False})
# check_same_thread:False allows you to make more than one request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
