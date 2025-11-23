from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import UserCreate, UserLogin, Token
from security import create_access_token, verify_password, get_password_hash
from database import get_db
from models import User
from sqlalchemy.future import select

app = FastAPI(
    docs_url="/auth/docs",
    openapi_url="/auth/openapi.json"
)

@app.post("/register/")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    stmt = select(User).filter(User.username == user.username)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    
    db.add(new_user)
    await db.commit()
    
    return {"msg": "User created successfully"}

@app.post("/login/", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    stmt = select(User).filter(User.username == user.username)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}
