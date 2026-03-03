from fastapi import FastAPI
from app.routers import auth

app = FastAPI(
    title="Hitbus API",
    description="Global Startup Demand Intelligence Platform",
    version="1.0.0"
)

app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Hitbus API is running"}
