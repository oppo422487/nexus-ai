import os,sys,threading,asyncio,time
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.stdout.reconfigure(encoding='utf-8')
import main as m
from PyQt6.QtCore import QTimer
m.get_brief_enabled=lambda:False
u=m.JarvisUI('face.png');j=m.JarvisLive(u);j._gmail_briefing_sent=True
# Only synthetic probe response is observed, not historical conversations.
original=u.write_log
found=[]
def log(text):
 if text.startswith(u.assistant_name+':'):found.append(text)
 original(text)
u.write_log=log
threading.Thread(target=lambda:asyncio.run(j.run()),daemon=True).start()
sent=False
second=False
start=time.monotonic()
def tick():
 global sent,second
 if j.session and not sent:
  sent=True;j._on_text_command('এটি সংযোগ পরীক্ষা। শুধু হ্যালো বলো। কোনো টুল চালাবে না।');print('PROBE_SENT',flush=True)
 if found and not second:
  second=True;found.clear();j._on_text_command('এবার শুধু ঠিক আছে বলো। কোনো টুল নয়।');print('SECOND_PROBE_SENT',flush=True)
 elif found and second:print('TWO_NATIVE_REPLIES_RECEIVED',flush=True);u._app.quit()
 elif time.monotonic()-start>45:print('PROBE_TIMEOUT',flush=True);u._app.quit()
t=QTimer();t.timeout.connect(tick);t.start(1000);u._app.exec()
os._exit(0)
