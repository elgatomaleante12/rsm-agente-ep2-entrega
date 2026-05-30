from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .database import rows
from .retriever import normalize


@dataclass
class Plan:
    intent: str
    steps: list[str]
    missing_fields: list[str]
    fields: dict[str, Any]


class TaskPlanner:
    """Small deterministic planner used to demonstrate adaptive decisions."""

    def __init__(self, path: Path | None = None):
        self.path = path

    def build(self, message: str, session_id: str) -> Plan:
        text = normalize(message)
        if self._is_write_report(text):
            return Plan(
                intent="redactar_reporte",
                steps=[
                    "Recuperar alertas vigentes.",
                    "Priorizar items criticos antes que items bajos.",
                    "Redactar archivo de evidencia operativa.",
                ],
                missing_fields=[],
                fields={},
            )

        if self._is_inventory_movement(text):
            fields = self._extract_movement_fields(message)
            missing = [name for name in ["item_ref", "quantity", "ot_id", "mechanic", "vehicle"] if not fields.get(name)]
            return Plan(
                intent="registrar_salida",
                steps=[
                    "Validar datos obligatorios de trazabilidad.",
                    "Consultar stock actual del repuesto.",
                    "Registrar salida si existe stock suficiente.",
                    "Guardar el evento en memoria de largo plazo.",
                    "Advertir si el stock queda bajo minimo.",
                ],
                missing_fields=missing,
                fields=fields,
            )

        if any(word in text for word in ["alerta", "alertas", "critico", "criticos", "minimo", "minimos", "quiebre"]):
            return Plan(
                intent="generar_alertas",
                steps=[
                    "Consultar inventario completo.",
                    "Detectar items con stock 0 o bajo minimo.",
                    "Ordenar alertas por urgencia y tiempo de reposicion.",
                ],
                missing_fields=[],
                fields={},
            )

        if any(word in text for word in ["reponer", "reposicion", "comprar", "pedido", "proveedor", "recomienda"]):
            return Plan(
                intent="recomendar_reposicion",
                steps=[
                    "Recuperar reglas de stock y proveedores.",
                    "Detectar items criticos y bajos.",
                    "Construir recomendacion priorizada.",
                ],
                missing_fields=[],
                fields={},
            )

        return Plan(
            intent="consultar_stock",
            steps=[
                "Interpretar consulta del usuario.",
                "Recuperar contexto semantico del inventario y memoria.",
                "Responder con stock, ubicacion, proveedor y fuente.",
            ],
            missing_fields=[],
            fields={"query": message},
        )

    @staticmethod
    def _is_inventory_movement(text: str) -> bool:
        verbs = ["registra", "registrar", "descuenta", "descontar", "salida", "use", "usar", "ocupe", "ocupar"]
        return any(verb in text for verb in verbs)

    @staticmethod
    def _is_write_report(text: str) -> bool:
        return any(word in text for word in ["reporte", "informe", "resumen", "bitacora"]) and any(
            word in text for word in ["alerta", "alertas", "stock", "operativo"]
        )

    def _extract_movement_fields(self, message: str) -> dict[str, Any]:
        text = normalize(message)
        fields: dict[str, Any] = {"movement_type": "salida"}

        qty_match = re.search(r"(\d+)\s*(?:unidades|unidad|unds|u)\b", text)
        if not qty_match:
            qty_match = re.search(r"\bsalida\s+de\s+(\d+)\b", text)
        if qty_match:
            fields["quantity"] = int(qty_match.group(1))

        ot_match = re.search(r"\b(ot[-\s]?\d+)\b", text)
        if ot_match:
            fields["ot_id"] = ot_match.group(1).replace(" ", "-").upper()

        mechanic_match = re.search(r"mecanico\s+([a-z]+(?:\s+[a-z]+){0,2})(?:\s+y\s+vehiculo|\s+vehiculo|$)", text)
        if mechanic_match:
            fields["mechanic"] = mechanic_match.group(1).title()

        vehicle_match = re.search(r"vehiculo\s+(.+)$", message, flags=re.IGNORECASE)
        if vehicle_match:
            fields["vehicle"] = vehicle_match.group(1).strip(" .")

        explicit_ref = re.search(r"\b[A-Z]{2,5}-[A-Z0-9]+-[A-Z0-9]+\b", message.upper())
        if explicit_ref:
            fields["item_ref"] = explicit_ref.group(0)
            return fields

        best = self._find_best_inventory_match(message)
        if best:
            fields["item_ref"] = best["ref"]
        return fields

    def _find_best_inventory_match(self, message: str) -> dict[str, Any] | None:
        from .retriever import cosine_score

        candidates = rows("SELECT * FROM inventory", path=self.path)
        scored = []
        for item in candidates:
            corpus = f"{item['ref']} {item['name']} {item['category']} {item['compatible_models']}"
            scored.append((cosine_score(message, corpus), item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        if scored and scored[0][0] >= 0.15:
            return scored[0][1]
        return None

