from __future__ import annotations

from pathlib import Path
from typing import Any

from .database import add_memory, get_recent_memory, init_db
from .planner import TaskPlanner
from .tools import RSMToolKit


class RSMAgent:
    """Functional agent for the EP2 evaluation."""

    def __init__(self, path: Path | None = None):
        self.path = path
        init_db(path=path)
        self.planner = TaskPlanner(path=path)
        self.toolkit = RSMToolKit(path=path)

    def handle(self, message: str, session_id: str = "demo") -> dict[str, Any]:
        plan = self.planner.build(message, session_id)
        tool_calls: list[dict[str, Any]] = []

        if plan.missing_fields:
            response = self._missing_fields_response(plan.missing_fields)
            add_memory(session_id, "user", message, path=self.path)
            add_memory(session_id, "assistant", response, {"intent": plan.intent}, path=self.path)
            return self._payload(response, plan, tool_calls, session_id)

        if plan.intent == "registrar_salida":
            result = self._invoke(
                "registrar_salida",
                {
                    "item_ref": plan.fields["item_ref"],
                    "quantity": plan.fields["quantity"],
                    "ot_id": plan.fields["ot_id"],
                    "mechanic": plan.fields["mechanic"],
                    "vehicle": plan.fields["vehicle"],
                    "session_id": session_id,
                },
                tool_calls,
            )
            response = self._format_movement_response(result)

        elif plan.intent == "generar_alertas":
            result = self._invoke("generar_alertas", {}, tool_calls)
            response = self._format_alert_response(result)

        elif plan.intent == "recomendar_reposicion":
            context = self._invoke("recuperar_contexto", {"query": message, "session_id": session_id}, tool_calls)
            alerts = self._invoke("generar_alertas", {}, tool_calls)
            response = self._format_recommendation(alerts, context)

        elif plan.intent == "redactar_reporte":
            result = self._invoke("redactar_reporte_alertas", {"session_id": session_id}, tool_calls)
            response = f"Reporte de alertas generado correctamente: {result['path']}"

        else:
            context = self._invoke("recuperar_contexto", {"query": message, "session_id": session_id}, tool_calls)
            inventory = self._invoke("consultar_inventario", {"query": message, "session_id": session_id}, tool_calls)
            response = self._format_stock_response(inventory, context)

        add_memory(session_id, "user", message, path=self.path)
        add_memory(session_id, "assistant", response, {"intent": plan.intent, "tools": [c["tool"] for c in tool_calls]}, path=self.path)
        return self._payload(response, plan, tool_calls, session_id)

    def _invoke(self, name: str, args: dict[str, Any], calls: list[dict[str, Any]]) -> Any:
        result = self.toolkit.get(name).invoke(args)
        calls.append({"tool": name, "args": args, "result_preview": self._preview(result)})
        return result

    @staticmethod
    def _preview(result: Any) -> Any:
        if isinstance(result, dict):
            preview = dict(result)
            if "context" in preview:
                preview["context"] = preview["context"][:2]
            if "hits" in preview:
                preview["hits"] = preview["hits"][:2]
            if "alerts" in preview:
                preview["alerts"] = preview["alerts"][:3]
            return preview
        return result

    def _payload(self, response: str, plan: Any, tool_calls: list[dict[str, Any]], session_id: str) -> dict[str, Any]:
        return {
            "response": response,
            "intent": plan.intent,
            "plan": [{"step": step, "status": "done" if not plan.missing_fields else "waiting"} for step in plan.steps],
            "missing_fields": plan.missing_fields,
            "tools_used": [call["tool"] for call in tool_calls],
            "tool_calls": tool_calls,
            "short_term_memory": list(reversed(get_recent_memory(session_id, limit=6, path=self.path))),
        }

    @staticmethod
    def _missing_fields_response(fields: list[str]) -> str:
        labels = {
            "item_ref": "repuesto o codigo de referencia",
            "quantity": "cantidad",
            "ot_id": "orden de trabajo",
            "mechanic": "mecanico responsable",
            "vehicle": "vehiculo",
        }
        readable = ", ".join(labels.get(field, field) for field in fields)
        return f"Antes de registrar la salida necesito completar: {readable}. No descuento stock hasta tener trazabilidad completa."

    @staticmethod
    def _format_stock_response(inventory: dict[str, Any], context: dict[str, Any]) -> str:
        items = inventory.get("items", [])
        if not items:
            return "No encontre coincidencias en el inventario actual."

        lines = ["Resultado de consulta de inventario:"]
        for item in items[:3]:
            lines.append(
                f"- {item['name']} ({item['ref']}): {item['stock']} unidad(es), ubicacion {item['location']}, "
                f"proveedor {item['provider']}. Compatible con: {item['compatible_models']}."
            )
        if context.get("hits"):
            source = context["hits"][0]
            lines.append(f"Fuente recuperada: {source['title']} ({source['source']}, score {source['score']}).")
        return "\n".join(lines)

    @staticmethod
    def _format_alert_response(result: dict[str, Any]) -> str:
        alerts = result.get("alerts", [])
        if not alerts:
            return "Inventario en niveles optimos: no hay items criticos ni bajo minimo."
        lines = [f"Alertas detectadas: {len(alerts)}."]
        for alert in alerts:
            lines.append(
                f"- {alert['level']}: {alert['name']} ({alert['ref']}) tiene {alert['stock']} "
                f"/ minimo {alert['min_stock']}. Proveedor sugerido: {alert['provider']} "
                f"({alert['lead_time_days']} dia(s))."
            )
        return "\n".join(lines)

    @staticmethod
    def _format_recommendation(alerts_result: dict[str, Any], context: dict[str, Any]) -> str:
        alerts = alerts_result.get("alerts", [])
        if not alerts:
            return "No recomiendo compras urgentes: el inventario no tiene items criticos ni bajo minimo."
        lines = ["Recomendacion de reposicion priorizada:"]
        for alert in alerts[:5]:
            reorder = max(int(alert["min_stock"]) * 2 - int(alert["stock"]), 1)
            lines.append(
                f"- Prioridad {alert['level']}: comprar {reorder} unidad(es) de {alert['name']} "
                f"con {alert['provider']}."
            )
        if context.get("hits"):
            lines.append(f"Criterio aplicado: {context['hits'][0]['title']} ({context['hits'][0]['source']}).")
        return "\n".join(lines)

    @staticmethod
    def _format_movement_response(result: dict[str, Any]) -> str:
        if not result.get("ok"):
            item = result["item"]
            return (
                f"No registro la salida: stock insuficiente para {item['name']} ({item['ref']}). "
                f"Disponible: {result['available']}; solicitado: {result['requested']}."
            )
        item = result["item"]
        lines = [
            f"Salida registrada para {item['name']} ({item['ref']}).",
            f"Stock anterior: {result['previous_stock']}; stock nuevo: {result['new_stock']}.",
        ]
        if result["below_minimum"]:
            lines.append("Atencion: el item queda bajo minimo, se recomienda reposicion.")
        return "\n".join(lines)
