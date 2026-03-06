# import os
# import logging
# from datetime import datetime
# from typing import List, Optional

# from fastapi import FastAPI, Depends, HTTPException
# from fastapi.security import OAuth2PasswordRequestForm
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, update, delete
# from google import genai
# from dotenv import load_dotenv
# from pydantic import BaseModel, Field
# from apscheduler.schedulers.asyncio import AsyncIOScheduler

# # Import your database models and auth helpers
# from database import init_db, get_db, ChatMessage, Medication, User, AsyncSessionLocal
# from auth import create_access_token, verify_password, get_current_user

# load_dotenv()
# app = FastAPI()
# client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# # --- Logging Setup ---
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("veda_production")

# @app.middleware("http")
# async def log_requests(request, call_next):
#     logger.info(f"Path: {request.url.path} | Method: {request.method}")
#     return await call_next(request)

# # --- Constants & Schemas ---
# MEDICAL_INSTRUCTIONS = """
# You are Veda, a professional medical information assistant. 
# RULES:
# 1. ALWAYS include a disclaimer.
# 2. DO NOT give prescriptions.
# 3. Mention emergency services for chest pain/bleeding.
# 4. If not medical, politely decline.
# """

# class MedicalReport(BaseModel):
#     summary: str
#     detected_symptoms: List[str]
#     severity_guess: str

# class MedicationExtraction(BaseModel):
#     name: str = Field(description="Name of the medicine")
#     dosage: str = Field(description="Dosage (e.g. 500mg)")
#     total_stock: int = Field(description="Total pills provided in the refill")

# # --- Scheduler Setup ---
# scheduler = AsyncIOScheduler()

# async def check_medication_reminders():
#     # Use the specific session maker for background tasks
#     async with AsyncSessionLocal() as db:
#         result = await db.execute(
#             select(Medication).where(Medication.current_stock <= Medication.refill_threshold)
#         )
#         low_stock_meds = result.scalars().all()
#         for med in low_stock_meds:
#             logger.warning(f"ALERT: User {med.user_id} is low on {med.name}. Only {med.current_stock} left!")

# # --- Lifecycle Events ---
# @app.on_event("startup")
# async def startup_event():
#     await init_db()
#     scheduler.add_job(check_medication_reminders, 'interval', minutes=60)
#     scheduler.start()
#     logger.info("Veda Backend & Scheduler Started.")

# # --- Endpoints ---

# @app.get("/")
# async def root():
#     return {"message": "Veda is online with Docker Postgres memory!"}

# @app.get("/ask")
# async def ask_ai(question: str, db: AsyncSession = Depends(get_db)):
#     try:
#         # FIXED: Corrected the 'exefromcute' typo
#         result = await db.execute(
#             select(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(10)
#         )
#         past_msgs = result.scalars().all()
#         history = [{"role": m.role, "parts": [{"text": m.content}]} for m in reversed(past_msgs)]

#         response = client.models.generate_content(
#             model="gemini-2.5-flash",
#             config={'system_instruction': MEDICAL_INSTRUCTIONS},
#             contents=history + [{"role": "user", "parts": [{"text": question}]}]
#         )

#         db.add(ChatMessage(role="user", content=question))
#         db.add(ChatMessage(role="model", content=response.text))
#         await db.commit()

#         return {"veda_says": response.text}
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/token")
# async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
#     # FIXED: Added actual logic to find user and verify password
#     result = await db.execute(select(User).where(User.username == form_data.username))
#     user = result.scalar_one_or_none()
    
#     if not user or not verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(status_code=401, detail="Invalid username or password")
    
#     token = create_access_token(data={"sub": user.username})
#     return {"access_token": token, "token_type": "bearer"}

# # @app.post("/veda-core/extract")
# # async def extract_and_add_med(text: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
# #     response = client.models.generate_content(
# #         model="gemini-2.5-flash",
# #         contents=f"Extract medication from: {text}",
# #         config={
# #             'response_mime_type': 'application/json',
# #             'response_schema': MedicationExtraction,
# #         }
# #     )
# #     data = response.parsed
    
# #     # FIXED: Linked medication to the logged-in user
# #     new_med = Medication(
# #         name=data.name,
# #         dosage=data.dosage,
# #         current_stock=data.total_stock,
# #         user_id=current_user.id
# #     )
# #     db.add(new_med)
# #     await db.commit()
# #     return {"message": "Vault Updated", "data": data}

# @app.post("/veda-core/extract")
# async def extract_medication(
#     text: str, 
#     db: AsyncSession = Depends(get_db), 
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         # 1. Call your VedaCore extraction function
#         # Ensure 'extract_info' is imported from your veda_core.py
#         from veda_core import extract_info 
        
#         extracted_data = await extract_info(text)
        
#         if not extracted_data:
#             raise HTTPException(status_code=400, detail="Veda couldn't find med info in that text.")

#         # 2. Save to the database (The Vault)
#         from database import Medication
#         new_med = Medication(
#             user_id=current_user.id,
#             name=extracted_data["name"],
#             dosage=extracted_data["dosage"],
#             current_stock=extracted_data["total_stock"],
#             total_stock=extracted_data["total_stock"]
#         )
        
#         db.add(new_med)
#         await db.commit()
#         await db.refresh(new_med)
        
#         return {
#             "status": "success", 
#             "message": f"Added {new_med.name} to your vault.",
#             "data": extracted_data
#         }
#     except Exception as e:
#         await db.rollback()
#         # This will print the ACTUAL error to your terminal so we can see it
#         print(f"CRITICAL ERROR: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    

# # --- ADD THIS IF MISSING ---
# @app.post("/signup")
# async def signup(username: str, password: str, db: AsyncSession = Depends(get_db)):
#     from auth import hash_password # Ensure this is imported
#     from sqlalchemy.exc import IntegrityError
#     from database import User # Ensure this is imported

#     try:
#         new_user = User(username=username, hashed_password=hash_password(password))
#         db.add(new_user)
#         await db.commit()
#         return {"message": "User created successfully. Welcome to Veda!"}
#     except IntegrityError:
#         await db.rollback()
#         raise HTTPException(status_code=400, detail="Username already exists.")
    


# @app.post("/meds/{med_id}/take")
# async def take_medication(med_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
#     try:
#         # Atomic update logic
#         query = (
#             update(Medication)
#             .where(Medication.id == med_id, Medication.user_id == current_user.id)
#             .values(current_stock=Medication.current_stock - 1)
#             .returning(Medication.current_stock)
#         )
#         result = await db.execute(query)
#         new_stock = result.scalar()
        
#         if new_stock is None:
#             raise HTTPException(status_code=404, detail="Medication not found or unauthorized")
            
#         await db.commit()
        
#         if new_stock <= 5: 
#             return {"status": "low_stock", "remaining": new_stock, "alert": "Time for a refill!"}
#         return {"status": "success", "remaining": new_stock}
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))


# @app.get("/my-meds")
# async def get_user_meds(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Medication).where(Medication.user_id == current_user.id))
#     return result.scalars().all()



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

# Database and Auth imports
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

# --- Endpoints ---

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