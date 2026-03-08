import os
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import init_db, get_db, ChatMessage, Medication, User, AsyncSessionLocal
from auth import create_access_token, verify_password, get_current_user, hash_password

load_dotenv()
app = FastAPI(title="Veda AI Backend")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("veda_production")

# --- Schemas ---
class MedicationExtraction(BaseModel):
    name: str
    dosage: str
    total_stock: int

# --- Scheduler ---
scheduler = AsyncIOScheduler()

async def check_medication_reminders():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Medication).where(Medication.current_stock <= 5)
        )
        low_stock_meds = result.scalars().all()
        for med in low_stock_meds:
            logger.warning(f"ALERT: User {med.user_id} is low on {med.name}!")

@app.on_event("startup")
async def startup_event():
    await init_db()
    if not scheduler.running:
        scheduler.add_job(check_medication_reminders, 'interval', minutes=60)
        scheduler.start()

@app.post("/signup")
async def signup(username: str, password: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.exc import IntegrityError
    try:
        new_user = User(username=username, hashed_password=hash_password(password))
        db.add(new_user)
        await db.commit()
        return {"message": "User created successfully."}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Username already exists.")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/veda-core/extract")
async def extract_medication(
    text: str, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        # We call Gemini directly here to avoid "ModuleNotFoundError"
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Extract medication info from this text: {text}",
            config={
                'response_mime_type': 'application/json',
                'response_schema': MedicationExtraction,
            }
        )
        data = response.parsed

        new_med = Medication(
            user_id=current_user.id,
            name=data.name,
            dosage=data.dosage,
            current_stock=data.total_stock,
            total_stock=data.total_stock
        )
        
        db.add(new_med)
        await db.commit()
        await db.refresh(new_med)
        
        return {"status": "success", "data": data}
    except Exception as e:
        await db.rollback()
        logger.error(f"Extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/my-meds")
async def get_user_meds(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Medication).where(Medication.user_id == current_user.id))
    return result.scalars().all()

@app.post("/meds/{med_id}/take")
async def take_medication(med_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Medication).where(Medication.id == med_id, Medication.user_id == current_user.id))
    med = result.scalar_one_or_none()
    
    if not med:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    med.current_stock -= 1
    await db.commit()
    return {"status": "success", "remaining": med.current_stock}