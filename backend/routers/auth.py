from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .. import schemas, models
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

@router.post("/signup", response_model=schemas.UserAuthResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter((models.User.email == user.email) | (models.User.username == user.username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_pwd = get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return schemas.UserAuthResponse(user_id=new_user.id, username=new_user.username, email=new_user.email)

@router.post("/login", response_model=schemas.UserAuthResponse)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    if not db_user:
        raise HTTPException(status_code=403, detail="Invalid Credentials")
        
    if not verify_password(user_credentials.password, db_user.hashed_password):
        raise HTTPException(status_code=403, detail="Invalid Credentials")
        
    return schemas.UserAuthResponse(user_id=db_user.id, username=db_user.username, email=db_user.email)
