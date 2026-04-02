from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import schemas, models
from ..database import get_db
from typing import List
from ..services.ai_agent import generate_quiz, replan_roadmap, analyze_performance
from datetime import datetime, timedelta

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("/", response_model=List[schemas.Task])
def get_tasks(goal_id: int = None, db: Session = Depends(get_db)):
    query = db.query(models.Task)
    if goal_id:
        query = query.filter(models.Task.goal_id == goal_id)
    tasks = query.order_by(models.Task.day_number).all()
    for task in tasks:
        # Check if a quiz result exists and has been completed (score > 0)
        task.has_quiz = task.quiz is not None
    return tasks

@router.put("/{task_id}", response_model=schemas.Task)
def update_task_status(task_id: int, is_completed: bool, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_completed = is_completed
    
    # Update Streak Logic
    user = task.goal.user
    if is_completed:
        now = datetime.utcnow()
        today = now.date()
        if user.last_active_date:
            last_active = user.last_active_date.date()
            if last_active == today:
                pass # Already active today
            elif last_active == today - timedelta(days=1):
                user.streak = (user.streak or 0) + 1
            else:
                user.streak = 1
        else:
            user.streak = 1
        user.last_active_date = now
    
    db.commit()
    db.refresh(task)
    task.has_quiz = task.quiz is not None
    return task

def _apply_full_replan(goal_id: int, new_plan: list, db: Session, min_day: int):
    # This helper replaces ONLY future INCOMPLETE tasks with the new plan from the AI
    # This prevents the "erasing" issue of past history (skipped or done)
    remaining_tasks = db.query(models.Task).filter(
        models.Task.goal_id == goal_id,
        models.Task.is_completed == False,
        models.Task.day_number > min_day
    ).all()
    
    for t in remaining_tasks:
        db.delete(t)
    
    # Sort new plan by day number just in case
    new_plan.sort(key=lambda x: x.get("day_number", 0))
    
    for p in new_plan:
        db_task = models.Task(
            goal_id=goal_id,
            day_number=p["day_number"],
            topic=p["topic"],
            description=p["description"]
        )
        db.add(db_task)
    db.commit()

@router.post("/{task_id}/quiz")
def submit_quiz(task_id: int, quiz_sub: schemas.QuizSubmission, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # AI Analysis for Weak Topics
    weak_areas = quiz_sub.weak_areas
    if quiz_sub.score < 1.0 and quiz_sub.missed_questions:
        from ..services.ai_agent import identify_weak_topics
        missed_data = []
        for i in range(len(quiz_sub.missed_questions)):
            missed_data.append({
                "q": quiz_sub.missed_questions[i],
                "user_ans": quiz_sub.user_answers[i] if i < len(quiz_sub.user_answers) else "No answer"
            })
        
        ai_weak_topics = identify_weak_topics(task.topic, task.description, missed_data)
        if ai_weak_topics:
            weak_areas = ai_weak_topics

    # Check if a result already exists
    existing_res = db.query(models.QuizResult).filter(models.QuizResult.task_id == task.id).first()

    if existing_res:
        existing_res.goal_id = task.goal_id
        existing_res.score = quiz_sub.score
        existing_res.total_questions = quiz_sub.total_questions
        existing_res.weak_areas = weak_areas
        quiz_res = existing_res
    else:
        quiz_res = models.QuizResult(
            task_id=task.id,
            goal_id=task.goal_id,
            score=quiz_sub.score,
            total_questions=quiz_sub.total_questions,
            weak_areas=weak_areas
        )
        db.add(quiz_res)
    
    # Mark task as completed so it's NOT deleted during replan
    task.is_completed = True
    db.flush() # Sync state before potential replan
    
    # AGENTIC ACTION: Trigger Replanning if score is low
    if quiz_sub.score < 0.6:
        goal = task.goal
        remaining_tasks = db.query(models.Task).filter(
            models.Task.goal_id == goal.id,
            models.Task.day_number > task.day_number,
            models.Task.is_completed == False
        ).order_by(models.Task.day_number).all()
        
        if remaining_tasks:
            tasks_data = [{"day_number": t.day_number, "topic": t.topic, "description": t.description} for t in remaining_tasks]
            new_plan = replan_roadmap(
                goal_title=goal.title,
                remaining_days=tasks_data,
                weak_topics=[quiz_sub.weak_areas],
                reason=f"Student struggled with {task.topic} (Score: {quiz_sub.score*100}%)"
            )
            if new_plan:
                # pass task.day_number to protect the past
                _apply_full_replan(goal.id, new_plan, db, task.day_number)
    
    db.commit()
    return {"message": "Quiz submitted successfully", "replanned": quiz_sub.score < 0.6}

@router.get("/{task_id}/quiz/generate")
def generate_task_quiz(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    print(f"Generating quiz for Task {task_id}: {task.topic}")
    quiz_data = generate_quiz(topic=task.topic, description=task.description)
    
    if not quiz_data:
        raise HTTPException(
            status_code=503,
            detail="AI Mentor is currently busy or unavailable. Please try again in 30 seconds."
        )
        
    return quiz_data

@router.post("/check_delays/{goal_id}")
def check_goal_delays(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Calculate expected day based on creation date
    days_since_start = (datetime.utcnow() - goal.created_at).days + 1
    
    # Find incomplete tasks that should have been done by now
    overdue_tasks = db.query(models.Task).filter(
        models.Task.goal_id == goal.id,
        models.Task.day_number < days_since_start,
        models.Task.is_completed == False
    ).all()
    
    if overdue_tasks:
        # Trigger replan for remaining tasks
        all_remaining = db.query(models.Task).filter(
            models.Task.goal_id == goal.id,
            models.Task.is_completed == False
        ).order_by(models.Task.day_number).all()
        
        tasks_data = [{"day_number": t.day_number, "topic": t.topic, "description": t.description} for t in all_remaining]
        new_plan = replan_roadmap(
            goal_title=goal.title,
            remaining_days=tasks_data,
            weak_topics=[],
            reason=f"Student missed deadlines. Current Day: {days_since_start}."
        )
        
        if new_plan:
            _apply_full_replan(goal.id, new_plan, db, days_since_start - 1)
            return {"message": "Roadmap adjusted because tasks were missed.", "adjusted": True}
            
    return {"message": "No delays found.", "adjusted": False}

@router.get("/performance/{goal_id}")
def get_goal_performance(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=401, detail="Goal not found")
    
    # Get all quiz results associated with this GOAL directly
    all_results = db.query(models.QuizResult).filter(models.QuizResult.goal_id == goal_id).all()
    all_tasks = db.query(models.Task).filter(models.Task.goal_id == goal_id).all()
            
    # Calculate expected day based on creation date
    days_since_start = (datetime.utcnow() - goal.created_at).days + 1
    
    # Use AI agent service to analyze performance
    performance_data = analyze_performance(all_results, all_tasks, days_since_start)
    return performance_data

@router.post("/replan_manual/{goal_id}")
def manual_replan(goal_id: int, topic: str, db: Session = Depends(get_db)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Find ALL incomplete tasks
    remaining_tasks = db.query(models.Task).filter(
        models.Task.goal_id == goal_id,
        models.Task.is_completed == False
    ).order_by(models.Task.day_number).all()
    
    if not remaining_tasks:
        return {"message": "All tasks completed. Nothing to replan."}

    tasks_data = [{"day_number": t.day_number, "topic": t.topic, "description": t.description} for t in remaining_tasks]
    
    new_plan = replan_roadmap(
        goal_title=goal.title,
        remaining_days=tasks_data,
        weak_topics=[topic],
        reason=f"Learning correction for: {topic}"
    )
    
    if new_plan:
        # For manual replan, we use the day number just BEFORE the first replacement day
        min_day = min([p["day_number"] for p in new_plan]) - 1 if new_plan else 0
        _apply_full_replan(goal_id, new_plan, db, min_day)
        return {"message": "Roadmap successfully adjusted based on your needs.", "success": True}
    
    return {"message": "Replan failed.", "success": False}

import threading
import time
import urllib.request
import urllib.parse
from ..database import SessionLocal
import os

def send_instant_notification(task_topic, goal_title):
    p_token = os.getenv("PUSHOVER_API_TOKEN")
    p_user = os.getenv("PUSHOVER_USER_KEY")
    if not p_token or not p_user:
        return
    
    try:
        data = urllib.parse.urlencode({
            "token": p_token,
            "user": p_user,
            "message": f"⏰ DevMentor Reminder: Time to study '{task_topic}' for your goal: {goal_title}",
            "title": "Study Reminder",
            "priority": 1
        }).encode("utf-8")
        req = urllib.request.Request("https://api.pushover.net/1/messages.json", data=data)
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"ERROR: Instant notification failed: {e}")

@router.put("/{task_id}/reminder")
def set_task_reminder(task_id: int, reminder_data: schemas.TaskReminderUpdate, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.reminder_time = reminder_data.reminder_time
    task.reminder_sent = False # Reset if updated
    db.commit()
    
    # AGENTIC ACTION: As requested, take help from the threading logic
    # Start a background thread to send the notification immediately if the time is near
    if task.reminder_time:
        delay = (task.reminder_time - datetime.now()).total_seconds()
        if 0 < delay < 3600: # Only start threads for reminders within experimental range (1 hour)
            def delayed_task():
                time.sleep(delay)
                # Re-verify task is still active and not sent
                new_db = SessionLocal()
                try:
                    t = new_db.query(models.Task).filter(models.Task.id == task_id).first()
                    if t and not t.is_completed and not t.reminder_sent:
                        send_instant_notification(t.topic, t.goal.title if t.goal else "Your Goal")
                        t.reminder_sent = True
                        new_db.commit()
                finally:
                    new_db.close()
            
            threading.Thread(target=delayed_task, daemon=True).start()
            print(f"LOG: Scheduled instant thread for Task {task_id} in {delay}s")

    return {"message": f"Reminder set for {task.reminder_time}"}
