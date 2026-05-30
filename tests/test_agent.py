from app.agent import RSMAgent
from app.database import init_db, one


def setup_function() -> None:
    init_db(reset=True)


def test_stock_query_uses_retrieval_and_inventory_tool() -> None:
    agent = RSMAgent()
    result = agent.handle("Cuantos filtros de aceite Toyota quedan?", session_id="test-stock")

    assert "FO-TOY-001" in result["response"]
    assert "consultar_inventario" in result["tools_used"]
    assert "recuperar_contexto" in result["tools_used"]


def test_register_movement_updates_stock_and_memory() -> None:
    agent = RSMAgent()
    result = agent.handle(
        "Registra salida de 2 unidades FO-TOY-001 para OT-778 con mecanico Ana y vehiculo Toyota Yaris 2020",
        session_id="test-movement",
    )
    item = one("SELECT stock FROM inventory WHERE ref = ?", ("FO-TOY-001",))
    memories = one("SELECT content FROM memory WHERE session_id = ? AND kind = 'movement'", ("test-movement",))

    assert item["stock"] == 6
    assert memories is not None
    assert "Salida registrada" in result["response"]
    assert result["tools_used"] == ["registrar_salida"]


def test_missing_traceability_prevents_stock_discount() -> None:
    agent = RSMAgent()
    result = agent.handle("Registra salida de 2 unidades FO-TOY-001", session_id="test-missing")
    item = one("SELECT stock FROM inventory WHERE ref = ?", ("FO-TOY-001",))

    assert item["stock"] == 8
    assert result["missing_fields"]
    assert "No descuento stock" in result["response"]


def test_insufficient_stock_is_rejected() -> None:
    agent = RSMAgent()
    result = agent.handle(
        "Registra salida de 99 unidades AC-5W30-1L para OT-999 con mecanico Luis y vehiculo Hyundai Accent",
        session_id="test-insufficient",
    )
    item = one("SELECT stock FROM inventory WHERE ref = ?", ("AC-5W30-1L",))

    assert item["stock"] == 3
    assert "stock insuficiente" in result["response"]

