import sys
import os
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Имитация config manager


def get_config_value(key, default=None):
    return default


# Импортируем обработчик из main.py:
try:
    from main import process_all_csv_from_list
except ImportError:
    def process_all_csv_from_list(folder_uid, csv_dir, file_list, log_callback, allow_headdep_recursive=True):
        for fn in file_list:
            log_callback(f'Обрабатывается: {fn}\n')
        log_callback('Выполнено (заглушка)\n')


class CSVProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_checkboxes = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Генерация XML из CSV')
        self.setGeometry(100, 100, 900, 700)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Настройки
        settings_group = QGroupBox("Настройки")
        settings_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
            }
        """)
        settings_layout = QGridLayout()
        settings_layout.setSpacing(10)
        settings_layout.setContentsMargins(15, 15, 15, 15)

        # UID
        uid_label = QLabel("UID папки для ролей:")
        uid_label.setStyleSheet("font-weight: normal;")
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("Введите UID папки...")
        self.uid_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
                outline: none;
            }
        """)
        settings_layout.addWidget(uid_label, 0, 0)
        settings_layout.addWidget(self.uid_input, 0, 1, 1, 2)

        # Папка CSV
        csv_label = QLabel("Папка с CSV-файлами:")
        csv_label.setStyleSheet("font-weight: normal;")
        self.csv_path_input = QLineEdit()
        self.csv_path_input.setPlaceholderText(
            "Выберите папку с CSV файлами...")
        self.csv_path_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
                outline: none;
            }
        """)
        self.browse_button = QPushButton("Обзор")
        self.browse_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.browse_button.clicked.connect(self.select_folder)
        settings_layout.addWidget(csv_label, 1, 0)
        settings_layout.addWidget(self.csv_path_input, 1, 1)
        settings_layout.addWidget(self.browse_button, 1, 2)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Список файлов
        files_group = QGroupBox("Выберите файлы для обработки")
        files_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
            }
        """)
        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(15, 15, 15, 15)

        # Прокручиваемая область для файлов
        self.files_scroll = QScrollArea()
        self.files_scroll.setWidgetResizable(True)
        self.files_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 15px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        self.files_widget = QWidget()
        self.files_layout = QVBoxLayout(self.files_widget)
        self.files_layout.setSpacing(5)
        self.files_layout.setContentsMargins(10, 10, 10, 10)
        self.files_scroll.setWidget(self.files_widget)
        files_layout.addWidget(self.files_scroll)

        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        # Опции
        options_layout = QHBoxLayout()
        self.recursive_checkbox = QCheckBox(
            "Рекурсивный доступ к дочерним подразделениям")
        self.recursive_checkbox.setChecked(get_config_value(
            'csv_processing.allow_headdep_recursive', True))
        self.recursive_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                font-size: 11px;
                color: #555555;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #cccccc;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #3498db;
            }
        """)
        options_layout.addWidget(self.recursive_checkbox)
        options_layout.addStretch()

        main_layout.addLayout(options_layout)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.start_button = QPushButton("Старт")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        self.start_button.clicked.connect(self.start_conversion)

        self.open_folder_button = QPushButton("Открыть папку с результатами")
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 11px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #6c7a7d;
            }
            QPushButton:pressed {
                background-color: #5a6668;
            }
        """)
        self.open_folder_button.clicked.connect(self.open_results_folder)

        buttons_layout.addWidget(self.start_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.open_folder_button)

        main_layout.addLayout(buttons_layout)

        # Лог
        log_group = QGroupBox("Протокол / лог")
        log_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
            }
        """)
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(15, 15, 15, 15)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #ffffff;
                color: #2c3e50;
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
            }
        """)

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # Применяем светлую тему
        self.apply_light_theme()

    def apply_light_theme(self):
        # Светлая палитра
        light_palette = QPalette()

        light_palette.setColor(QPalette.Window, QColor(245, 245, 245))
        light_palette.setColor(QPalette.WindowText, QColor(44, 62, 80))
        light_palette.setColor(QPalette.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ToolTipBase, QColor(44, 62, 80))
        light_palette.setColor(QPalette.ToolTipText, QColor(44, 62, 80))
        light_palette.setColor(QPalette.Text, QColor(44, 62, 80))
        light_palette.setColor(QPalette.Button, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ButtonText, QColor(44, 62, 80))
        light_palette.setColor(QPalette.BrightText, QColor(231, 76, 60))
        light_palette.setColor(QPalette.Link, QColor(52, 152, 219))
        light_palette.setColor(QPalette.Highlight, QColor(52, 152, 219))
        light_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        self.setPalette(light_palette)

        # Основной стиль
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
            }
            
            QLabel {
                color: #2c3e50;
            }
            
            QCheckBox {
                color: #2c3e50;
            }
        """)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку с CSV файлами")
        if folder:
            self.csv_path_input.setText(folder)
            self.populate_file_list()

    def populate_file_list(self):
        # Очищаем список чекбоксов
        for checkbox in self.file_checkboxes:
            checkbox.setParent(None)
        self.file_checkboxes.clear()

        folder = self.csv_path_input.text()
        if not folder or not os.path.isdir(folder):
            return

        try:
            files = [f for f in os.listdir(folder)
                     if f.lower().endswith('.csv') and f.lower() != 'sample.csv']
        except Exception as e:
            self.add_log(f"Ошибка чтения папки: {e}\n")
            return

        if not files:
            no_files_label = QLabel("(Нет подходящих файлов)")
            no_files_label.setStyleSheet(
                "color: #e74c3c; font-style: italic; padding: 10px;")
            self.files_layout.addWidget(no_files_label)
            self.file_checkboxes.append(no_files_label)
            return

        # Сортируем файлы
        files.sort()

        # Создаем чекбоксы для каждого файла
        for filename in files:
            checkbox = QCheckBox(filename)
            checkbox.setChecked(True)
            checkbox.setStyleSheet("""
                QCheckBox {
                    padding: 8px 10px;
                    border-bottom: 1px solid #f0f0f0;
                    spacing: 10px;
                }
                QCheckBox:last-child {
                    border-bottom: none;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border: 2px solid #cccccc;
                    border-radius: 4px;
                }
                QCheckBox::indicator:unchecked {
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #3498db;
                    border-color: #3498db;
                }
            """)
            self.files_layout.addWidget(checkbox)
            self.file_checkboxes.append(checkbox)

    def start_conversion(self):
        uid = self.uid_input.text().strip()
        csv_dir = self.csv_path_input.text()

        # Получаем выбранные файлы
        selected_files = []
        for checkbox in self.file_checkboxes:
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_files.append(checkbox.text())

        allow_recursive = self.recursive_checkbox.isChecked()

        # Валидация
        if not uid:
            QMessageBox.warning(self, "Внимание!",
                                "Введите UID папки для ролей!")
            return
        if not csv_dir or not os.path.isdir(csv_dir):
            QMessageBox.warning(self, "Внимание!",
                                "Выберите действительную папку с CSV-файлами!")
            return
        if not selected_files:
            QMessageBox.warning(self, "Внимание!", "Выделите хотя бы 1 файл!")
            return

        # Очищаем лог
        self.log_text.clear()

        # Запускаем обработку в отдельном потоке
        def run_job():
            try:
                process_all_csv_from_list(
                    uid, csv_dir, selected_files, self.add_log,
                    allow_headdep_recursive=allow_recursive
                )
                self.add_log("Обработка завершена.\n")
            except Exception as e:
                self.add_log(f"Ошибка: {e}\n")

        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()

    def add_log(self, text):
        # Исправленный метод для обновления лога из другого потока
        self.log_text.appendPlainText(text)

    def open_results_folder(self):
        folder = self.csv_path_input.text()
        if not folder or not os.path.isdir(folder):
            QMessageBox.information(
                self, "Инфо", "Папка не выбрана или не найдена.")
            return

        try:
            if sys.platform.startswith('win'):
                os.startfile(folder)
            elif sys.platform.startswith('darwin'):
                QProcess.startDetached('open', [folder])
            else:
                QProcess.startDetached('xdg-open', [folder])
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка", f"Не удалось открыть папку: {e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Используем Fusion стиль для лучшего внешнего вида

    window = CSVProcessorApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
