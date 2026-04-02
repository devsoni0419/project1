from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TaskBase(BaseModel):
    day_number: int
    topic: str
    description: str
    deadline: Optional[datetime] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    goal_id: int
    is_completed: bool
    reminder_time: Optional[datetime] = None
    has_quiz: bool = False
    
    class Config:
        from_attributes = True

class TaskReminderUpdate(BaseModel):
    reminder_time: Optional[datetime] = None

class GoalBase(BaseModel):
    title: str
    daily_study_hours: float

class GoalCreate(GoalBase):
    pass

class Goal(GoalBase):
    id: int
    user_id: int
    created_at: datetime
    tasks: List[Task] = []
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserAuthResponse(BaseModel):
    user_id: int
    username: str
    email: str

class User(UserBase):
    id: int
    streak: int
    goals: List[Goal] = []

    class Config:
        from_attributes = True

class QuizSubmission(BaseModel):
    task_id: int
    score: float
    total_questions: int
    weak_areas: str

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

class QuizGenerationResponse(BaseModel):
    questions: List[QuizQuestion]

class CodeAssistRequest(BaseModel):
    code: str = ""
    language: str = ""
    question: Optional[str] = ""
    action: str # "debug", "explain", "improve", "solve_doubt"
    context_text: Optional[str] = ""
