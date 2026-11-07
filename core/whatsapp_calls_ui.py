"""Small, native setup panel; opening it never calls anybody."""
import json
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QComboBox,QCheckBox,QPlainTextEdit,QSpinBox,QLineEdit,QTableWidget,QTableWidgetItem,QAbstractItemView
from core import whatsapp_calls as calls
from core import whatsapp_auto_reply as auto
from PyQt6.QtCore import QTimer


class WhatsAppCallsPanel(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self)
        intro=QLabel('WhatsApp Desktop calls\n\nVoice calls and manual answer / decline / hang up are available through chat. Automatic incoming voice-call replies can be enabled below using your exact saved message. WhatsApp must be running. Video calls are excluded.\n\nTo play a message into a call, install a virtual audio cable separately. In WhatsApp Audio settings choose its recording endpoint (normally CABLE Output) as microphone. Choose the matching playback endpoint below (normally CABLE Input). This is software routing, not a physical cable. Normal Nexa microphone/speaker settings are unchanged.')
        intro.setWordWrap(True);layout.addWidget(intro)
        self.visual=QCheckBox('Use verified WhatsApp-window vision when accessibility controls are unavailable')
        self.visual.setToolTip('Sends only the foreground WhatsApp window image to your configured Gemini vision provider when a fresh incoming-call hint or explicit call action requires verification. No saved screenshots.')
        self.visual.setChecked(calls.settings().get('visual_fallback',True))
        layout.addWidget(self.visual)
        self.outputs=QComboBox();layout.addWidget(self.outputs)
        self.routed=QCheckBox('I selected the matching virtual cable microphone in WhatsApp Audio settings')
        layout.addWidget(self.routed)
        self.auto_enabled=QCheckBox('Default reply for callers without a matching personal rule')
        self.auto_enabled.setChecked(bool(calls.settings().get('auto_answer_enabled')))
        layout.addWidget(self.auto_enabled)
        self._auto_dirty=False
        self._loaded_message=calls.settings().get('auto_answer_message','')
        self.auto_message=QPlainTextEdit();self.auto_message.setPlaceholderText('Exact words to speak to callers')
        self.auto_message.setPlainText(calls.settings().get('auto_answer_message',''))
        self.auto_message.setMaximumHeight(100);layout.addWidget(self.auto_message)
        layout.addWidget(QLabel('Auto-reply duration in minutes (0 = until turned off)'))
        self.duration=QSpinBox();self.duration.setRange(0,10080)
        deadline=calls.settings().get('auto_answer_expires_at')
        if deadline:
            import time,math
            self.duration.setValue(max(0,math.ceil((deadline-time.time())/60)))
        layout.addWidget(self.duration)
        self.personal_intro=QCheckBox('Introduce Nexa AI using my profile name before the saved message')
        self.personal_intro.setChecked(calls.settings().get('personal_intro_enabled',False));layout.addWidget(self.personal_intro)
        self.caller_notes=QCheckBox('Take a short caller reply, save a note, then request hangup')
        self.caller_notes.setChecked(calls.settings().get('caller_notes_enabled',False));layout.addWidget(self.caller_notes)
        self.caller_input=QComboBox();layout.addWidget(self.caller_input)
        from core import whatsapp_caller_notes as notes
        cfg=calls.settings()
        for device in notes.return_inputs():
            self.caller_input.addItem(f"{device['name']} [device {device['id']}]",device)
            if device['name']==cfg.get('caller_input_name') and device['id']==cfg.get('caller_input_id'):
                self.caller_input.setCurrentIndex(self.caller_input.count()-1)
        self.caller_routed=QCheckBox('WhatsApp speaker is set to the separate return cable Input (e.g. Hi-Fi Cable Input)')
        self.caller_routed.setChecked(cfg.get('caller_return_routed',False));layout.addWidget(self.caller_routed)
        layout.addWidget(QLabel('Only the dedicated return cable is recorded. Wait up to 15 seconds for speech; then stop after 2 seconds of silence, up to 60 seconds. No detected speech leaves the call open for manual takeover.'))
        self.auto_message.textChanged.connect(self.mark_auto_dirty)
        self.auto_enabled.toggled.connect(self.mark_auto_dirty)
        self.duration.valueChanged.connect(self.mark_auto_dirty)
        layout.addWidget(QLabel('Per-caller replies — exact WhatsApp names or phone numbers; independent timers'))
        self.rule_table=QTableWidget(0,3);self.rule_table.setHorizontalHeaderLabels(['Caller','Exact message','Expiry / state'])
        self.rule_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rule_table.setMaximumHeight(160);layout.addWidget(self.rule_table)
        self.rule_name=QLineEdit();self.rule_name.setPlaceholderText('Exact WhatsApp caller name');layout.addWidget(self.rule_name)
        self.rule_aliases=QLineEdit();self.rule_aliases.setPlaceholderText('Optional exact aliases / full phone numbers, separated by commas');layout.addWidget(self.rule_aliases)
        self.rule_message=QPlainTextEdit();self.rule_message.setPlaceholderText('Exact message for this caller');self.rule_message.setMaximumHeight(75);layout.addWidget(self.rule_message)
        self.rule_duration=QSpinBox();self.rule_duration.setRange(0,10080);self.rule_duration.setPrefix('Caller rule minutes (0 = no expiry): ');layout.addWidget(self.rule_duration)
        add_rule=QPushButton('Save / enable this caller reply');add_rule.clicked.connect(lambda:self.save_rule(True));layout.addWidget(add_rule)
        disable_rule=QPushButton('Disable this caller reply');disable_rule.clicked.connect(lambda:self.save_rule(False));layout.addWidget(disable_rule)
        self.rule_table.cellClicked.connect(self.select_rule)
        self._rules_snapshot=None
        self.watch_status=QLabel();self.watch_status.setWordWrap(True);layout.addWidget(self.watch_status)
        self.watch_timer=QTimer(self);self.watch_timer.timeout.connect(self.refresh_watch_status);self.watch_timer.start(1500)
        self.refresh_watch_status()
        self.result=QLabel();self.result.setWordWrap(True);layout.addWidget(self.result)
        refresh=QPushButton('Refresh audio devices');refresh.clicked.connect(self.refresh);layout.addWidget(refresh)
        save=QPushButton('Save call audio routing');save.clicked.connect(self.save);layout.addWidget(save)
        self.refresh()

    def refresh(self):
        self.outputs.clear();cfg=calls.settings()
        try:
            for d in calls.audio_outputs():
                self.outputs.addItem(f"{d['name']} [device {d['id']}]",d)
                if d['name']==cfg.get('output_name') and d['id']==cfg.get('output_id'):
                    self.outputs.setCurrentIndex(self.outputs.count()-1)
            self.routed.setChecked(bool(cfg.get('microphone_routed')))
            self.result.setText('Virtual audio output detected. Calls have not been tested.' if self.outputs.count() else 'No supported virtual audio cable output detected. Ordinary call controls remain available. Speaking into calls needs this audio device; no driver is installed automatically.')
        except Exception as exc:
            self.result.setText('Audio devices could not be read: '+str(exc))

    def save(self):
        d=self.outputs.currentData()
        changes=dict(visual_fallback=self.visual.isChecked(),microphone_routed=self.routed.isChecked(),personal_intro_enabled=self.personal_intro.isChecked(),caller_notes_enabled=self.caller_notes.isChecked(),caller_return_routed=self.caller_routed.isChecked())
        caller_device=self.caller_input.currentData()
        if caller_device:changes.update(caller_input_name=caller_device['name'],caller_input_id=caller_device['id'])
        if d:changes.update(output_name=d['name'],output_id=d['id'])
        try:
            with calls._settings_lock:
                calls.update_settings(changes,expected_message=self._loaded_message if self._auto_dirty else None)
                if self._auto_dirty:
                    auto.configure(self.auto_enabled.isChecked(),self.auto_message.toPlainText(),self.duration.value() or None,disable_contacts=False)
            self._auto_dirty=False
            self.result.setText('Saved. Chat and settings share the same stored message. Live call delivery is unverified.')
        except Exception as exc:
            self.result.setText('Not saved: '+str(exc)+' Close and reopen this page to reload the current message.')
        self.refresh_watch_status()

    def refresh_watch_status(self):
        state=auto.status()
        cfg=calls.settings()
        if not self._auto_dirty:
            for widget in (self.auto_message,self.auto_enabled,self.duration):widget.blockSignals(True)
            self._loaded_message=cfg.get('auto_answer_message','')
            self.auto_message.setPlainText(self._loaded_message)
            self.auto_enabled.setChecked(bool(cfg.get('auto_answer_enabled')))
            import time,math
            deadline=cfg.get('auto_answer_expires_at')
            self.duration.setValue(max(0,math.ceil((deadline-time.time())/60)) if deadline else 0)
            for widget in (self.auto_message,self.auto_enabled,self.duration):widget.blockSignals(False)
        rules=cfg.get('caller_rules',[])
        snapshot=json.dumps(rules,sort_keys=True)
        if snapshot!=self._rules_snapshot:
            self._rules_snapshot=snapshot;self.rule_table.setRowCount(len(rules))
            from datetime import datetime
            for row,rule in enumerate(rules):
                deadline=rule.get('expires_at')
                expiry=datetime.fromtimestamp(deadline).strftime('%Y-%m-%d %H:%M') if deadline else 'Until disabled'
                if not rule.get('enabled',True):expiry='Disabled'
                elif deadline and deadline<=__import__('time').time():expiry='Expired: '+expiry
                for column,text in enumerate((rule['contact_name'],rule['message'],expiry)):
                    self.rule_table.setItem(row,column,QTableWidgetItem(text))
        self.watch_status.setText('Auto reply: '+('enabled' if state['enabled'] else 'disabled')+' | '+state['phase']+(' | default expires '+state['expires_at'] if state['expires_at'] else '')+(' | '+state['error'] if state['error'] else ''))

    def mark_auto_dirty(self,*args):
        self._auto_dirty=True

    def select_rule(self,row,column):
        rule=calls.settings().get('caller_rules',[])[row]
        self.rule_name.setText(rule['contact_name']);self.rule_aliases.setText(', '.join(rule.get('aliases',[])))
        self.rule_message.setPlainText(rule['message'])
        import time,math
        expiry=rule.get('expires_at')
        self.rule_duration.setValue(max(1,math.ceil((expiry-time.time())/60)) if expiry else 0)

    def save_rule(self,enabled):
        try:
            from core.whatsapp_contact_rules import configure
            configure(self.rule_name.text(),self.rule_message.toPlainText(),self.rule_duration.value() or None,
                      [x.strip() for x in self.rule_aliases.text().split(',') if x.strip()],enabled)
            self.result.setText('Caller rule saved. Only a verified exact caller match uses this message.')
            self.refresh_watch_status()
        except Exception as exc:self.result.setText('Caller rule not saved: '+str(exc))
