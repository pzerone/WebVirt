import asyncio
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import vms, auth, admin
from app.utils.tasks import check_expiry


# Runs check_expiry() func on startup and tear down on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(check_expiry())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(admin.router)

# Can be used by regular users to manage their VMs. all CRUD operations supported.
# app.include_router(vms.router)


# Health check
@app.get("/ping")
async def pong() -> Literal["pong"]:
    return "pong"
