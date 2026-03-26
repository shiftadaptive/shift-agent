# SHIFT ::: Agent
# Lightweight correction service for API requests
# (c) 2026 ShiftAdaptive

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import requests as http_requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from logger import init_logger, log

load_dotenv()
init_logger()

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CORRECTION_CACHE = {}
OPENAPI_CACHE = {}

class CorrectionRequest(BaseModel):
    request: dict
    error: str
    requestId: str
    target: str = ""

def get_base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def fetch_openapi(base_url: str):
    if base_url in OPENAPI_CACHE:
        return OPENAPI_CACHE[base_url]

    paths = [
        "/openapi.json",
        "/swagger.json",
        "/v3/api-docs"
    ]

    for path in paths:
        try:
            res = http_requests.get(base_url + path, timeout=2)
            if res.status_code == 200:
                spec = res.json()
                OPENAPI_CACHE[base_url] = spec
                return spec
        except:
            continue

    OPENAPI_CACHE[base_url] = None
    return None

def extract_params_from_openapi(spec):
    params = []

    try:
        paths = spec.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue
                for p in details.get("parameters", []):
                    params.append({
                        "name": p.get("name"),
                        "in": p.get("in"),
                        "required": p.get("required", False)
                    })
    except:
        pass

    return params

@app.post("/correct")
async def correct(req: CorrectionRequest):
    log.info(f"[{req.requestId}] Agent received correction request")
    log.info(f"[{req.requestId}] Error: {req.error}")

    cache_key = json.dumps(req.request, sort_keys=True) + req.error
    if cache_key in CORRECTION_CACHE:
        log.info(f"[{req.requestId}] Agent cache hit")
        return CORRECTION_CACHE[cache_key]

    params = req.request.get("params", {})

    # OpenAPI-aware schema fetching
    params_schema = []
    if req.target:
        base_url = get_base_url(req.target)
        openapi = fetch_openapi(base_url)
        if openapi:
            params_schema = extract_params_from_openapi(openapi)
            log.info(f"[{req.requestId}] OpenAPI spec found, {len(params_schema)} params extracted")
        else:
            log.info(f"[{req.requestId}] No OpenAPI spec found for {base_url}")

    schema_context = ""
    if params_schema:
        schema_context = f"""
Available API parameters (from OpenAPI spec):
{json.dumps(params_schema, indent=2)}
"""

    prompt = f"""
You are an API request correction engine.

Your job is to fix incorrect API request parameters.

Original request params:
{json.dumps(params)}

Error message:
{req.error}
{schema_context}
Rules:
- Only modify parameter names if needed
- Keep values unchanged
- Do NOT add new unrelated parameters
- If a parameter is missing, infer correct name from error
- If API schema is provided, use parameter names from the schema

Example:
Input:
params = {{"city": "Colombo"}}
error = "Parameter q is missing"

Output:
{{"params": {{"q": "Colombo"}}}}

Return ONLY valid JSON:
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

        if "params" not in result:
            log.error(f"[{req.requestId}] LLM returned invalid structure (missing 'params' key)")
            return {"params": {}}

        log.info(f"[{req.requestId}] Corrected params: {result.get('params', {})}")

        CORRECTION_CACHE[cache_key] = result

        return result
    except Exception as e:
        log.error(f"[{req.requestId}] Failed to parse LLM response: {e}")
        return {"params": {}}

@app.on_event("startup")
async def startup_event():
    log.info("SHIFT Agent running on :8000")