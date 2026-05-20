"""
Main entry point for the AetherTest API.
"""
from fastapi import FastAPI
from src.aethertest.api.v1 import routes as api_v1_routes
from src.aethertest.api.v1 import analytics as api_v1_analytics

app = FastAPI(
    title="AetherTest API",
    description="AI Infrastructure Simulation Platform",
    version="0.1.0",
)

app.include_router(api_v1_routes.router, prefix="/api/v1", tags=["simulations"])
app.include_router(api_v1_analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

@app.get("/")
async def root():
    return {"message": "Welcome to AetherTest - AI Infrastructure Simulation Platform"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
