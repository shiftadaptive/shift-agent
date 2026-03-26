# SHIFT ::: Agent
# Lightweight correction service for API requests
# (c) 2026 ShiftAdaptive

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from logger import init_logger, log

load_dotenv()
init_logger()

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CorrectionRequest(BaseModel):
    request: dict
    error: str
    requestId: str

@app.post("/correct")
async def correct(req: CorrectionRequest):
    log.info(f"[{req.requestId}] Agent received correction request")
    log.info(f"[{req.requestId}] Error: {req.error}")

    prompt = f"""
You are an API request correction engine.

Original request:
{json.dumps(req.request)}

Error message:
{req.error}

Fix the request parameters.

Return ONLY valid JSON in this format:
{{
  "params": {{ ... }}
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.choices[0].message.content

    try:
        result = json.loads(content)
        log.info(f"[{req.requestId}] Corrected params: {result.get('params', {})}")
        return result
    except Exception as e:
        log.error(f"[{req.requestId}] Failed to generate correction: {e}")
        return {"params": {}}

@app.on_event("startup")
async def startup_event():
    log.info("SHIFT Agent running on :8000")