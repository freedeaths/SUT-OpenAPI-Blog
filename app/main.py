from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api.api import api_router
from .db.database import create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # 确保所有表都存在
    create_tables()
    yield

app = FastAPI(lifespan=lifespan)

# 注册路由
app.include_router(api_router, prefix="/api")
