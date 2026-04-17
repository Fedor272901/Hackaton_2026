from fastapi import FastAPI
from app.api_router import api_router

app = FastAPI(title="Hackathon API", version="1.0.0")

app.include_router(api_router)
