from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import init_db
from app.routers.packages import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SkillHub Server", lifespan=lifespan)
app.include_router(router, prefix="/api")
