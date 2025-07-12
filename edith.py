from fastapi import FastAPI, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from typing import List
import speech_recognition as sr
import google.generativeai as genai
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uvicorn
from starlette.middleware.cors import CORSMiddleware

# ---------- Database Setup ----------
engine = create_engine("mysql+mysqlconnector://root:karan3613@localhost/edith")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------- Database Models ----------
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True , autoincrement= True)
    alert = Column(String(255), nullable=False)
    date = Column(String(255), default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    time = Column(String(255), default=lambda: datetime.utcnow().strftime("%H:%M:%S"))

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True , autoincrement= True)
    person = Column(String(255), nullable=False)
    conversation = Column(String(255))
    summary = Column(String(255))
    date = Column(String(255), default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    time = Column(String(255), default=lambda: datetime.utcnow().strftime("%H:%M:%S"))

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True , autoincrement= True)
    note = Column(String(255), nullable=False)
    date = Column(String(255), default=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    time = Column(String(255) , default=lambda: datetime.utcnow().strftime("%H:%M:%S"))

Base.metadata.create_all(bind=engine)

# ---------- FastAPI Setup ----------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Dependencies ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- Pydantic Schemas ----------
class AlertRequest(BaseModel):
    alert: str

class AlertResponse(AlertRequest):
    id: int
    date: str
    time: str

class ConversationRequest(BaseModel):
    person_name: str

class ConversationResponse(BaseModel):
    id: int
    person: str
    conversation: str
    summary: str
    date: str
    time: str

class NoteCreate(BaseModel):
    note: str

class NoteRead(BaseModel):
    id: int
    note: str
    date: str
    time: str

class Config:
    orm_mode = True

# ---------- Routes: Alerts ----------
@app.post("/alert", response_model=AlertResponse)
async def create_alert(request: AlertRequest, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    alert = Alert(
        alert=request.alert,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S")
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

@app.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).all()

# ---------- Routes: Conversations ----------
genai.configure(api_key="")  # Replace with your actual key

@app.post("/conversation", response_model=ConversationResponse)
async def record_and_save_conversation(request: ConversationRequest, db: Session = Depends(get_db)):
    conversation_text = record_conversation(duration=request.duration)
    summary = summarize_with_gemini(conversation_text)
    now = datetime.utcnow()
    conversation = Conversation(
        person=request.person_name,
        conversation=conversation_text,
        summary=summary,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S")
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

@app.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(db: Session = Depends(get_db)):
    return db.query(Conversation).all()

def record_conversation(duration=30):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.record(source, duration=duration)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""

def summarize_with_gemini(text):
    if not text:
        return "No transcript to summarize."
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(f"Summarize this conversation:\n\n{text}")
    return response.text.strip()

# ---------- Routes: Notes ----------
@app.post("/note", response_model=NoteRead)
async def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    db_note = Note(
        note=note.note,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S")
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

@app.get("/notes", response_model=List[NoteRead])
async def get_notes(db: Session = Depends(get_db)):
    return db.query(Note).all()

def recognize_real_time(db: Session = Depends(get_db)):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening for 7-8 seconds... Speak now!")
        audio = recognizer.listen(source, phrase_time_limit=7)
    print("Processing...")
    try:
        text = recognizer.recognize_google(audio)
        now = datetime.utcnow()
        db_note = Note(
            note= text,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S")
        )
        db.add(db_note)
        db.commit()
        db.refresh(db_note)
        return db_note
        print("You said:", text)
    except sr.UnknownValueError:
        print("Could not understand audio.")
    except sr.RequestError as e:
        print(f"Could not request results; {e}")


@app.post("/quick_note")
async def start_recognition(background_tasks: BackgroundTasks):
    background_tasks.add_task(recognize_real_time)
    return {"message": "Speech recognition started in background."}

if __name__ == "__main__":
    uvicorn.run("edith:app", host="127.0.0.1", port=8000, reload=True)