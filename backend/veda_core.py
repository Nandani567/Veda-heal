import os
from google import genai
from pydantic import BaseModel, Field

# Schema for the AI to follow
class MedicationExtraction(BaseModel):
    name: str = Field(description="Name of the medicine")
    dosage: str = Field(description="Dosage (e.g. 500mg)")
    total_stock: int = Field(description="Total pills provided")

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

async def extract_info(text: str):
    response = client.models.generate_content(
        model="gemini-2.0-flash", # Use 2.0 or 1.5
        contents=f"Extract medication from: {text}",
        config={
            'response_mime_type': 'application/json',
            'response_schema': MedicationExtraction,
        }
    )
    # The new SDK returns a parsed object automatically
    return response.parsed