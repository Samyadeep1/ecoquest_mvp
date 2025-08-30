from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pydantic import BaseModel
from pathlib import Path
import os

# -------------------
# CONFIG
# -------------------
SECRET_KEY = "ecoquestsecret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = "sqlite:///./ecoquest.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------
# MODELS
# -------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="student")
    points = Column(Integer, default=0)
    submissions = relationship("Submission", back_populates="owner")

class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    points = Column(Integer)
    submissions = relationship("Submission", back_populates="challenge")

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    proof_text = Column(String)
    status = Column(String, default="pending")
    user_id = Column(Integer, ForeignKey("users.id"))
    challenge_id = Column(Integer, ForeignKey("challenges.id"))
    owner = relationship("User", back_populates="submissions")
    challenge = relationship("Challenge", back_populates="submissions")

Base.metadata.create_all(bind=engine)

# Seed admin
def seed_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=pwd_context.hash("admin123"),
                role="admin",
                points=0,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()

seed_admin()

# -------------------
# SCHEMAS
# -------------------
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChallengeCreate(BaseModel):
    title: str
    description: str
    points: int

class SubmissionCreate(BaseModel):
    challenge_id: int
    proof_text: str

# -------------------
# APP
# -------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------
# Serve frontend
# -------------------
# Compute path from backend/main.py to repo root/frontend
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

if not STATIC_DIR.exists():
    raise RuntimeError(f"Static directory not found at {STATIC_DIR}")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=500, detail="index.html not found")
    return FileResponse(index_file)

# -------------------
# UTILS
# -------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# -------------------
# ROUTES
# -------------------
@app.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username taken")
    user = User(username=req.username, hashed_password=pwd_context.hash(req.password), role="student")
    db.add(user)
    db.commit()
    return {"msg": "User registered"}

@app.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not pwd_context.verify(req.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token({"sub": req.username}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
        "points": user.points,
    }

@app.get("/challenges")
def get_challenges(db: Session = Depends(get_db)):
    return [
        {"id": c.id, "title": c.title, "description": c.description, "points": c.points}
        for c in db.query(Challenge).all()
    ]

@app.post("/challenges")
def create_challenge(
    ch: ChallengeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create challenges")
    challenge = Challenge(title=ch.title, description=ch.description, points=ch.points)
    db.add(challenge)
    db.commit()
    return {"msg": "Challenge created"}

@app.post("/submissions")
def submit(
    sub: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    challenge = db.query(Challenge).filter(Challenge.id == sub.challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    submission = Submission(
        proof_text=sub.proof_text,
        user_id=current_user.id,
        challenge_id=sub.challenge_id,
        status="completed",
    )
    current_user.points += challenge.points
    db.add(submission)
    db.commit()
    return {"msg": f"Challenge completed! {challenge.points} points added."}

@app.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    return [
        {"username": u.username, "points": u.points, "role": u.role}
        for u in db.query(User).order_by(User.points.desc()).all()
    ]

# -------------------
# ENTRY
# -------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)
