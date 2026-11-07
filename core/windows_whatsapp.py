"""Launch the installed Windows WhatsApp, never a Start/Bing search result."""
import json
import os
from pathlib import Path
import re
import subprocess
import time
from core import appidentity


def matches():
    # Browser titles can say WhatsApp while displaying Bing or WhatsApp Web.
    # They are not evidence that the installed desktop application was opened.
    return [m for m in appidentity.running('WhatsApp', include_self=True)
            if Path(m.name).stem.casefold() in ('whatsapp', 'whatsapproot', 'whatsapp.root', 'whatsappdesktop')]


def foreground_pid():
    import ctypes
    from ctypes import wintypes
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(user.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


def owned_pids():
    """Include embedded WebView/call processes, only below verified app roots."""
    import psutil
    roots = matches()
    ids = {m.pid for m in roots}
    for item in roots:
        try:
            ids.update(p.pid for p in psutil.Process(item.pid).children(recursive=True))
        except psutil.Error:
            pass
    return ids


def focus_existing():
    owned = owned_pids()
    for item in matches():
        if foreground_pid() in owned:
            return True
        if appidentity.focus(item) and foreground_pid() in owned:
            return True
    return False


def installed_id():
    # Constant PowerShell code: user text is never interpolated into a command.
    script = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); Get-StartApps | Where-Object {$_.Name -eq 'WhatsApp'} | Select-Object -ExpandProperty AppID | ConvertTo-Json -Compress"
    p = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
        capture_output=True, timeout=12, creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode or not p.stdout.strip():
        return ''
    values = json.loads(p.stdout.decode('utf-8-sig'))
    values = values if isinstance(values, list) else [values]
    ids = [v for v in values if isinstance(v,str) and re.fullmatch(r'[\w.\-]+_[\w]+![\w.\-]+',v)
           and 'whatsapp' in v.casefold()]
    return ids[0] if len(ids)==1 else ''


def request_launch():
    app_id = installed_id()
    if app_id:
        subprocess.Popen([str(Path(os.environ.get('WINDIR','C:/Windows'))/'explorer.exe'),
                          'shell:AppsFolder\\'+app_id],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    # Older non-Store WhatsApp installations register this app-specific protocol.
    # Missing handlers fail; never fall through to Windows Search or a browser.
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'whatsapp'):
            pass
        os.startfile('whatsapp:')
        return True
    except OSError:
        return False


def open_desktop(timeout=12):
    if focus_existing():
        return {'opened':True,'focused':True,'already_running':True,'verified':True}
    if not request_launch():
        return {'opened':False,'reason':'Installed WhatsApp could not be resolved. No web search was performed.'}
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        # Store activation often reuses an existing process, so requiring a NEW
        # PID incorrectly reports failure for an app already running in the tray.
        if focus_existing():
            return {'opened':True,'focused':True,'verified':True}
        time.sleep(0.35)
    return {'opened':False,'requested':True,'reason':'Desktop launch requested, but WhatsApp foreground window could not be verified. No web search was performed.'}


def visible_windows():
    """Native window handles below verified WhatsApp processes; no UI actions."""
    import ctypes
    from ctypes import wintypes
    pids=owned_pids();result=[]
    user=ctypes.WinDLL('user32',use_last_error=True)
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    user.IsWindowVisible.argtypes=[wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    def visit(hwnd,unused):
        pid=wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value in pids and user.IsWindowVisible(hwnd):
            title=ctypes.create_unicode_buffer(512)
            user.GetWindowTextW(hwnd,title,len(title))
            result.append({'hwnd':int(hwnd),'pid':pid.value,'title':title.value})
        return True
    callback=callback_type(visit)
    user.EnumWindows(callback,0)
    return result
