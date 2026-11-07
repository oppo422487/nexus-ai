"""Native Qt setup and inspectable local records; optional tools load on demand."""
from threading import Thread
import json
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QPushButton,
    QTextEdit, QLineEdit, QLabel, QFileDialog, QMessageBox, QComboBox)


class LifeTools(QDialog):
    finished_work = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        from core.nexa_fonts import ensure_ui_fonts
        ensure_ui_fonts()
        self.setWindowTitle('Nexa — Work & documents')
        self.setFont(QFont('Nirmala UI', 10))
        self.resize(850, 680)
        self.busy = False
        self.setStyleSheet('QWidget{background:#17151d;color:#e8e3ef;font-family:"Nirmala UI";font-size:13px;} QLineEdit,QTextEdit,QComboBox{background:#231e2c;border:1px solid #493958;padding:8px;} QPushButton{background:#342840;border:1px solid #544264;padding:9px;border-radius:6px;} QPushButton:disabled{color:#807488;}')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Reminders and monitors run while Nexa is open. Overdue items are checked on the next launch.'))
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.buttons = []
        documents = QWidget(); d = QVBoxLayout(documents)
        self.language = QLineEdit('eng+ben'); d.addWidget(QLabel('OCR languages')); d.addWidget(self.language)
        self.button(d, 'Add a document or scanned PDF to archive', self.index_file)
        self.query = QLineEdit(); self.query.setPlaceholderText('Search your information…'); d.addWidget(self.query)
        self.button(d, 'Find evidence and source files', lambda: self.search(False))
        self.button(d, 'Answer with evidence', lambda: self.search(True))
        self.button(d, 'List archived documents', lambda: self.run(lambda: self.docs().documents()))
        self.button(d, 'Read Excel (first sheet, A1:T50)', self.read_excel)
        self.button(d, 'Search work memory', self.find_memory)
        d.addStretch(); tabs.addTab(documents, 'Documents & memory')
        tasks = QWidget(); t = QVBoxLayout(tasks)
        self.kind = QComboBox(); self.kind.addItems(['followup', 'job', 'meeting', 'monitor', 'change', 'backup', 'calendar_request']); t.addWidget(self.kind)
        self.button(t, 'View saved tasks and results', self.records)
        t.addWidget(QLabel('Try: "Remind me about this task tomorrow at 10", "Extract tasks from this meeting",\nor "Notify me when this page changes". You can also create multi-step jobs.\nUse the task ID to update, pause or resume a task.'))
        self.button(t, 'Analyze meeting transcript', self.meeting)
        self.button(t, 'Transcribe selected audio (local model required)', self.audio)
        t.addStretch(); tabs.addTab(tasks, 'Tasks & monitors')
        backup = QWidget(); b = QVBoxLayout(backup)
        b.addWidget(QLabel('Backup limit: 500 MB / 3000 files. ZIP archives are not encrypted.\nRestore uses a new folder and never overwrites existing files.'))
        self.button(b, 'Create verified folder backup', self.backup)
        self.button(b, 'Verify backup and restore to a new folder', self.restore)
        b.addStretch(); tabs.addTab(backup, 'Backups')
        connections = QWidget(); c = QVBoxLayout(connections)
        c.addWidget(QLabel('Enable Calendar API in Google Cloud. The Desktop OAuth JSON from Gmail setup is reused.'))
        self.button(c, 'Connect Google Calendar', self.connect_calendar)
        c.addWidget(QLabel('Spotify Premium and an active player are required. Redirect URI: http://127.0.0.1:8888/callback'))
        self.client_id = QLineEdit(); self.client_id.setPlaceholderText('Spotify client ID'); c.addWidget(self.client_id)
        self.secret = QLineEdit(); self.secret.setPlaceholderText('Spotify client secret'); self.secret.setEchoMode(QLineEdit.EchoMode.Password); c.addWidget(self.secret)
        self.button(c, 'Save Spotify settings and connect', self.connect_spotify)
        self.button(c, 'Check setup status', self.check_status)
        c.addStretch(); tabs.addTab(connections, 'Connections')
        models = QWidget(); m = QVBoxLayout(models)
        m.addWidget(QLabel('Offline translation needs an installed language model. There is no cloud fallback.\nChoose an official Argos .argosmodel file. Meeting audio requires Whisper small.'))
        self.button(m, 'Import offline translation model', self.import_model)
        self.button(m, 'Download Bengali ↔ English models (~140 MB)', self.download_bengali)
        self.button(m, 'View installed translation pairs', self.list_languages)
        self.button(m, 'Download Whisper small model (~500 MB)', self.download_whisper)
        m.addStretch(); tabs.addTab(models, 'Offline models')
        self.output = QTextEdit(); self.output.setReadOnly(True); self.output.setMinimumHeight(220); layout.addWidget(self.output)
        self.finished_work.connect(self.done)
        self.check_status()

    def button(self, layout, title, callback):
        button = QPushButton(title); button.clicked.connect(callback); layout.addWidget(button); self.buttons.append(button)

    def run(self, callback):
        if self.busy:
            return
        self.busy = True
        for button in self.buttons:
            button.setEnabled(False)
        self.output.setPlainText('Working…')
        def worker():
            try:
                result = json.dumps(callback(), ensure_ascii=False, indent=2, default=str)
            except Exception as exc:
                # Never display raw HTTP errors which can contain authorization data.
                result = ('Task did not complete: '+str(exc)[:800]) if isinstance(exc, (ValueError, ImportError, FileNotFoundError)) else ('Task did not complete ('+type(exc).__name__+'). Check connection or model setup.')
            self.finished_work.emit(result)
        Thread(target=worker, daemon=True).start()

    def done(self, result):
        self.busy = False
        self.output.setPlainText(result)
        for button in self.buttons:
            button.setEnabled(True)

    def closeEvent(self, event):
        if self.busy:
            event.ignore()
        else:
            event.accept()

    def reject(self):
        if not self.busy:
            super().reject()

    @staticmethod
    def docs():
        from core import document_archive
        return document_archive

    def index_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose a document', '', 'Documents (*.pdf *.docx *.txt *.md *.csv *.png *.jpg *.jpeg *.tif *.tiff)')
        if path:
            language = self.language.text().strip()
            self.run(lambda: self.docs().index(path, language))

    def read_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose an Excel file', '', 'Excel (*.xlsx *.xlsm)')
        if path:
            from core.excel_adapter import read
            self.run(lambda: read(path))

    def find_memory(self):
        from core.life_store import find_activity
        query = self.query.text()
        self.run(lambda: find_activity(query))

    def search(self, answer=False):
        query = self.query.text()
        self.run(lambda: self.docs().answer(query) if answer else self.docs().search(query))

    def records(self):
        from core.life_store import records
        kind = self.kind.currentText()
        self.run(lambda: records(kind))

    def backup(self):
        source = QFileDialog.getExistingDirectory(self, 'Choose the folder to back up')
        if not source:
            return
        dest = QFileDialog.getExistingDirectory(self, 'Choose a separate backup destination')
        if dest:
            from core.safe_backup import backup
            self.run(lambda: backup(source, dest))

    def restore(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Nexa backup', '', 'Nexa backup (*.nexa.zip)')
        if not path:
            return
        from pathlib import Path
        parent = QFileDialog.getExistingDirectory(self, 'Choose the parent folder for a new restore')
        if parent:
            from core.safe_backup import restore
            from datetime import datetime
            dest = str(Path(parent)/('Nexa-restored-'+datetime.now().strftime('%Y%m%d-%H%M%S')))
            self.run(lambda: restore(path, dest))

    def meeting(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Meeting transcript', '', 'Transcript (*.txt *.md *.docx *.pdf)')
        if path:
            from core.life_workflows import meeting_preview
            language = self.language.text().strip()
            self.run(lambda: meeting_preview('\n'.join(p['text'] for p in self.docs().extract(path, language)['pages']), path))

    def audio(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Meeting audio', '', 'Audio (*.wav *.mp3 *.m4a *.ogg *.flac *.mp4)')
        if path:
            from core.life_connectors import transcribe
            self.run(lambda: transcribe(path))

    def connect_calendar(self):
        from core.life_connectors import calendar
        self.run(lambda: {'connected': bool(calendar(True))})

    def connect_spotify(self):
        from core.life_connectors import save_spotify, spotify
        client_id, secret = self.client_id.text(), self.secret.text()
        def connect():
            save_spotify(client_id, secret)
            return {'connected': bool(spotify(True))}
        self.secret.clear()
        self.run(connect)

    def check_status(self):
        from plugins.nexa_life import status
        self.run(status)

    def list_languages(self):
        from core.life_connectors import offline_languages
        self.run(offline_languages)

    def import_model(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Official Argos model', '', 'Argos (*.argosmodel)')
        if path:
            from core.life_connectors import install_translation_model
            self.run(lambda: install_translation_model(path))

    def download_whisper(self):
        if QMessageBox.question(self, 'Model download', 'Download Whisper small now? This requires about 500 MB of storage and internet data.') != QMessageBox.StandardButton.Yes:
            return
        def download():
            from faster_whisper.utils import download_model
            return {'model_path': download_model('small')}
        self.run(download)

    def download_bengali(self):
        if QMessageBox.question(self, 'Model download', 'Download official Argos Bengali ↔ English models now? About 140 MB of internet data is required.') != QMessageBox.StandardButton.Yes:
            return
        from core.life_connectors import download_bengali_models
        self.run(download_bengali_models)
