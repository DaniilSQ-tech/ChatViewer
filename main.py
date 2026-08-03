import sys

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from db import Database, DEFAULT_DB_PATH
from models import ModelManager
from network import NetworkClient
from ui.main_window import MainWindow


def init_app() -> tuple[Database, ModelManager, NetworkClient]:
    load_dotenv()
    load_dotenv(".env.local", override=True)
    db = Database(DEFAULT_DB_PATH)
    model_manager = ModelManager(db)
    model_manager.seed_defaults()
    model_manager.sync_activation_from_env()
    network = NetworkClient(db, model_manager)
    return db, model_manager, network


def main() -> None:
    db, model_manager, network = init_app()
    app = QApplication(sys.argv)
    app.setApplicationName("ChatList")
    window = MainWindow(db, model_manager, network)
    window.show()

    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
