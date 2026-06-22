import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication, Qt
from ui.main_window import MainWindow

def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    else:
        pass
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Flipper Asset Studio")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()