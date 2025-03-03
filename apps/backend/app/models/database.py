from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# 然后在其他模型文件中从这里导入 Base:
# from app.models.database import Base 