from app.agent import RSMAgent


def main() -> None:
    agent = RSMAgent()
    examples = [
        "Cuantos filtros de aceite Toyota quedan?",
        "Que items estan criticos o bajo minimo?",
        "Registra salida de 2 unidades FO-TOY-001 para OT-778 con mecanico Ana y vehiculo Toyota Yaris 2020",
        "Genera un reporte de alertas de stock",
    ]
    for message in examples:
        print(f"\nUSUARIO: {message}")
        result = agent.handle(message, session_id="demo-cli")
        print(f"AGENTE:\n{result['response']}")
        print(f"Herramientas: {', '.join(result['tools_used']) or 'ninguna'}")


if __name__ == "__main__":
    main()

