import os
import shutil
import zipfile
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QFileDialog, QProgressBar
)
from PyQt5.QtCore import pyqtSignal, QThread

class DataSyncWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()

    def __init__(self, mode, r_folder, target_path, is_zip):
        super().__init__()
        self.mode = mode
        self.r_folder = r_folder
        self.target_path = target_path
        self.is_zip = is_zip

    def run(self):
        if self.mode == "export":
            self._export()
        else:
            self._import()
        self.finished.emit()

    def _export(self):
        if not os.path.exists(self.r_folder):
            self.log.emit(f"[ERROR] Target path verification failure: Location '{self.r_folder}' not found.")
            return
        
        files = [f for f in os.listdir(self.r_folder) if os.path.isfile(os.path.join(self.r_folder, f))]
        total = len(files)
        if total == 0:
            self.log.emit("[WARN] Process skipped: No matching data records discovered in active scope.")
            return

        self.log.emit(f"[INFO] Initializing serialization protocol for {total} elements...")
        
        if self.is_zip:
            try:
                with zipfile.ZipFile(self.target_path, 'w', zipfile.ZIP_DEFLATED) as z:
                    for idx, f in enumerate(files):
                        z.write(os.path.join(self.r_folder, f), os.path.join("r", f))
                        if idx % 20 == 0 or idx == total - 1:
                            self.progress.emit(idx + 1, total)
                self.log.emit(f"[SUCCESS] Export package compiled successfully: {os.path.basename(self.target_path)}")
            except Exception as e:
                self.log.emit(f"[ERROR] Compressed archive output file generation failed: {e}")
        else:
            try:
                os.makedirs(self.target_path, exist_ok=True)
                skipped, copied = 0, 0
                for idx, f in enumerate(files):
                    src = os.path.join(self.r_folder, f)
                    dst = os.path.join(self.target_path, f)
                    if os.path.exists(dst):
                        skipped += 1
                    else:
                        shutil.copy2(src, dst)
                        copied += 1
                    if idx % 20 == 0 or idx == total - 1:
                        self.progress.emit(idx + 1, total)
                self.log.emit(f"[SUCCESS] Directory sync phase completed. Copied: {copied}, Skipped due to collision protection: {skipped}")
            except Exception as e:
                self.log.emit(f"[ERROR] I/O sync batch transfer execution hit fault: {e}")

    def _import(self):
        os.makedirs(self.r_folder, exist_ok=True)
        existing_hashes = set(os.listdir(self.r_folder))
        copied, skipped = 0, 0

        if self.is_zip:
            if not zipfile.is_zipfile(self.target_path):
                self.log.emit("[ERROR] Format verification fault: File is not a valid compressed ZIP sequence.")
                return
            try:
                with zipfile.ZipFile(self.target_path, 'r') as z:
                    valid_entries = [n for n in z.namelist() if n.endswith('.osr') and not n.endswith('/')]
                    total = len(valid_entries)
                    if total == 0:
                        self.log.emit("[WARN] Parsing terminated: Found zero structured database data objects (.osr).")
                        return
                    
                    self.log.emit(f"[INFO] Cross-checking package entries against local data catalog ({total} records)...")
                    for idx, entry in enumerate(valid_entries):
                        filename = os.path.basename(entry)
                        if filename in existing_hashes:
                            skipped += 1
                        else:
                            data = z.read(entry)
                            with open(os.path.join(self.r_folder, filename), "wb") as out_f:
                                out_f.write(data)
                            copied += 1
                        if idx % 20 == 0 or idx == total - 1:
                            self.progress.emit(idx + 1, total)
                self.log.emit(f"[SUCCESS] Import completed. Injected: {copied} elements, Shielded: {skipped} duplicates.")
            except Exception as e:
                self.log.emit(f"[ERROR] Critical system fault during file compression layout extraction: {e}")
        else:
            if not os.path.exists(self.target_path):
                self.log.emit("[ERROR] Path mapping fault: Source backup folder pointer cannot be resolved on disk.")
                return
            try:
                files = [f for f in os.listdir(self.target_path) if os.path.isfile(os.path.join(self.target_path, f))]
                total = len(files)
                if total == 0:
                    self.log.emit("[WARN] Processing skipped: Target directory contains no readable data blocks.")
                    return
                
                self.log.emit(f"[INFO] Executing target batch evaluation routine across {total} elements...")
                for idx, f in enumerate(files):
                    if f in existing_hashes:
                        skipped += 1
                    else:
                        shutil.copy2(os.path.join(self.target_path, f), os.path.join(self.r_folder, f))
                        copied += 1
                    if idx % 20 == 0 or idx == total - 1:
                        self.progress.emit(idx + 1, total)
                self.log.emit(f"[SUCCESS] Manifest analysis finish. Merged elements: {copied}, Shielded entries: {skipped}")
            except Exception as e:
                self.log.emit(f"[ERROR] File system merge process encountered a fatal layout copy failure: {e}")


class GameDataTab(QWidget):
    log_signal = pyqtSignal(str)

    def __init__(self, main_window_config):
        super().__init__()
        self.config = main_window_config
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 14, 14, 14)

        dir_group = QGroupBox("Target osu! Database Directory Path (Data/r)")
        dir_lay = QHBoxLayout(dir_group)
        self.r_path_input = QLineEdit()
        self.r_path_input.setPlaceholderText("Provide path string terminating explicitly in .../Data/r")
        
        browse_r_btn = QPushButton("Browse Folder")
        browse_r_btn.clicked.connect(self._browse_r_folder)
        
        dir_lay.addWidget(self.r_path_input)
        dir_lay.addWidget(browse_r_btn)
        layout.addWidget(dir_group)

        exp_group = QGroupBox("Replay Data Export Utilities")
        exp_lay = QVBoxLayout(exp_group)
        exp_row = QHBoxLayout()
        exp_zip_btn = QPushButton("Export to Compressed Archive (.zip)")
        exp_zip_btn.clicked.connect(lambda: self._start_sync("export", is_zip=True))
        exp_folder_btn = QPushButton("Export to Directory")
        exp_folder_btn.clicked.connect(lambda: self._start_sync("export", is_zip=False))
        exp_row.addWidget(exp_zip_btn)
        exp_row.addWidget(exp_folder_btn)
        exp_lay.addLayout(exp_row)
        layout.addWidget(exp_group)

        imp_group = QGroupBox("Replay Data Import Utilities")
        imp_lay = QVBoxLayout(imp_group)
        imp_row = QHBoxLayout()
        imp_zip_btn = QPushButton("Import from Compressed Archive (.zip)")
        imp_zip_btn.clicked.connect(lambda: self._start_sync("import", is_zip=True))
        imp_folder_btn = QPushButton("Import from Directory")
        imp_folder_btn.clicked.connect(lambda: self._start_sync("import", is_zip=False))
        imp_row.addWidget(imp_zip_btn)
        imp_row.addWidget(imp_folder_btn)
        imp_lay.addLayout(imp_row)
        layout.addWidget(imp_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Waiting...")
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def _browse_r_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Map Local Directory Endpoint")
        if folder:
            self.r_path_input.setText(folder)
            self.config["r_folder_path"] = folder

    def load_saved_path(self):
        saved = self.config.get("r_folder_path", "")
        if saved:
            self.r_path_input.setText(saved)
        else:
            songs = self.config.get("songs_folder", "")
            if songs:
                guess = os.path.join(os.path.dirname(os.path.abspath(songs)), "Data", "r")
                if os.path.exists(guess):
                    self.r_path_input.setText(guess)
                    self.config["r_folder_path"] = guess

    def _start_sync(self, mode, is_zip):
        r_folder = self.r_path_input.text().strip()
        if not r_folder or not os.path.isdir(r_folder):
            self.log_signal.emit("[ERROR] Execution aborted: Invalid local database directory configuration context.")
            return

        if mode == "export":
            if is_zip:
                target, _ = QFileDialog.getSaveFileName(self, "Specify Archive Output Destination", "backup_manifest.zip", "Archives (*.zip)")
            else:
                target = QFileDialog.getExistingDirectory(self, "Select Output Target Directory Path")
        else:
            if is_zip:
                target, _ = QFileDialog.getOpenFileName(self, "Select Input Stream Archive", "", "Archives (*.zip)")
            else:
                target = QFileDialog.getExistingDirectory(self, "Select Input Source Directory Path")

        if not target:
            return

        self.progress_bar.setFormat("%p%")
        self.progress_bar.setValue(0)
        
        self.worker = DataSyncWorker(mode, r_folder, target, is_zip)
        self.worker.log.connect(self.log_signal.emit)
        self.worker.progress.connect(lambda cur, tot: (self.progress_bar.setMaximum(tot), self.progress_bar.setValue(cur)))
        self.worker.finished.connect(self._on_sync_finished)
        self.worker.start()

    def _on_sync_finished(self):
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.progress_bar.setFormat("Done!")