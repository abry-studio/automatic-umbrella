import win32gui
import win32process
import psutil

excel_pids = [p.pid for p in psutil.process_iter(['name']) if p.info['name'] and 'excel' in p.info['name'].lower()]
print("Excel PIDs:", excel_pids)

def enum_windows_proc(hwnd, results):
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    if pid in excel_pids:
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        visible = win32gui.IsWindowVisible(hwnd)
        results.append((hwnd, pid, visible, cls, title))

results = []
win32gui.EnumWindows(enum_windows_proc, results)
for hwnd, pid, visible, cls, title in results:
    print(f"HWND {hwnd} | PID {pid} | Visible: {visible} | Class: {cls} | Title: '{title}'")
