import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from views.main_window import CAAOcularMainWindow
from controllers.main_controller import MainController


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    view = CAAOcularMainWindow()
    controller = MainController(view)

    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()