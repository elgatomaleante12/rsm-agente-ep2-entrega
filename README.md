# RSM Agente Funcional EP2

Agente local para gestión de inventario mecánico, construido con FastAPI, LangChain y SQLite. Este proyecto es una entrega funcional para la Evaluación Parcial 2 de ISY0101 y está diseñado para que sea fácil de ejecutar, probar y presentar.

## Qué hace

- Proporciona una API web con interfaz estática y endpoints REST.
- Gestiona inventario mecánico con consultas de stock, ubicación, proveedor y compatibilidad.
- Registra movimientos de salida con trazabilidad por OT, mecánico y vehículo.
- Genera alertas de stock crítico y bajo mínimo.
- Recupera contexto de inventario, política y memoria histórica.
- Produce reportes operativos en formato Markdown.

## Tecnologías principales

- Python 3
- FastAPI
- LangChain (`langchain-core`)
- SQLite
- pytest
- Uvicorn

## Configuración rápida

1. Abre la carpeta `rsm-agente-ep2` en Visual Studio Code.
2. Abre `Terminal > Run Task...`.
3. Ejecuta `Instalar dependencias`.
4. Ejecuta `Inicializar base de datos`.
5. Ejecuta `Ejecutar API`.
6. Navega a `http://127.0.0.1:8000`.

También puedes usar el workspace `rsm-agente-ep2.code-workspace` si prefieres abrir todo el proyecto con la configuración de VS Code.

## Instalación por terminal

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\init_db.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Endpoints principales

- `GET /` → Interfaz web
- `GET /health` → Estado del servicio
- `POST /api/chat` → Chat con el agente
- `GET /api/inventory` → Listado de inventario completo
- `GET /api/alerts` → Alertas de stock crítico y bajo mínimo
- `POST /api/reports/alerts` → Genera reporte Markdown de alertas
- `GET /api/memory/{session_id}` → Memoria de conversación por sesión

## Cómo usar el chat

Ejemplos de mensajes válidos:

- `Cuantos filtros de aceite Toyota quedan?`
- `Que items estan criticos o bajo minimo?`
- `Registra salida de 2 unidades FO-TOY-001 para OT-778 con mecanico Ana y vehiculo Toyota Yaris 2020`
- `Recomienda que debo reponer hoy`
- `Genera un reporte de alertas de stock`

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Lo que cubren los tests

- Consulta de inventario con recuperación de contexto.
- Registro de salida y actualización de stock.
- Prevención de descuentos de stock sin trazabilidad completa.
- Rechazo de movimientos con stock insuficiente.
- Endpoints de API básicos.

## Estructura del proyecto

- `app/` → Código principal del agente y API
- `data/` → Datos de inventario y base de conocimiento
- `docs/` → Diagrama de orquestación y documentación adicional
- `scripts/` → Scripts de inicialización y demo
- `tests/` → Pruebas unitarias y de API
- `requirements.txt` → Dependencias del proyecto

## Detalles de implementación

- `app/main.py` monta la API FastAPI y expone la interfaz web.
- `app/agent.py` coordina la planificación, la ejecución de herramientas y la memoria.
- `app/planner.py` interpreta la intención del usuario y decide el flujo.
- `app/tools.py` define las herramientas LangChain para inventario, alertas, contexto y reportes.
- `app/retriever.py` recupera contexto relevante desde inventario, conocimiento y memoria.
- `app/database.py` inicializa SQLite, carga datos y registra movimientos.


## Referencias

- LangChain: https://python.langchain.com/docs/
- FastAPI: https://fastapi.tiangolo.com/
- SQLite: https://sqlite.org/docs.html

