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
                mode_id = struct.unpack("<B", f.read(1))[0]
                modes = {0: "osu!", 1: "Taiko", 2: "Catch the Beat", 3: "osu!mania"}
                mode_str = modes.get(mode_id, f"Unknown ({mode_id})")

                version = struct.unpack("<I", f.read(4))[0]

                def read_osu_string(file_obj):
                    indicator = file_obj.read(1)
                    if not indicator or indicator == b'\x00':
                        return ""
                    if indicator == b'\x0b':
                        length = 0
                        shift = 0
                        while True:
                            b = file_obj.read(1)[0]
                            length |= (b & 0x7F) << shift
                            if not (b & 0x80):
                                break
                            shift += 7
                        return file_obj.read(length).decode('utf-8', errors='ignore')
                    return ""

                beatmap_hash = read_osu_string(f)
                player_name = read_osu_string(f)
                replay_hash = read_osu_string(f)

                # The actual fix: The struct needs exactly 23 bytes, not 30.
                stats_bytes = f.read(23)
                
                if len(stats_bytes) == 23:
                    count_300, count_100, count_50, gekis, katus, misses, score, max_combo, perfect, mods_bitmask = struct.unpack(
                        "<HHHHHHIHBI", stats_bytes
                    )
                else:
                    count_300 = count_100 = count_50 = gekis = katus = misses = score = max_combo = perfect = mods_bitmask = "N/A"

                metadata_text = (
                    f"File: {os.path.basename(path)}\n"
                    f"Size: {os.path.getsize(path):,} bytes\n"
                    f"----------------------------------------\n"
                    f"Game Mode: {mode_str}\n"
                    f"Game Version: {version}\n"
                    f"Player Name: {player_name if player_name else 'Unknown'}\n"
                    f"Score: {score if isinstance(score, str) else f'{score:,}'}\n"
                    f"Max Combo: {max_combo}x\n"
                    f"300s / 100s / 50s: {count_300} / {count_100} / {count_50}\n"
                    f"Misses: {misses}\n"
                    f"Beatmap MD5: {beatmap_hash if beatmap_hash else 'N/A'}\n"
                    f"Replay MD5: {replay_hash if replay_hash else 'N/A'}\n"
                )
                    
                self.info_view.setPlainText(metadata_text)
                self.log_signal.emit(f"[INFO] Successfully processed metadata for: {os.path.basename(path)}")

        except Exception as e:
            self.info_view.setPlainText(f"Parsing Error: {e}")
            self.log_signal.emit(f"[ERROR] Binary parsing failed on target replay file: {e}")