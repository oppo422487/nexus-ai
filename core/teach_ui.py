"""English native Qt teaching controls; all work is opt-in and reviewable."""
from threading import Thread
import json
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit, QMessageBox, QDialogButtonBox)
from core import teach_mode as teach
from plugins.nexa_teach import review_text


class TeachPanel(QWidget):
    done = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.busy = False
        self.items = []
        self.current = None
        layout = QVBoxLayout(self); layout.setContentsMargins(20,20,20,20); layout.setSpacing(12)
        intro = QLabel('1. Name a routine and start teaching.\n2. Ask Nexa to perform each step in chat or by voice.\n3. Finish teaching, review the saved steps, then run when needed.')
        intro.setWordWrap(True); layout.addWidget(intro)
        note = QLabel('Records Nexa tool actions only. No screen, mouse, keyboard or microphone recording is added.\nSupported: open apps/folders, read/search files, web search, documents, Excel, translation and backups.\nOther actions are skipped and reported. Saved arguments are reused until edited.')
        note.setWordWrap(True); layout.addWidget(note)
        self.name = QLineEdit(); self.name.setPlaceholderText('Routine name, e.g. Weekly report review'); layout.addWidget(self.name)
        row = QHBoxLayout()
        self.start_button = QPushButton('Start teaching'); self.start_button.clicked.connect(self.start)
        self.finish_button = QPushButton('Finish && save'); self.finish_button.clicked.connect(self.finish)
        row.addWidget(self.start_button); row.addWidget(self.finish_button); layout.addLayout(row)
        self.recording = QLabel(); self.recording.setWordWrap(True); layout.addWidget(self.recording)
        self.list = QListWidget(); self.list.setFixedHeight(110); self.list.currentRowChanged.connect(self.select); layout.addWidget(self.list)
        actions = QHBoxLayout()
        self.refresh_button = QPushButton('Refresh'); self.refresh_button.clicked.connect(self.refresh)
        self.run_button = QPushButton('Review && run'); self.run_button.clicked.connect(self.run_selected)
        self.discard_button = QPushButton('Discard routine'); self.discard_button.clicked.connect(self.discard)
        for button in (self.refresh_button,self.run_button,self.discard_button): actions.addWidget(button)
        layout.addLayout(actions)
        self.history_button = QPushButton('Show last run results'); self.history_button.clicked.connect(self.history)
        layout.addWidget(self.history_button)
        self.steps = QListWidget(); self.steps.setFixedHeight(125); layout.addWidget(self.steps)
        edits = QHBoxLayout()
        self.edit_button = QPushButton('Edit selected step'); self.edit_button.clicked.connect(self.edit)
        self.remove_button = QPushButton('Remove selected step'); self.remove_button.clicked.connect(self.remove)
        self.stop_button = QPushButton('Stop running routine'); self.stop_button.clicked.connect(self.stop)
        for button in (self.edit_button,self.remove_button,self.stop_button): edits.addWidget(button)
        layout.addLayout(edits)
        self.output = QTextEdit(); self.output.setReadOnly(True); self.output.setFixedHeight(130); layout.addWidget(self.output)
        self.buttons = [self.start_button,self.finish_button,self.refresh_button,self.run_button,self.discard_button,self.edit_button,self.remove_button,self.history_button]
        self.done.connect(self.completed); self.progress.connect(self.output.setPlainText)
        self.refresh()

    def refresh(self):
        active = teach.status()
        self.recording.setText(('Recording: '+active['title']+' — '+str(len(active['payload']['steps']))+' steps') if active.get('id') else 'Teaching is off. Choose a routine or start a new one.')
        selected = self.current['id'] if self.current else None
        self.items = teach.workflows()
        self.list.blockSignals(True); self.list.clear()
        for item in self.items:
            self.list.addItem(f'{item["title"]} — {item["status"]} — {len(item["payload"]["steps"])} steps')
        self.list.blockSignals(False)
        row = next((i for i,x in enumerate(self.items) if x['id']==selected), 0 if self.items else -1)
        self.list.setCurrentRow(row)
        if row < 0:
            self.current = None; self.steps.clear()

    def select(self, row):
        if not 0 <= row < len(self.items): return
        self.current = teach.preview(self.items[row]['id'])
        self.steps.clear()
        for i, step in enumerate(self.current['steps'],1):
            args = '; '.join(f'{k}: {v}' for k,v in step['args'].items())
            self.steps.addItem(f'{i}. {step["tool"]} — {args[:250]}')
        skipped = self.current.get('skipped',[])
        if skipped:
            self.output.setPlainText('Not recorded:\n'+'\n'.join(x['tool']+': '+x['reason'] for x in skipped))

    def work(self, callback):
        if self.busy: return
        self.busy = True
        for button in self.buttons: button.setEnabled(False)
        def worker():
            try: result = json.dumps(callback(),ensure_ascii=False,indent=2,default=str)
            except Exception as exc: result = str(exc)[:600] if isinstance(exc,ValueError) else 'Teach mode failed ('+type(exc).__name__+'). No automatic retry.'
            self.done.emit(result)
        Thread(target=worker,daemon=True,name='Nexa-teach-operation').start()

    def completed(self, result):
        self.busy = False
        for button in self.buttons: button.setEnabled(True)
        self.refresh(); self.output.setPlainText(result)

    def start(self):
        name = self.name.text()
        self.work(lambda: teach.start(name))

    def finish(self):
        active = teach.status()
        key = active.get('id') or (self.current['id'] if self.current else '')
        self.work(lambda: teach.finish(key))

    def history(self):
        if not self.current: return
        from core import life_store
        rows = [x for x in life_store.records('taught_run',limit=100) if x['payload'].get('workflow_id')==self.current['id']]
        self.output.setPlainText(json.dumps(rows[:5],ensure_ascii=False,indent=2,default=str) if rows else 'No previous runs for this routine.')

    def stop(self):
        self.output.setPlainText(teach.request_stop())

    def discard(self):
        if not self.current: return
        key = self.current['id']
        if QMessageBox.question(self,'Discard routine','Discard this saved routine and its recorded steps?') == QMessageBox.StandardButton.Yes:
            self.work(lambda: teach.discard(key))

    def run_selected(self):
        if not self.current: return
        snapshot = teach.preview(self.current['id'])
        if snapshot['status'] != 'ready':
            self.output.setPlainText('Finish teaching before running this routine.'); return
        dialog = QDialog(self); dialog.setWindowTitle('Review taught workflow'); dialog.resize(700,530)
        layout = QVBoxLayout(dialog)
        content = QTextEdit(); content.setReadOnly(True); content.setPlainText(review_text(snapshot)); layout.addWidget(content)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Run these steps')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.work(lambda: teach.run_reviewed(snapshot, self.progress.emit))

    def edit(self):
        if not self.current or self.current['status']!='ready': return
        index = self.steps.currentRow()
        if index < 0: return
        key = self.current['id']; step = self.current['steps'][index]
        dialog = QDialog(self); dialog.setWindowTitle('Edit step arguments'); dialog.resize(650,300)
        layout = QVBoxLayout(dialog); form = QFormLayout(); fields = {}
        for name,value in step['args'].items():
            entry = QLineEdit(value); fields[name] = entry; form.addRow(name.replace('_',' ').title(),entry)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            args = {k:v.text() for k,v in fields.items()}
            self.work(lambda: teach.edit_step(key,index,args))

    def remove(self):
        if self.current and self.steps.currentRow()>=0:
            key,index = self.current['id'], self.steps.currentRow()
            self.work(lambda: teach.remove_step(key,index))
