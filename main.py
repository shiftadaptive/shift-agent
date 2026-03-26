# SHIFT ::: Agent
# Lightweight correction service for API requests
# (c) 2026 ShiftAdaptive

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
import json

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class CorrectionRequest(BaseModel):
    request: dict
    error: str

@app.post("/correct")
async def correct(req: CorrectionRequest):

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
        return json.loads(content)
    except:
        return {"params": {}}