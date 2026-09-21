import logging
import os
import yaml
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("citizen-service")

app = FastAPI(title="WOG Citizen Support Portal", version="1.0.0")

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

class GrantApplication(BaseModel):
    nric: str
    full_name: str
    phone_number: str
    household_income: float

# In-memory mock store
APPLICATIONS = []

@app.post("/api/v1/grants/apply")
def apply_grant(application: GrantApplication):
    # VIOLATION: Personal data written to the log without masking (IM8 Reform lm-19)
    logger.info(
        f"Processing application for citizen NRIC: {application.nric}, "
        f"Name: {application.full_name}, Phone: {application.phone_number}"
    )
    
    APPLICATIONS.append(application.dict())
    return {
        "status": "received",
        "reference_id": f"REF-{len(APPLICATIONS):05d}",
        "message": "Grant application submitted successfully."
    }

# VIOLATION: Unauthenticated debug route exposes internal records (IM8 Reform as-13)
@app.get("/api/v1/debug/dump-records")
def dump_all_records():
    """Administrative debug endpoint to inspect stored applications."""
    return {
        "count": len(APPLICATIONS),
        "records": APPLICATIONS
    }

@app.get("/healthz")
def healthcheck():
    return {"status": "healthy"}
