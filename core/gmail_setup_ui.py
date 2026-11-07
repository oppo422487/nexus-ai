"""Native OAuth setup with actionable status, no credentials in logs."""
from threading import Thread
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QLabel,QPushButton,QFileDialog
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from core import gmail_service as gmail


class Result(QObject):
    done = pyqtSignal(bool,str)


class GmailSetup(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Nexa — Gmail setup')
        self.setMinimumWidth(520)
        self.setStyleSheet('QDialog{background:#17131f;color:#eee5f5;} QLabel{color:#ddd0e8;} QPushButton{background:#30233e;color:#ead8ff;border:1px solid #594068;border-radius:7px;padding:10px;} QPushButton:disabled{color:#82718e;}')
        layout=QVBoxLayout(self)
        intro=QLabel('1. Enable Gmail API in Google Cloud.\n2. Download the Desktop app OAuth client JSON.\n3. Select the JSON file and connect your Google account.\n\nA Gemini API key cannot connect Gmail.')
        intro.setWordWrap(True);layout.addWidget(intro)
        help_button=QPushButton('Open Google Gmail setup guide')
        help_button.clicked.connect(lambda:QDesktopServices.openUrl(QUrl('https://developers.google.com/workspace/gmail/api/quickstart/python')))
        layout.addWidget(help_button)
        self.choose=QPushButton('Choose OAuth JSON file');self.choose.clicked.connect(self.import_file);layout.addWidget(self.choose)
        self.status=QLabel('Client JSON is available.' if gmail.CLIENT.exists() else 'Client JSON is missing. Choose the file first.')
        self.status.setWordWrap(True);layout.addWidget(self.status)
        self.connect_button=QPushButton('Connect Google account');self.connect_button.clicked.connect(self.connect_account);layout.addWidget(self.connect_button)
        self.signal=Result(self);self.signal.done.connect(self.finished_connect)
        self.busy=False

    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Google Desktop OAuth JSON','','JSON (*.json)')
        if not path:return
        try:
            gmail.import_client(path)
            self.status.setText('OAuth client saved. Now connect your Google account.')
        except Exception as exc:
            self.status.setText(str(exc) if isinstance(exc,ValueError) else 'Could not read JSON. Choose a valid Desktop OAuth JSON file.')

    def connect_account(self):
        if not gmail.CLIENT.exists():
            self.status.setText('Choose the Desktop OAuth JSON file first.');return
        if self.busy:return
        self.busy=True;self.connect_button.setEnabled(False);self.choose.setEnabled(False)
        self.status.setText('Complete Google sign-in in your browser. This may wait up to 3 minutes.')
        def work():
            try:self.signal.done.emit(True,str(gmail.connect()))
            except Exception as exc:
                kind=type(exc).__name__
                code=getattr(getattr(exc,'resp',None),'status',None)
                msg='Connection failed ('+kind+(f', HTTP {code}' if code else '')+')। '
                msg+='Check Gmail API, OAuth test users and Google consent. Connect again if authorization expired or was cancelled.'
                self.signal.done.emit(False,msg)
        Thread(target=work,daemon=True).start()

    def finished_connect(self,ok,message):
        self.busy=False;self.connect_button.setEnabled(True);self.choose.setEnabled(True)
        self.status.setText('Gmail connected: '+message+'\nAsk Nexa to show your unread mail to check your inbox.' if ok else message)

    def closeEvent(self,event):
        if self.busy:
            self.status.setText('Google sign-in is in progress. Finish in your browser or wait for the 3-minute timeout.')
            event.ignore()
        else:super().closeEvent(event)

    def reject(self):
        if not self.busy:
            super().reject()
