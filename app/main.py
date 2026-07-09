from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.llms.chat_models.models_config import models_config
from app.third_agent.register.api import router as agents_router
from app.session.api import router as workflows_router, recover_workflows_on_startup
from app.config.settings import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await recover_workflows_on_startup()
    yield


app = FastAPI(
    title="MOMA-Developer",
    description="MOMA-Developer：多 Agent 编排与 AI 研发交付平台",
    version="0.1.0",
    lifespan=lifespan,
)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(workflows_router)
app.include_router(agents_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "MOMA-Developer",
        "llm": {
            "available": models_config.is_available(),
            "models_file": str(settings.models_path),
        },
    }
