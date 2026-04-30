import os
from datetime import datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, create_engine, text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/skillhub.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    versions = relationship("Version", back_populates="package", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="package", cascade="all, delete-orphan")


class Version(Base):
    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    version = Column(String, nullable=False)
    message = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    contents = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    package = relationship("Package", back_populates="versions")
    __table_args__ = (UniqueConstraint("package_id", "version"),)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=False)
    tag_name = Column(String, nullable=False)

    package = relationship("Package", back_populates="tags")
    __table_args__ = (UniqueConstraint("package_id", "tag_name"),)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(versions)"))]
        if "contents" not in cols:
            conn.execute(text("ALTER TABLE versions ADD COLUMN contents TEXT"))
            conn.commit()
