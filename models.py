from sqlalchemy import Column,Integer,String , Text, ForeignKey 
from db import Base 

#SQLAlchemy mein hum is class ko database table ka model/blueprint banane ke liye use kar rahe hain.
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True)
    password = Column(String(100))


class Reports(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_text = Column(Text)
    result = Column(Text)
