import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # HighDPIAttributes в PyQt6 включены по умолчанию и недоступны как атрибуты Qt.
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Flipper Asset Studio")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()