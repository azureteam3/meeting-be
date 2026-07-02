from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session):
    return db.query(User).all()

def create_user(db: Session, user_in: UserCreate):
    db_user = User(name=user_in.name, email=user_in.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user