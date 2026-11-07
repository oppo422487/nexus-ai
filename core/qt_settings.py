"""One native settings window around the existing, unchanged settings forms."""
from PyQt6.QtCore import Qt, QEvent, QObject, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QStackedWidget, QScrollArea,
    QSizePolicy, QFrame, QAbstractButton, QLayout, QComboBox, QLineEdit)

STYLE = '''
QDialog#NexaSettings { background:#111015; color:#eee7f5; }
QWidget { color:#e5ddec; font-family:"Nirmala UI"; font-size:13px; }
QWidget#SettingsNavigation { background:#19151f; border-right:1px solid #302738; }
QLabel { background:transparent; border:0; }
QLabel#SettingsBrand { color:#f3ebfa; font-size:24px; font-weight:600; }
QLabel#SettingsTitle { color:#f1e7fa; font-size:24px; font-weight:600; }
QLabel#SettingsDescription { color:#ac9cb8; font-size:12px; }
QLabel#SettingsFooter { color:#9b89aa; font-size:12px; }
QListWidget { background:transparent; border:0; outline:0; padding:0; }
QListWidget::item { color:#b7a8c4; border-radius:8px; padding:10px 12px; margin:3px 0; }
QListWidget::item:selected { background:#352740; color:#e6caff; }
QListWidget::item:hover { background:#292131; }
QStackedWidget,QScrollArea,QScrollArea>QWidget>QWidget { background:#111015; border:0; }
QWidget[settingsForm="true"] { background:#17131d; border:1px solid #33283e; border-radius:12px; }
QLineEdit,QTextEdit,QPlainTextEdit,QComboBox,QSpinBox,QDoubleSpinBox {
  background:#241d2c; color:#efe4fa; border:1px solid #4d3b5d; border-radius:6px;
  padding:7px 9px; selection-background-color:#775a94; }
QLineEdit:focus,QTextEdit:focus,QComboBox:focus { border:1px solid #bd9de6; }
QLineEdit:disabled,QComboBox:disabled { color:#8f7d9f; background:#1c1822; }
QComboBox QAbstractItemView { background:#292032; color:#f1e6fc; selection-background-color:#513663; }
QPushButton { background:#2d2337; color:#ddcce9; border:1px solid #503c60;
  border-radius:7px; padding:7px 12px; min-height:22px; }
QPushButton:hover { background:#41304f; border-color:#9774b5; }
QPushButton:pressed { background:#50365e; }
QPushButton:checked,QPushButton[active="true"] { background:#593b71; border-color:#b995df; color:#f7e9ff; }
QPushButton:disabled { color:#82718e; border-color:#352b3e; background:#211b27; }
QPushButton#SettingsClose { background:#c3a2ed; color:#24142e; font-weight:600; }
QCheckBox,QRadioButton { color:#dbcce6; background:transparent; spacing:8px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #725986; border-radius:4px; background:#251c2e; }
QCheckBox::indicator:checked { background:#ba95e6; }
QGroupBox { border:1px solid #42334e; border-radius:8px; margin-top:16px; padding:12px; }
QGroupBox::title { subcontrol-origin:margin; left:12px; color:#d6bee9; }
QTabWidget::pane { border:1px solid #45334f; background:#17131d; border-radius:6px; }
QTabBar::tab { background:#241c2d; color:#b9a6c8; padding:9px 12px; border:0; }
QTabBar::tab:selected { background:#493157; color:#f0d8ff; }
QProgressBar { background:#231b2b; border:1px solid #493453; border-radius:4px; color:#dfcaef; }
QProgressBar::chunk { background:#ac81da; }
QSlider::groove:horizontal { background:#3c2c48; height:5px; border-radius:2px; }
QSlider::handle:horizontal { background:#c5a0f0; width:15px; margin:-5px 0; border-radius:7px; }
QScrollBar:vertical { background:#1b1621; width:9px; margin:0; }
QScrollBar::handle:vertical { background:#5b456b; min-height:24px; border-radius:4px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:transparent; }
'''

PAGES = [
    ('general', 'General', 'Everyday app preferences and startup options.'),
    ('identity', 'Assistant & voice', 'Choose a name, how you are addressed, and the assistant voice.'),
    ('audio', 'Audio devices', 'Choose and test your microphone and speakers.'),
    ('voice', 'Voice controls', 'Manage speaking, wake word and startup briefing.'),
    ('providers', 'Engine & providers', 'Connection and model settings. Opening this page changes nothing.'),
    ('plugins', 'Plugins', 'View installed features and enable or disable them.'),
    ('plugin_settings', 'Plugin settings', 'Configure plugins that provide their own settings.'),
    ('memory', 'Memory', 'Review what your assistant remembers.'),
    ('gmail', 'Gmail connection', 'Connect Gmail using your Google account.'),
    ('tools', 'Work & documents', 'Documents, backups, tasks, offline models and connections.'),
    ('teach', 'Teach mode', 'Teach Nexa a routine through your tool requests, then review and replay it.'),
    ('whatsapp_calls', 'WhatsApp calls', 'Timed incoming replies, per-caller messages, caller notes and virtual audio routing.'),
    ('screen_guide', 'Screen Guide', 'Understand the current screen and get read-only visual guidance.'),
    ('remote', 'Remote access', 'Connect to the existing remote dashboard.'),
]

TRANSLATIONS = {
    'CLOSE':'Close', 'CANCEL':'Cancel', 'APPLY':'Apply', '▸  APPLY':'Apply',
    '▸  SAVE':'Save', '▸  SAVE  &  APPLY':'Save & apply',
    '▸  APPLY CHANGES':'Apply changes', 'APPLY CHANGES':'Apply changes',
    'DEFAULT':'Default', 'ASSISTANT NAME':'Assistant name',
    'YOUR NAME  (leave blank for default sir / efendim)':'Your name (optional)',
    'ASSISTANT VOICE':'Assistant voice', 'UI COLOUR  —  drag the handle':'Interface color',
    '🧩  PLUGIN MANAGER':'Installed plugins', '🔌  ENGINE  &  PROVIDERS':'Engine & providers',
}


class SettingsPolish(QObject):
    """Restyle legacy forms after their own dynamic refresh without changing slots."""
    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.pending = False
        self.applying = False

    def eventFilter(self, obj, event):
        if not self.applying and event.type() in (QEvent.Type.ChildAdded, QEvent.Type.StyleChange, QEvent.Type.Show):
            self.schedule()
        if event.type() == QEvent.Type.Hide and obj in self.host.forms.values():
            if obj.isHidden() and self.host.isVisible() and not self.host.changing:
                QTimer.singleShot(0, self.host.close)
        return False

    def schedule(self):
        if not self.pending:
            self.pending = True
            QTimer.singleShot(0, self.apply)

    def apply(self):
        self.pending = False
        self.applying = True
        try:
            for form in self.host.forms.values():
                for widget in [form, *form.findChildren(QWidget)]:
                    widget.installEventFilter(self)
                    if widget.styleSheet():
                        widget.setStyleSheet('')
                    widget.setFont(QFont('Nirmala UI', 10))
                    if isinstance(widget, (QLabel, QPushButton)):
                        original = widget.text()
                        if original in TRANSLATIONS:
                            widget.setText(TRANSLATIONS[original])
                        if isinstance(widget, QLabel):
                            widget.setWordWrap(True)
                            policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                            policy.setHeightForWidth(True)
                            widget.setSizePolicy(policy)
                        else:
                            widget.setAutoDefault(False)
                            widget.setProperty('active', 'ON' in original and 'OFF' not in original)
                            if len(widget.text()) > 95 and '\n' in widget.text() and widget.layout() is None:
                                # Qt buttons do not wrap their own text. Keep the
                                # original button/slot, and put a mouse-transparent
                                # wrapping label inside it so provider cards fit.
                                caption = QLabel(widget.text(), widget)
                                caption.setWordWrap(True)
                                caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                                policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
                                policy.setHeightForWidth(True)
                                caption.setSizePolicy(policy)
                                caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                widget.setAccessibleName(widget.text())
                                widget.setText('')
                                inner = QVBoxLayout(widget); inner.setContentsMargins(12,12,12,12); inner.addWidget(caption)
                                widget.setMinimumWidth(0)
                                widget.setMinimumHeight(150)
                                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                            elif widget.maximumHeight() < 36:
                                widget.setFixedHeight(36)
                    if isinstance(widget, QComboBox):
                        widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                        widget.setMinimumContentsLength(12)
                        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
                    if isinstance(widget, (QLineEdit, QComboBox)) and widget.maximumHeight() < 34:
                        widget.setFixedHeight(34)
        except RuntimeError:
            # A dynamic provider form can discard its old fields in this frame.
            self.schedule()
        finally:
            self.applying = False


class NativeSettings(QDialog):
    def __init__(self, win):
        super().__init__(win)
        from core.nexa_fonts import ensure_ui_fonts
        ensure_ui_fonts()
        self.win = win
        self.forms = {}
        self.views = {}
        self.changing = False
        self.current_key = ''
        self.setObjectName('NexaSettings')
        self.setWindowTitle('Nexa — Settings')
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(800, 580)
        self.resize(1080, 760)
        self.setStyleSheet(STYLE)
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        rail = QWidget(); rail.setObjectName('SettingsNavigation'); rail.setFixedWidth(222)
        nav = QVBoxLayout(rail); nav.setContentsMargins(18,25,18,20); nav.setSpacing(8)
        brand = QLabel('Nexa.'); brand.setObjectName('SettingsBrand'); nav.addWidget(brand)
        caption = QLabel('Make it yours'); caption.setObjectName('SettingsDescription'); nav.addWidget(caption)
        nav.addSpacing(18)
        self.navigation = QListWidget(); self.navigation.setAccessibleName('Settings categories'); nav.addWidget(self.navigation,1)
        for key, title, description in PAGES:
            item = QListWidgetItem(title); item.setData(Qt.ItemDataRole.UserRole, key)
            item.setToolTip(description); self.navigation.addItem(item)
        root.addWidget(rail)
        content = QVBoxLayout(); content.setContentsMargins(26,28,26,20); content.setSpacing(12)
        header = QHBoxLayout()
        self.title = QLabel(); self.title.setObjectName('SettingsTitle'); header.addWidget(self.title,1)
        close = QPushButton('Close'); close.setObjectName('SettingsClose'); close.clicked.connect(self.close); header.addWidget(close)
        content.addLayout(header)
        self.description = QLabel(); self.description.setObjectName('SettingsDescription'); self.description.setWordWrap(True); content.addWidget(self.description)
        self.stack = QStackedWidget(); content.addWidget(self.stack,1)
        self.footer = QLabel('Opening settings does not save changes.'); self.footer.setObjectName('SettingsFooter'); self.footer.setWordWrap(True); content.addWidget(self.footer)
        root.addLayout(content,1)
        self.polish = SettingsPolish(self)
        self.navigation.currentRowChanged.connect(self._row_changed)

    def _row_changed(self, row):
        if row >= 0:
            self.select(PAGES[row][0])

    def select(self, key):
        if key not in {item[0] for item in PAGES}:
            key = 'general'
        self.changing = True
        try:
            row = next(i for i, data in enumerate(PAGES) if data[0] == key)
            self.navigation.blockSignals(True); self.navigation.setCurrentRow(row); self.navigation.blockSignals(False)
            _, title, description = PAGES[row]
            self.title.setText(title); self.description.setText(description)
            if key not in self.forms:
                try:
                    form = self._create_form(key)
                    self.forms[key] = form
                    form.setWindowFlags(Qt.WindowType.Widget)
                    form.setProperty('settingsForm', True)
                    form.setMinimumWidth(0); form.setMaximumWidth(16777215)
                    form.setMinimumHeight(0); form.setMaximumHeight(16777215)
                    form.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                    if form.layout():
                        form.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
                    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
                    wrapper = QWidget()
                    wrapper_layout = QVBoxLayout(wrapper); wrapper_layout.setContentsMargins(0,0,0,0)
                    wrapper_layout.addWidget(form, 0, Qt.AlignmentFlag.AlignTop)
                    wrapper_layout.addStretch(1)
                    scroll.setWidget(wrapper); self.stack.addWidget(scroll); self.views[key] = scroll
                except Exception:
                    # No secrets/raw provider exceptions in the settings UI.
                    error = QLabel('This category could not open. Check the app log for connection or dependency details.')
                    error.setWordWrap(True)
                    self.stack.addWidget(error); self.views[key] = error
            self.current_key = key
            self.stack.setCurrentWidget(self.views[key])
            if key in self.forms:
                self.forms[key].show()
            self.polish.apply()
        finally:
            self.changing = False

    def _create_form(self, key):
        import ui
        win = self.win
        if key == 'teach':
            from core.teach_ui import TeachPanel
            return TeachPanel(self)
        if key == 'whatsapp_calls':
            from core.whatsapp_calls_ui import WhatsAppCallsPanel
            return WhatsAppCallsPanel(self)
        if key == 'screen_guide':
            from core.screen_guide_ui import ScreenGuidePanel
            return ScreenGuidePanel(win,self)
        if key == 'identity':
            cfg = ui._read_full_config()
            panel = ui.CustomizeOverlay(cfg.get('assistant_name') or 'Nexa AI', cfg.get('user_name',''),
                cfg.get('ui_color') or ui.DEFAULT_UI_COLOR, cfg.get('voice_name',''), parent=self)
            panel.on_preview = win._preview_ui_color
            panel.saved.connect(win._apply_name_update)
            return panel
        if key == 'audio':
            panel = ui.AudioDeviceOverlay(parent=self); panel.picked.connect(win._on_audio_devices_applied); return panel
        if key == 'providers':
            panel = ui.ProvidersOverlay(parent=self); panel.changed.connect(win._on_providers_applied); return panel
        if key == 'plugins':
            return ui.PluginManagerOverlay(win.get_plugins() if win.get_plugins else [], parent=self)
        if key == 'plugin_settings':
            return ui.PluginSettingsOverlay(win.get_plugin_settings() if win.get_plugin_settings else [], parent=self)
        if key == 'memory':
            return ui.MemoryOverlay(parent=self)
        if key == 'gmail':
            from core.gmail_setup_ui import GmailSetup
            return GmailSetup(self)
        if key == 'tools':
            from core.life_tools_ui import LifeTools
            return LifeTools(self)
        if key == 'remote':
            win._open_remote()
            panel = getattr(win, '_remote_overlay', None)
            if panel is None:
                panel = QLabel('Remote access is not ready. Other settings remain available.')
                panel.setWordWrap(True)
            return panel
        panel = QWidget(self); layout = QVBoxLayout(panel); layout.setContentsMargins(22,24,22,24); layout.setSpacing(14)
        if key == 'voice':
            win._refresh_wake_btns()
            win._refresh_talk_btns()
            for name in ('_brief_btn', '_wake_btn', '_wake_sleep_btn', '_ptt_btn'):
                button = getattr(win, name)
                was_hidden = button.isHidden()
                layout.addWidget(button)
                if not was_hidden:
                    button.show()
            note = QLabel('These buttons use the existing voice engine controls.'); note.setWordWrap(True); layout.addWidget(note)
        else:
            intro = QLabel('Your chat and settings share the same Nexa workspace. Choose a category on the left.')
            intro.setWordWrap(True); layout.addWidget(intro)
            for title, description, callback in [
                ('Customize assistant', 'Name, addressing and voice', lambda: self.select('identity')),
                ('Test your audio', 'Choose the right microphone and speakers', lambda: self.select('audio')),
                ('Browse plugins', 'Your installed extra features', lambda: self.select('plugins')),
                ('Create desktop shortcut', 'Launch Nexa with a desktop shortcut', win._create_desktop_shortcut),
            ]:
                button = QPushButton(title+'\n'+description); button.setMinimumHeight(64); button.clicked.connect(callback); layout.addWidget(button)
            layout.addWidget(win._autostart_btn); win._autostart_btn.show()
        layout.addStretch()
        return panel

    def _busy(self):
        return any(getattr(form, 'busy', False) for form in self.forms.values())

    def closeEvent(self, event):
        if self._busy():
            self.footer.setText('A connection or task is running. You can close settings when it finishes.')
            event.ignore(); return
        for name in ('_drawer_btn', '_ctrl_btn'):
            getattr(self.win, name).setChecked(False)
        event.accept()

    def reject(self):
        self.close()


def open_settings(win, page='general'):
    """UI-only entry point; does not rebuild or reconnect the conversation engine."""
    win._close_setup()
    win._close_controls()
    dialog = getattr(win, '_native_settings_dialog', None)
    if dialog is None:
        dialog = NativeSettings(win)
        win._native_settings_dialog = dialog
    dialog.select(page)
    dialog.show(); dialog.raise_(); dialog.activateWindow()
    if page == 'voice':
        win._ctrl_btn.setChecked(True)
    else:
        win._drawer_btn.setChecked(True)
    return dialog
