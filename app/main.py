from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import public, admin

app = FastAPI(title="BTE Careers API")

# Mount Routers
# Note: Admin endpoints will require HR authentication middleware (coordinated with Security Gem)
# app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
