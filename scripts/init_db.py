from app.database import init_db


if __name__ == "__main__":
    path = init_db(reset=True)
    print(f"Base de datos inicializada en {path}")

