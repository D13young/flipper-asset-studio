import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.resources import app_icon

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Flipper Asset Studio")
    app.setApplicationDisplayName("Flipper Asset Studio")
    app.setWindowIcon(app_icon())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()