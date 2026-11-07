"""Explicit local-model check using synthetic text and blocked network sockets."""
from pathlib import Path
import sys
import json
import socket
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy  # native DLL initialization before optional inference libraries
from core.life_connectors import translate
with patch.object(socket, 'create_connection', side_effect=AssertionError('network forbidden')):
    a = translate('Good morning. Please send the report tomorrow.', 'en', 'bn')
    b = translate('আমি আগামীকাল স্কুলে যাব।', 'bn', 'en')
assert any('\u0980' <= c <= '\u09ff' for c in a['text']), a
assert 'school' in b['text'].lower(), b
(ROOT/'runtime').mkdir(exist_ok=True)
(ROOT/'runtime/offline_translation_check.json').write_text(json.dumps([a,b], ensure_ascii=False, indent=2), encoding='utf-8')
print('PASS: Bengali/English local models translated synthetic text with network connections blocked.')
