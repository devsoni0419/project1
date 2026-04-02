from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    streak = Column(Integer, default=0)
    last_active_date = Column(DateTime, nullable=True)
    
    goals = relationship("Goal", back_populates="user")

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)  # e.g. "Master DSA in 30 days"
    daily_study_hours = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")
    quiz_results = relationship("QuizResult", back_populates="goal", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    day_number = Column(Integer)
    topic = Column(String)
    description = Column(Text)
    is_completed = Column(Boolean, default=False)
    deadline = Column(DateTime, nullable=True)
    reminder_time = Column(DateTime, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    
    goal = relationship("Goal", back_populates="tasks")
    quiz = relationship("QuizResult", back_populates="task", uselist=False, cascade="all, delete-orphan")

class QuizResult(Base):
    __tablename__ = "quiz_results"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    score = Column(Float)
    total_questions = Column(Integer)
    weak_areas = Column(Text) # JSON string of weak topics
    
    task = relationship("Task", back_populates="quiz")
    goal = relationship("Goal", back_populates="quiz_results")
