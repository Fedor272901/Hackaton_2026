from fastapi import FastAPI
from app.api_router import api_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Hackathon API", version="1.0.0")

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
