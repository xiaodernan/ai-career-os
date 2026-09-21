from fastapi import APIRouter

router = APIRouter(prefix="/internal/agents", tags=["agents"])
# implemented in task #8 (orchestrator, tools, memory)
