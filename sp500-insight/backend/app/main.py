from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import health, stocks

settings = get_settings()

app = FastAPI(
    title="S&P 500 Insight API",
    description="Daily automated analysis and data for the S&P 500",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(stocks.router, prefix="/api/v1", tags=["Stocks"])


@app.get("/")
async def root():
    return {
        "project": "S&P 500 Insight",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "scaffolded",
    }
