"""Entry point for the PromptVault desktop application.

Launches a QApplication and shows the main window. Run directly via
`python -m promptvault.ui.app`.
"""

import sys

from PySide6.QtWidgets import QApplication

from promptvault.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
