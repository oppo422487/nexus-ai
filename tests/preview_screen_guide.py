"""Native Screen Guide visual fixture; no user screen capture or network."""
from pathlib import Path
import os,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from core.screen_guide import validate
from core.screen_guide_ui import ScreenGuidePanel
from core.qt_settings import STYLE
from core.nexa_fonts import ensure_ui_fonts
from PyQt6.QtWidgets import QApplication,QDialog,QVBoxLayout,QMainWindow

app=QApplication([]);ensure_ui_fonts()
host=QMainWindow();dialog=QDialog(host);dialog.setObjectName('NexaSettings');dialog.setStyleSheet(STYLE);dialog.resize(950,900)
layout=QVBoxLayout(dialog);panel=ScreenGuidePanel(host,dialog);layout.addWidget(panel);dialog.show()
try:
    image=Image.new('RGB',(900,500),'#ededf5');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
    draw.text((40,40),'Project settings',font=font,fill='#202030')
    draw.text((40,120),'Name: Example project',font=font,fill='#202030')
    draw.rounded_rectangle((650,40,850,100),radius=10,fill='#5b3890')
    draw.text((700,55),'Export',font=font,fill='white')
    panel.got_image(image)
    panel.question.setText('Where is the Export button?')
    panel.got_result(validate({'summary':'Export is visible near the top right.',
       'steps':[{'label':'Export','location':'Top right','guidance':'Review your file, then use Export when ready.','box':[722,80,945,200]}],'uncertainties':[]}))
    for _ in range(6):app.processEvents()
    root=Path(__file__).resolve().parents[1]/'runtime'
    dialog.grab().save(str(root/'screen_guide_preview.png'))
finally:dialog.close();host.close()
print('Synthetic Screen Guide preview saved.')
