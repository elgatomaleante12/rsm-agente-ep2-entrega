# Cambios finales EP2

Este documento resume los cambios incorporados para transformar el diseño inicial del sistema RSM en una versión funcional, ejecutable y evaluable en Visual Studio Code.

## Proyecto funcional

- Se creó una API con FastAPI en `app/main.py`.
- Se agregó una interfaz web simple en `app/static/`.
- Se configuró el proyecto para abrirse directamente en Visual Studio Code mediante `rsm-agente-ep2.code-workspace`.
- Se agregaron tareas de VS Code para instalar dependencias, inicializar la base de datos, ejecutar la API, correr pruebas y ejecutar una demo CLI.

## Agente y herramientas

- Se implementó `RSMAgent` en `app/agent.py` como orquestador principal.
- Se agregó `TaskPlanner` en `app/planner.py` para decidir el flujo según la intención del usuario.
- Se integraron herramientas LangChain Core (`StructuredTool`) en `app/tools.py`:
  - `consultar_inventario`
  - `registrar_salida`
  - `generar_alertas`
  - `recuperar_contexto`
  - `redactar_reporte_alertas`

## Memoria y recuperación de contexto

- Se agregó persistencia local en SQLite mediante `app/database.py`.
- Se implementó memoria de sesión y memoria histórica en la tabla `memory`.
- Se agregó recuperación de contexto local en `app/retriever.py`, usando inventario, reglas operativas y memoria previa.
- Se ajustó el orden de memoria para que el agente recupere contexto previo antes de guardar la consulta actual.

## Datos y evidencia

- Se creó inventario de ejemplo en `data/inventory.csv`.
- Se agregaron reglas operativas en `data/knowledge_base.json`.
- Se implementaron pruebas automatizadas en `tests/`.
- Resultado validado: `6 passed`.

## Documentación entregable

- `README.md` con instrucciones de ejecución, endpoints, arquitectura y alineación con la pauta EP2.
- `docs/diagrama_orquestacion.mmd` con diagrama Mermaid.
- `docs/diagrama_orquestacion.png` usado en el informe.
- `docs/Informe_EP2_RSM_Agente_Funcional.docx`.
- `docs/Informe_EP2_RSM_Agente_Funcional.pdf`, validado en 5 páginas.

