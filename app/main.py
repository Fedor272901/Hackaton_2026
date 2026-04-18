from fastapi import FastAPI
from app.api_router import api_router

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

app = FastAPI(title="Hackathon API", version="1.0.0")

app.include_router(api_router)
