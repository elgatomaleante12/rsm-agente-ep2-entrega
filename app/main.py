from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import RSMAgent
from .database import init_db, rows
from .tools import RSMToolKit

STATIC_DIR = Path(__file__).resolve().parent / "static"

init_db()
agent = RSMAgent()
toolkit = RSMToolKit()

app = FastAPI(
    title="RSM Agente Funcional EP2",
    description="Agente local para consulta, escritura, razonamiento, memoria y planificacion de inventario mecanico.",
    version="2.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(..., examples=["Cuantos filtros de aceite Toyota quedan en stock?"])
    session_id: str = "demo"


class ReportRequest(BaseModel):
    session_id: str = "demo"


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "tools": toolkit.tool_names()}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    return agent.handle(request.message, session_id=request.session_id)


@app.get("/api/inventory")
def inventory() -> dict[str, Any]:
    return {"items": rows("SELECT * FROM inventory ORDER BY category, name")}


@app.get("/api/alerts")
def alerts() -> dict[str, Any]:
    return toolkit.generar_alertas()


@app.post("/api/reports/alerts")
def report_alerts(request: ReportRequest) -> dict[str, Any]:
    return toolkit.redactar_reporte_alertas(session_id=request.session_id)


@app.get("/api/memory/{session_id}")
def memory(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "events": rows(
            """
            SELECT kind, content, metadata_json, created_at
            FROM memory
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT 30
            """,
            (session_id,),
        ),
    }

