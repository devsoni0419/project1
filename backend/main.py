from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine, SessionLocal
from .routers import goals, tasks, assistant, auth
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")

async def check_reminders():
    print("LOG [Reminders]: Background check loop started.")
    while True:
        db = None
        try:
            db = SessionLocal()
            now = datetime.now()
            
            # Find tasks where reminder_time is in the past and not yet sent
            pending_tasks = db.query(models.Task).filter(
                models.Task.is_completed == False,
                models.Task.reminder_sent == False,
                models.Task.reminder_time != None,
                models.Task.reminder_time <= now
            ).all()

            if pending_tasks:
                print(f"LOG [Reminders]: Found {len(pending_tasks)} pending study reminders to process (Current UTC: {now}).")
                
            for t in pending_tasks:
                # Refresh keys in case they changed in .env
                p_token = os.getenv("PUSHOVER_API_TOKEN")
                p_user = os.getenv("PUSHOVER_USER_KEY")
                
                if not p_token or not p_user:
                    print(f"ERROR [Reminders]: Pushover keys missing in environment! Cannot send reminder for task {t.id}.")
                    continue
                
                goal_title = t.goal.title if t.goal else "Your Learning Goal"
                
                try:
                    print(f"LOG [Reminders]: Sending notification for Task {t.id} ('{t.topic}') at {t.reminder_time}")
                    message_body = f"⏰ DevMentor Reminder: Time to study '{t.topic}' for your goal: {goal_title}"
                    
                    data = urllib.parse.urlencode({
                        "token": p_token,
                        "user": p_user,
                        "message": message_body,
                        "title": "Study Reminder",
                        "priority": 1
                    }).encode("utf-8")
                    
                    req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
                    urllib.request.urlopen(req)
                    
                    t.reminder_sent = True
                    db.commit()
                    print(f"SUCCESS [Reminders]: Notification sent for Task {t.id}.")
                except Exception as e:
                    print(f"ERROR [Reminders]: Pushover API failure for task {t.id}: {e}")
                    db.rollback() # Ensure one failure doesn't block the loop
        except Exception as e:
            print(f"ERROR [Reminders]: Database or Loop error: {e}")
        finally:
            if db:
                db.close()
        await asyncio.sleep(20) # Check every 20 seconds for better precision

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DevMentorAI API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_reminders())

# Configure CORS so the frontend can easily communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(goals.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(assistant.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to DevMentorAI Backend Service!"}
