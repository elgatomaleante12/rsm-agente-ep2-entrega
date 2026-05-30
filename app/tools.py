from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool

from . import database
from .database import add_memory, register_movement, rows
from .retriever import retrieve_context


class RSMToolKit:
    """LangChain tool adapter for consultation, writing and reasoning tools."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.tools = [
            StructuredTool.from_function(
                self.consultar_inventario,
                name="consultar_inventario",
                description="Consulta stock, ubicacion, proveedor y compatibilidad de repuestos RSM.",
            ),
            StructuredTool.from_function(
                self.registrar_salida,
                name="registrar_salida",
                description="Registra una salida de inventario con trazabilidad por orden de trabajo.",
            ),
            StructuredTool.from_function(
                self.generar_alertas,
                name="generar_alertas",
                description="Detecta items con stock critico o bajo minimo.",
            ),
            StructuredTool.from_function(
                self.recuperar_contexto,
                name="recuperar_contexto",
                description="Recupera contexto semantico desde inventario, reglas y memoria.",
            ),
            StructuredTool.from_function(
                self.redactar_reporte_alertas,
                name="redactar_reporte_alertas",
                description="Escribe un reporte markdown con alertas y recomendaciones.",
            ),
        ]

    def tool_names(self) -> list[str]:
        return [tool.name for tool in self.tools]

    def get(self, name: str) -> StructuredTool:
        for tool in self.tools:
            if tool.name == name:
                return tool
        raise KeyError(name)

    def consultar_inventario(self, query: str, session_id: str = "demo") -> dict[str, Any]:
        """Consulta inventario por texto natural."""
        hits = retrieve_context(query, session_id=session_id, limit=5, path=self.path)
        items = [hit["payload"] for hit in hits if hit["source"] == "inventory"]
        if not items:
            items = rows("SELECT * FROM inventory ORDER BY stock ASC LIMIT 5", path=self.path)
        return {"query": query, "items": items[:5], "context": hits}

    def registrar_salida(
        self,
        item_ref: str,
        quantity: int,
        ot_id: str,
        mechanic: str,
        vehicle: str,
        session_id: str = "demo",
    ) -> dict[str, Any]:
        """Registra una salida de stock y deja memoria persistente."""
        result = register_movement(
            item_ref=item_ref,
            quantity=quantity,
            movement_type="salida",
            ot_id=ot_id,
            mechanic=mechanic,
            vehicle=vehicle,
            note="Movimiento registrado por agente RSM EP2",
            path=self.path,
        )
        if result["ok"]:
            item = result["item"]
            add_memory(
                session_id,
                "movement",
                (
                    f"Salida registrada: {quantity} unidad(es) de {item_ref} para {ot_id}. "
                    f"Mecanico: {mechanic}. Vehiculo: {vehicle}. Stock nuevo: {item['stock']}."
                ),
                {"item_ref": item_ref, "ot_id": ot_id, "vehicle": vehicle},
                path=self.path,
            )
        return result

    def generar_alertas(self) -> dict[str, Any]:
        """Genera alertas de stock ordenadas por prioridad."""
        inventory = rows("SELECT * FROM inventory", path=self.path)
        alerts = []
        for item in inventory:
            stock = int(item["stock"])
            minimum = int(item["min_stock"])
            if stock == 0:
                level = "CRITICO"
            elif stock <= minimum:
                level = "BAJO"
            else:
                continue
            alerts.append(
                {
                    "level": level,
                    "ref": item["ref"],
                    "name": item["name"],
                    "stock": stock,
                    "min_stock": minimum,
                    "provider": item["provider"],
                    "lead_time_days": item["lead_time_days"],
                    "location": item["location"],
                }
            )
        alerts.sort(key=lambda row: (0 if row["level"] == "CRITICO" else 1, row["lead_time_days"]))
        return {"count": len(alerts), "alerts": alerts}

    def recuperar_contexto(self, query: str, session_id: str = "demo") -> dict[str, Any]:
        """Recupera fragmentos relevantes de inventario, politicas y memoria."""
        return {"query": query, "hits": retrieve_context(query, session_id=session_id, path=self.path)}

    def redactar_reporte_alertas(self, session_id: str = "demo") -> dict[str, Any]:
        """Escribe evidencia operativa con alertas y recomendaciones."""
        alerts = self.generar_alertas()["alerts"]
        out_dir = database.PROJECT_ROOT / "outputs"
        out_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"reporte_alertas_{stamp}.md"

        lines = [
            "# Reporte operativo de alertas RSM",
            "",
            f"Generado por el agente funcional EP2 para la sesion `{session_id}`.",
            "",
            "## Prioridades",
        ]
        if not alerts:
            lines.append("- Inventario en niveles operativos normales.")
        for alert in alerts:
            reorder = max(int(alert["min_stock"]) * 2 - int(alert["stock"]), 1)
            lines.append(
                "- "
                f"{alert['level']}: {alert['name']} ({alert['ref']}) tiene {alert['stock']} "
                f"unidad(es), minimo {alert['min_stock']}. Reponer {reorder} unidad(es) con "
                f"{alert['provider']} (lead time {alert['lead_time_days']} dia(s))."
            )

        lines.extend(
            [
                "",
                "## Decision del agente",
                "El agente prioriza stock CRITICO, luego stock BAJO, y conserva trazabilidad local en SQLite.",
            ]
        )
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        add_memory(session_id, "report", f"Reporte de alertas generado: {out_path.name}", {"path": str(out_path)}, path=self.path)
        return {"path": str(out_path), "alerts": alerts}

