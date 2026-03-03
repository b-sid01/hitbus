from fastapi import FastAPI
from app.routers import auth, ideas

app = FastAPI(
    title="Hitbus API",
    description="Global Startup Demand Intelligence Platform",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(ideas.router)

@app.get("/")
def root():
    return {"message": "Hitbus API is running"}
