from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, Boolean, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    polls = relationship("Poll", back_populates="author", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="user", cascade="all, delete-orphan")

class Poll(Base):
    __tablename__ = "polls"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True)
    is_test = Column(Boolean, default=False)
    
    time_limit = Column(Integer, nullable=True) # <--- Время в минутах
    allow_retake = Column(Boolean, default=False) # <--- Разрешить перепрохождение
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    author = relationship("User", back_populates="polls")
    questions = relationship("Question", back_populates="poll", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(200), nullable=False)
    question_type = Column(String(20), default="single")
    
    poll = relationship("Poll", back_populates="questions")
    options = relationship("Option", back_populates="question", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="question", cascade="all, delete-orphan")

class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(200), nullable=False)
    is_correct = Column(Boolean, default=False)
    
    question = relationship("Question", back_populates="options")
    votes = relationship("Vote", back_populates="option", cascade="all, delete-orphan")

class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    option_id = Column(Integer, ForeignKey("options.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint("question_id", "option_id", "user_id", name="uq_one_vote_per_option"),)
    
    question = relationship("Question", back_populates="votes")
    option = relationship("Option", back_populates="votes")
    user = relationship("User", back_populates="votes")