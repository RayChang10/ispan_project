#!/usr/bin/env python3
"""
標準 SQLAlchemy 資料層
- 提供 Engine、SessionLocal、Base
- 定義 User / WorkExperience / Skill / InterviewSession 四個 ORM 模型
"""

from __future__ import annotations

from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)

import os
from sqlalchemy import text

# 延遲初始化資料庫連接
DATABASE_URL = None
engine = None
SessionLocal = None

def get_database_url() -> str:
    """獲取資料庫 URL，支援延遲初始化"""
    global DATABASE_URL
    if DATABASE_URL is None:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise RuntimeError(
                "未設定環境變數 DATABASE_URL。請提供 PostgreSQL 連線字串，例如 "
                "postgresql+psycopg://user:password@host:5432/dbname"
            )
    return DATABASE_URL

def get_engine():
    """獲取資料庫引擎，支援延遲初始化"""
    global engine
    if engine is None:
        engine = create_engine(get_database_url())
    return engine

def get_session_local():
    """獲取 SessionLocal，支援延遲初始化"""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return SessionLocal


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    desired_position: Mapped[str | None] = mapped_column(String(200))
    desired_field: Mapped[str | None] = mapped_column(String(100))
    desired_location: Mapped[str | None] = mapped_column(String(100))
    introduction: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[str | None] = mapped_column(Text)  # JSON string if any
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    work_experiences: Mapped[list[WorkExperience]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    skills: Mapped[list[Skill]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class WorkExperience(Base):
    __tablename__ = "work_experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry_type: Mapped[str | None] = mapped_column(String(100))
    work_location: Mapped[str | None] = mapped_column(String(100))
    position_title: Mapped[str | None] = mapped_column(String(200))
    position_category_1: Mapped[str | None] = mapped_column(String(100))
    position_category_2: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    job_description: Mapped[str | None] = mapped_column(Text)
    job_skills: Mapped[str | None] = mapped_column(Text)
    salary: Mapped[str | None] = mapped_column(String(100))
    salary_type: Mapped[str | None] = mapped_column(String(50))
    management_responsibility: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="work_experiences")


class Skill(Base):
    __tablename__ = "skill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="skills")


class InterviewSession(Base):
    __tablename__ = "interview_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_data: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    
def create_tables_safely() -> None:
    """
    使用 PostgreSQL advisory lock 避免多進程/多執行緒同時執行 create_all 造成競態。
    """
    with get_engine().connect() as conn:
        # 固定的 lock key（可任意選擇整數），同一個 DB 內需一致
        conn.execute(text("SELECT pg_advisory_lock(987654321)"))
        try:
            Base.metadata.create_all(bind=conn)
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(987654321)"))