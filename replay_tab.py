import os
import struct
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QGroupBox, QTextEdit, QFileDialog
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont

class ReplayTab(QWidget):
    log_signal = pyqtSignal(str)

    def __init__(self, main_window_config):
        super().__init__()
        self.config = main_window_config
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 14, 14, 14)

        file_group = QGroupBox("Single Target Replay File Evaluation (.osr)")
        file_lay = QHBoxLayout(file_group)
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Path to targeted replay data file")
        self.file_input.setReadOnly(True)
        browse_btn = QPushButton("Browse File")
        browse_btn.clicked.connect(self._browse_file)
        file_lay.addWidget(self.file_input)
        file_lay.addWidget(browse_btn)
        layout.addWidget(file_group)

        info_group = QGroupBox("Metadata")
        info_lay = QVBoxLayout(info_group)
        self.info_view = QTextEdit()
        self.info_view.setReadOnly(True)
        self.info_view.setFont(QFont("Consolas", 10))
        info_lay.addWidget(self.info_view)
        layout.addWidget(info_group)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Replay File", "", "osu! Replays (*.osr)")
        if path:
            self.file_input.setText(path)
            self._parse_osr(path)

    def _parse_osr(self, path):
        try:
            with open(path, "rb") as f:
                mode = struct.unpack("<B", f.read(1))[0]
                self.info_view.setPlainText(f"Replay File:\nGame Mode Context ID: {mode}\nFile Size Array: {os.path.getsize(path)} bytes")
                self.log_signal.emit(f"Processed isolated file parameters for: {os.path.basename(path)}")
        except Exception as e:
            self.info_view.setPlainText(f"Parsing Error: {e}")