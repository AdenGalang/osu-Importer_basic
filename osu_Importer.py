import sys
import os
import json
import re
import zipfile
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit, QFileDialog,
    QProgressBar, QGroupBox, QTabWidget
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from replay_tab import ReplayTab
from game_data_tab import GameDataTab

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".osu_downloader_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f: return json.load(f)
        except: pass
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f: json.dump(data, f)
    except: pass

class DownloadWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    finished = pyqtSignal()

    def __init__(self, ids, songs_folder, token, cookie, no_video, skip_existing, existing_ids):
        super().__init__()
        self.ids = ids
        self.songs_folder = songs_folder
        self.token = token
        self.cookie = cookie
        self.no_video = no_video
        self.skip_existing = skip_existing
        self.existing_ids = existing_ids
        self._stop = False

    def stop(self): self._stop = True

    def run(self):
        self.log.emit("[INFO] Performing pre-download verification on target directory...")
        active_local_ids = set()
        try:
            for entry in os.scandir(self.songs_folder):
                if entry.is_dir():
                    m = re.match(r'^(\d+)', entry.name)
                    if m: active_local_ids.add(m.group(1))
        except Exception as e:
            self.log.emit(f"  [WARN] Directory pre-scan failed: {e}. Utilizing cached metadata.")
            active_local_ids = self.existing_ids

        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://osu.ppy.sh/beatmapsets",
            "Connection": "keep-alive"
        })
        
        if self.token: session.headers.update({"Authorization": f"Bearer {self.token}"})
        if self.cookie: session.cookies.set("osu_session", self.cookie.strip().strip('"\''), domain="osu.ppy.sh")

        to_download = [bid for bid in self.ids if not (self.skip_existing and bid in active_local_ids)]
        total = len(to_download)
        if total == 0:
            self.log.emit("[INFO] No new items to download.")
            self.finished.emit()
            return
        self.log.emit(f"[INFO] Download queue verified. Preparing transfer for {total} element(s)...")

        for i, bid in enumerate(to_download):
            if self._stop: break
            self.progress.emit(i, total)
            
            url = f"https://osu.ppy.sh/beatmapsets/{bid}/download" + ("?noVideo=1" if self.no_video else "")
            self.log.emit(f"[INFO] [{i+1}/{total}] Requesting remote ID {bid} from primary server...")
            osz_path = os.path.join(self.songs_folder, f"{bid}.tmp_osz")
            download_success = False

            try:
                resp = session.get(url, stream=True, timeout=15, allow_redirects=True)
                is_html = "text/html" in resp.headers.get("Content-Type", "")
                if resp.status_code == 200 and not is_html:
                    with open(osz_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            if self._stop: break
                            f.write(chunk)
                    if not self._stop and os.path.exists(osz_path) and zipfile.is_zipfile(osz_path):
                        download_success = True
                        self.log.emit("  [INFO] Download completed from primary server database.")
            except Exception as e:
                self.log.emit(f"  [DEBUG] Primary server link dropped connection: {e}")

            #Community Mirror
            if not download_success and not self._stop:
                mirrors = [
                    f"https://api.nerinyan.moe/d/{bid}" + ("?nv=1" if self.no_video else ""),
                    f"https://catboy.best/d/{bid}",
                    f"https://txy1.sayobot.cn/beatmaps/download/full/{bid}"
                ]
                for m_url in mirrors:
                    if self._stop: break
                    domain = m_url.split('/')[2]
                    try:
                        m_resp = requests.get(m_url, headers={"User-Agent": "osu-downloader/1.0"}, stream=True, timeout=15)
                        if m_resp.status_code == 200 and not "text/html" in m_resp.headers.get("Content-Type", ""):
                            with open(osz_path, "wb") as f:
                                for chunk in m_resp.iter_content(chunk_size=8192):
                                    if self._stop: break
                                    f.write(chunk)
                            if not self._stop and os.path.exists(osz_path) and zipfile.is_zipfile(osz_path):
                                download_success = True
                                self.log.emit(f"  [INFO] Download completed from mirror network domain: {domain}")
                                break
                    except: pass
                    if os.path.exists(osz_path): os.remove(osz_path)

            if self._stop:
                if os.path.exists(osz_path): os.remove(osz_path)
                break

            if download_success:
                folder_name = bid
                try:
                    with zipfile.ZipFile(osz_path, 'r') as z:
                        osu_files = [f for f in z.namelist() if f.endswith('.osu')]
                        if osu_files:
                            with z.open(osu_files[0]) as f:
                                content = f.read().decode('utf-8', errors='ignore')
                                artist, title = "", ""
                                for line in content.splitlines():
                                    if line.startswith("Artist:"): artist = line.split(":", 1)[1].strip()
                                    elif line.startswith("Title:"): title = line.split(":", 1)[1].strip()
                                    if artist and title: break
                                if artist or title:
                                    folder_name = re.sub(r'[\\/*?:"<>|]', "", f"{bid} {artist} - {title}".strip())
                except: pass

                extract_dir = os.path.join(self.songs_folder, folder_name)
                try:
                    with zipfile.ZipFile(osz_path, 'r') as z: z.extractall(extract_dir)
                    os.remove(osz_path)
                    self.log.emit(f"  [SUCCESS] Extraction completed to destination: {os.path.basename(extract_dir)}/")
                except Exception as e:
                    self.log.emit(f"  [ERROR] Archive decompress operations failed: {e}")
                    if os.path.exists(osz_path): os.remove(osz_path)
            else:
                self.log.emit(f"  [ERROR] Execution batch for element ID {bid} failed across all available mirrors.")

        self.progress.emit(total, total)
        self.finished.emit()


class ScanWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(set)

    def __init__(self, songs_folder):
        super().__init__()
        self.songs_folder = songs_folder

    def run(self):
        found = set()
        try:
            for entry in os.scandir(self.songs_folder):
                if entry.is_dir():
                    m = re.match(r'^(\d+)', entry.name)
                    if m: found.add(m.group(1))
        except Exception as e:
            self.log.emit(f"[ERROR] Directory scan operation failure: {e}")
        self.done.emit(found)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("osu!importer")
        self.setMinimumSize(800, 800)
        self.config = load_config()
        self.existing_ids = set()
        self.worker = None
        self._scan_worker = None
        self._build_ui()
        self._apply_theme()
        self._load_settings()

    def _build_ui(self):
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        #--1
        self.tab1_widget = QWidget()
        t1_layout = QVBoxLayout(self.tab1_widget)
        t1_layout.setSpacing(10)
        t1_layout.setContentsMargins(14, 14, 14, 14)

        auth_group = QGroupBox("Authentication Profiles")
        auth_lay = QVBoxLayout(auth_group)
        
        token_lay = QHBoxLayout()
        token_lay.addWidget(QLabel("Client Secret:"))
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.show_token_btn = QPushButton("Show")
        self.show_token_btn.setCheckable(True)
        self.show_token_btn.toggled.connect(lambda c: (self.token_input.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password), self.show_token_btn.setText("Hide" if c else "Show")))
        token_lay.addWidget(self.token_input)
        token_lay.addWidget(self.show_token_btn)
        auth_lay.addLayout(token_lay)

        cookie_lay = QHBoxLayout()
        cookie_lay.addWidget(QLabel("Session Cookie:"))
        self.cookie_input = QLineEdit()
        self.cookie_input.setEchoMode(QLineEdit.Password)
        self.show_cookie_btn = QPushButton("Show")
        self.show_cookie_btn.setCheckable(True)
        self.show_cookie_btn.toggled.connect(lambda c: (self.cookie_input.setEchoMode(QLineEdit.Normal if c else QLineEdit.Password), self.show_cookie_btn.setText("Hide" if c else "Show")))
        cookie_lay.addWidget(self.cookie_input)
        cookie_lay.addWidget(self.show_cookie_btn)
        auth_lay.addLayout(cookie_lay)
        t1_layout.addWidget(auth_group)

        folder_group = QGroupBox("Target Songs Directory Location")
        folder_lay = QHBoxLayout(folder_group)
        self.folder_input = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_folder)
        folder_lay.addWidget(self.folder_input)
        folder_lay.addWidget(browse_btn)
        t1_layout.addWidget(folder_group)

        id_group = QGroupBox("Beatmapset Indexed Queue (Numeric IDs)")
        id_lay = QVBoxLayout(id_group)
        id_btn_row = QHBoxLayout()
        import_btn = QPushButton("Import List From File")
        import_btn.clicked.connect(self._import_ids)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.id_input.clear())
        id_btn_row.addWidget(import_btn)
        id_btn_row.addWidget(clear_btn)
        id_btn_row.addStretch()

        self.id_input = QTextEdit()
        self.id_input.setFixedHeight(100)
        id_lay.addLayout(id_btn_row)
        id_lay.addWidget(self.id_input)
        t1_layout.addWidget(id_group)

        opt_group = QGroupBox("Execution Options")
        opt_lay = QHBoxLayout(opt_group)
        self.no_video_cb = QCheckBox("No Video Downloads")
        self.skip_existing_cb = QCheckBox("Skip Existing")
        scan_btn = QPushButton("Index Target Folder")
        scan_btn.clicked.connect(self._scan_folder)
        self.scan_status = QLabel("Status: Unindexed")
        opt_lay.addWidget(self.no_video_cb)
        opt_lay.addWidget(self.skip_existing_cb)
        opt_lay.addWidget(scan_btn)
        opt_lay.addWidget(self.scan_status)
        opt_lay.addStretch()
        t1_layout.addWidget(opt_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Waiting...")
        t1_layout.addWidget(self.progress_bar)

        btn_row = QHBoxLayout()
        self.download_btn = QPushButton("Execute Download Queue")
        self.download_btn.setFixedHeight(34)
        self.download_btn.clicked.connect(self._start_download)
        self.stop_btn = QPushButton("Abort Process")
        self.stop_btn.setFixedHeight(34)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_download)
        btn_row.addWidget(self.download_btn)
        btn_row.addWidget(self.stop_btn)
        t1_layout.addLayout(btn_row)

        log_group = QGroupBox("System Log Console")
        log_lay = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(120)
        self.log_view.setFont(QFont("Consolas", 9))
        log_lay.addWidget(self.log_view)
        t1_layout.addWidget(log_group)

        self.tab2_widget = ReplayTab(self.config)
        self.tab2_widget.log_signal.connect(self._log)

        self.tab3_widget = GameDataTab(self.config)
        self.tab3_widget.log_signal.connect(self._log)

        self.tab_widget.addTab(self.tab1_widget, "Beatmap")
        self.tab_widget.addTab(self.tab2_widget, "Replay Metadata")
        self.tab_widget.addTab(self.tab3_widget, "Replay")
        
        self.tab_widget.currentChanged.connect(lambda idx: self.tab3_widget.load_saved_path() if idx == 2 else None)

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #1a1a2e; color: #e0e0e0; }
            QTabWidget::pane { border: 1px solid #3a3a5c; background-color: #1a1a2e; }
            QTabBar::tab { background-color: #24243e; border: 1px solid #3a3a5c; padding: 8px 14px; min-width: 140px; font-weight: bold; color: #a0a0c0; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #2d2b55; color: #c0b0ff; border-bottom-color: #2d2b55; }
            QTabBar::tab:hover { background-color: #2d2b55; color: #fff; }
            QGroupBox { border: 1px solid #3a3a5c; border-radius: 6px; margin-top: 8px; padding: 8px; font-weight: bold; color: #c0b0ff; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QLineEdit, QTextEdit { background-color: #0f0f23; border: 1px solid #3a3a5c; border-radius: 4px; padding: 4px 6px; color: #e0e0e0; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #7c5cbf; }
            QPushButton { background-color: #2d2b55; border: 1px solid #4a3a8a; border-radius: 4px; padding: 5px 12px; color: #e0e0e0; min-height: 22px; }
            QPushButton:hover { background-color: #3d3b75; }
            QPushButton:pressed { background-color: #7c5cbf; }
            QPushButton:disabled { color: #555; border-color: #333; background-color: #1e1e3a; }
            QPushButton#download_btn { background-color: #4a2d8a; font-weight: bold; }
            QPushButton#download_btn:hover { background-color: #6040aa; }
            QProgressBar { border: 1px solid #3a3a5c; border-radius: 4px; background: #0f0f23; text-align: center; color: #e0e0e0; font-weight: bold; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a2d8a, stop:1 #c060ff); border-radius: 3px; }
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #4a3a8a; border-radius: 3px; background: #0f0f23; }
            QCheckBox::indicator:checked { background: #7c5cbf; }
        """)
        self.download_btn.setObjectName("download_btn")

    def _load_settings(self):
        self.token_input.setText(self.config.get("token", ""))
        self.cookie_input.setText(self.config.get("cookie", ""))
        self.folder_input.setText(self.config.get("songs_folder", ""))
        self.id_input.setPlainText(self.config.get("inputted_ids", ""))
        self.no_video_cb.setChecked(self.config.get("no_video", False))
        self.skip_existing_cb.setChecked(self.config.get("skip_existing", True))
        self.existing_ids = set(str(i) for i in self.config.get("scanned_ids", []))
        if self.existing_ids: self.scan_status.setText(f"Status: {len(self.existing_ids)} Indexed")
        self.tab3_widget.load_saved_path()

    def _save_settings(self):
        self.config["token"] = self.token_input.text().strip()
        self.config["cookie"] = self.cookie_input.text().strip()
        self.config["songs_folder"] = self.folder_input.text().strip()
        self.config["inputted_ids"] = self.id_input.toPlainText()
        self.config["no_video"] = self.no_video_cb.isChecked()
        self.config["skip_existing"] = self.skip_existing_cb.isChecked()
        self.config["scanned_ids"] = sorted(list(self.existing_ids))
        save_config(self.config)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Songs Directory Target Location")
        if folder:
            self.folder_input.setText(folder)
            self._save_settings()
            self.tab3_widget.load_saved_path()

    def _import_ids(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Identifier Manifest File", "", "Text Manifests (*.txt);;All Streams (*)")
        if path:
            try:
                with open(path) as f: text = f.read()
                self.id_input.setPlainText((self.id_input.toPlainText().strip() + "\n" + text).strip())
            except Exception as e: self._log(f"[ERROR] Import module crash: {e}")

    def _scan_folder(self):
        folder = self.folder_input.text().strip()
        if not folder or not os.path.isdir(folder): return
        self.scan_status.setText("Status: Scanning...")
        self._scan_worker = ScanWorker(folder)
        self._scan_worker.done.connect(lambda ids: (setattr(self, 'existing_ids', ids), self.scan_status.setText(f"Status: {len(ids)} Indexed"), self._save_settings()))
        self._scan_worker.start()

    def _start_download(self):
        folder = self.folder_input.text().strip()
        raw_ids = self.id_input.toPlainText().strip()
        if not folder or not os.path.isdir(folder) or not raw_ids: return

        ids = [m.group(1) for line in raw_ids.splitlines() if (m := re.match(r'^(\d+)', line.strip()))]
        if not ids: return

        self._save_settings()
        self.download_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(ids))

        self.worker = DownloadWorker(ids, folder, self.token_input.text(), self.cookie_input.text(), self.no_video_cb.isChecked(), self.skip_existing_cb.isChecked(), self.existing_ids)
        self.worker.log.connect(self._log)
        self.worker.progress.connect(lambda cur, tot: (self.progress_bar.setMaximum(tot), self.progress_bar.setValue(cur)))
        self.worker.finished.connect(self._on_download_finished)
        self.worker.start()

    def _stop_download(self):
        if self.worker: self.worker.stop()

    def _on_download_finished(self):
        self.download_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.worker and (self.worker._stop or self.progress_bar.value() == 0):
            self.progress_bar.setFormat("Waiting...")
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setValue(self.progress_bar.maximum())
            self.progress_bar.setFormat("Done!")

    def _log(self, msg):
        self.log_view.append(msg)
        self.log_view.moveCursor(QTextCursor.End)

    def closeEvent(self, event):
        self._save_settings()
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning(): self.worker.stop(); self.worker.wait()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())