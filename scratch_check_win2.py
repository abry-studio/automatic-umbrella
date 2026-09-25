import ctypes
from ctypes import wintypes
import psutil

user32 = ctypes.windll.user32

excel_pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] and 'excel' in p.info['name'].lower()]
print("Excel PIDs:", excel_pids)

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def enum_proc(hwnd, lparam):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in excel_pids:
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, 512)
        cls = ctypes.create_unicode_buffer(512)
        user32.GetClassNameW(hwnd, cls, 512)
        visible = bool(user32.IsWindowVisible(hwnd))
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if visible or title.value:
            print(f"HWND {hwnd} | Visible: {visible} | Pos: ({rect.left},{rect.top}) Size: {width}x{height} | Class: {cls.value} | Title: '{title.value}'")
    return True

user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
