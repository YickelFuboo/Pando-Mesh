from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.maas.chat_models.models_config import models_config
from app.third_agent.register.api import router as agents_router
from app.session.api import router as workflows_router
from app.config.settings import settings

app = FastAPI(
    title="Pando-Mesh",
    description="产 Agent 的 Mesh 层：多 Agent 注册、Workflow 编排与调度",
    version="0.1.0",
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
        "service": "Pando-Mesh",
        "llm": {
            "available": models_config.is_available(),
            "models_file": str(settings.models_path),
        },
    }
