import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column()
    
    # Relationships
    medications: Mapped[list["Medication"]] = relationship(back_populates="owner")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="owner")

class Medication(Base):
    __tablename__ = "medications"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    dosage: Mapped[str] = mapped_column()
    # Adding frequency so VedaCore can save it
    frequency: Mapped[str] = mapped_column(nullable=True) 
    current_stock: Mapped[int] = mapped_column(default=0)
    refill_threshold: Mapped[int] = mapped_column(default=5)
    
    # Link to User
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped["User"] = relationship(back_populates="medications")

class ChatMessage(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column()  # 'user' or 'model'
    content: Mapped[str] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Link to User (CRITICAL for privacy)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    owner: Mapped["User"] = relationship(back_populates="messages")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session