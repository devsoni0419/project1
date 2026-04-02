from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .. import schemas, models
from ..database import get_db
from ..services.ai_agent import generate_learning_plan
from typing import List, Optional

router = APIRouter(prefix="/goals", tags=["Goals"])

@router.post("/", response_model=schemas.Goal)
def create_goal(goal: schemas.GoalCreate, x_user_id: int = Header(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_goal = models.Goal(
        user_id=user.id,
        title=goal.title,
        daily_study_hours=goal.daily_study_hours
    )
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)

    # Automatically generate tasks with AI
    ai_res = generate_learning_plan(goal.title, goal.daily_study_hours)
    if not ai_res:
        raise HTTPException(
            status_code=503, 
            detail="AI Mentor is currently busy or unavailable. Please try again in 30 seconds."
        )

    # Update title with corrected version
    db_goal.title = ai_res["corrected_title"]
    
    for p in ai_res["tasks"]:
        db_task = models.Task(
            goal_id=db_goal.id,
            day_number=p["day_number"],
            topic=p["topic"],
            description=p["description"]
        )
        db.add(db_task)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.post("/{goal_id}/regenerate")
def regenerate_roadmap(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    # Generate new plan BEFORE touching the database (this takes seconds)
    ai_res = generate_learning_plan(db_goal.title, db_goal.daily_study_hours)
    
    if not ai_res:
        raise HTTPException(
            status_code=503, 
            detail="AI Mentor is currently busy or unavailable. Please try again in 30 seconds."
        )

    # Rapid DB operation starts here
    db.query(models.Task).filter(models.Task.goal_id == goal_id).delete()
    
    # Update title with corrected version
    db_goal.title = ai_res["corrected_title"]
    
    for p in ai_res["tasks"]:
        db_task = models.Task(
            goal_id=db_goal.id,
            day_number=p["day_number"],
            topic=p["topic"],
            description=p["description"]
        )
        db.add(db_task)
    db.commit()
    return {"message": "Roadmap regenerated successfully", "corrected_title": ai_res["corrected_title"]}

@router.get("/", response_model=List[schemas.Goal])
def read_goals(x_user_id: Optional[int] = Header(None), skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Goal)
    if x_user_id:
        query = query.filter(models.Goal.user_id == x_user_id)
    goals = query.offset(skip).limit(limit).all()
    return goals

@router.delete("/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    db.delete(db_goal)
    db.commit()
    return {"message": "Goal deleted successfully"}
