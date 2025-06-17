from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI


from app.api.v1.videos import router
from app.db.database import engine, Base
from app.services.playwright_service import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.start()
    yield
    await manager.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
    uvicorn.run("main:app")
