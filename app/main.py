import os
import jwt  # This is from PyJWT
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
from openai import OpenAI
import secrets

from chroma_db import ChromaDBHandler

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

chroma_db_handler = ChromaDBHandler()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Integer, default=1)
    reset_token = Column(String, nullable=True)
    chat_history = relationship("ChatHistory", back_populates="user")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    framework = Column(String)
    question = Column(String)
    answer = Column(String)
    timestamp = Column(String, default=str(datetime.utcnow()))
    user = relationship("User", back_populates="chat_history")

Base.metadata.create_all(bind=engine)

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class QueryRequest(BaseModel):
    framework: str
    question: str

# Security & JWT config
SECRET_KEY = "supersecretkey"  # This should be kept safe
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", None))

# Initialize FastAPI app
app = FastAPI()

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions for authentication and hashing
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# User registration
@app.post("/register/", response_model=Token)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# User login
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# Forgot password
@app.post("/forgot-password/")
async def forgot_password(email: EmailStr, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email not found")

    # Generate a reset token
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    db.commit()

    # Send email (mocked)
    send_reset_email(email, reset_token)
    return {"msg": "Password reset link sent to email"}

# Reset password
@app.post("/reset-password/")
async def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Update password
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None  # Clear the reset token
    db.commit()
    return {"msg": "Password updated successfully"}

# Helper function to simulate sending a password reset email
def send_reset_email(email: str, reset_token: str):
    reset_link = f"http://localhost:8000/reset-password?token={reset_token}"
    print(f"Sending reset link to {email}: {reset_link}")

# Chatbot query endpoint with history logging
@app.post("/query")
async def query_docs(request: QueryRequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Authenticate the user
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == token_data.email).first()
    if not user:
        raise credentials_exception

    # Check if the requested framework exists (assuming `chroma_db_handler` is defined)
    retriever = chroma_db_handler.get_index(request.framework)
    if retriever is None:
        raise HTTPException(status_code=400, detail="Unsupported framework")

    # Retrieve relevant documents from ChromaDB
    docs = retriever.similarity_search(request.question, k=5)
    print(f"Found {len(docs)} for context.")
    context = "\n".join([doc.page_content for doc in docs])

    # Construct the messages for chat completion with retrieved context
    messages = [
        {"role": "system", "content": f"You are a helpful assistant for answering questions about the framework {request.framework}."},
        {"role": "assistant", "content": f"Context:\n{context}"},
        {"role": "user", "content": f"Question: {request.question}"}
    ]

    # Generate the final answer using OpenAI's 4o mini
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

    # Store the interaction in chat history, including the framework
    chat_history = ChatHistory(user_id=user.id, framework=request.framework, question=request.question, answer=answer)
    db.add(chat_history)
    db.commit()

    return {"answer": answer}


# View chat history for logged in user
@app.get("/history/")
async def get_chat_history(framework: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == token_data.email).first()
    if not user:
        raise credentials_exception

    # Filter the chat history by both user ID and framework
    history = db.query(ChatHistory).filter(ChatHistory.user_id == user.id, ChatHistory.framework == framework).order_by(ChatHistory.timestamp.desc()).all()

    return {
        "history": [
            {"question": h.question, "answer": h.answer, "timestamp": h.timestamp}
            for h in history
        ]
    }
