import time
import subprocess
import os
import sys
import ctypes
import threading
from ctypes import wintypes
import win32api
import atexit

## this program blocks Windows, Tab, Shift, Control, and Alt


keyboard_hook_handle = None
hook_thread_obj = None
hook_proc_ptr = None

WH_KEYBOARD_LL = 13
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_TAB = 0x09
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5
HC_ACTION = 0

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


LPKBDLLHOOKSTRUCT = ctypes.POINTER(KBDLLHOOKSTRUCT)
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32 = ctypes.windll.user32
user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = ctypes.c_int
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]


def LowLevelKeyboardProc(nCode, wParam, lParam):
    global keyboard_hook_handle
    if nCode == HC_ACTION:
        p_kb_struct = ctypes.cast(lParam, LPKBDLLHOOKSTRUCT)
        blocked_keys = [
            VK_LWIN, VK_RWIN, VK_TAB, VK_SHIFT, VK_CONTROL, VK_MENU,
            VK_LSHIFT, VK_RSHIFT, VK_LCONTROL, VK_RCONTROL, VK_LMENU, VK_RMENU
        ]
        if p_kb_struct.contents.vkCode in blocked_keys:
            return 1
    return user32.CallNextHookEx(keyboard_hook_handle, nCode, wParam, lParam)


def hook_thread_func():
    global keyboard_hook_handle, hook_proc_ptr

    hook_proc_ptr = HOOKPROC(LowLevelKeyboardProc)

    h_instance = win32api.GetModuleHandle(None)
    if not h_instance:
        print("cant hook module")
        return

    keyboard_hook_handle = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_proc_ptr, h_instance, 0)

    if not keyboard_hook_handle:
        error_code = ctypes.windll.kernel32.GetLastError()
        print(f"cant hook keyboard error code: {error_code}")
        return

    print("keyboard hook installed")

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def setup_keyboard_hook():
    global hook_thread_obj
    if hook_thread_obj and hook_thread_obj.is_alive():
        print("keyboard hook already installed")
        return

    print("installing hook")
    hook_thread_obj = threading.Thread(target=hook_thread_func)
    hook_thread_obj.daemon = True
    hook_thread_obj.start()


def uninstall_keyboard_hook():
    global keyboard_hook_handle
    if keyboard_hook_handle:
        print("uninstalling hook")
        if user32.UnhookWindowsHookEx(keyboard_hook_handle):
            print("keyboard hook uninstalled")
        else:
            error_code = ctypes.windll.kernel32.GetLastError()
            print(f"error uninstalling hook error code: {error_code}")
        keyboard_hook_handle = None

def main():
    try:
        is_admin = (os.getuid() == 0)
    except AttributeError:
        is_admin = (ctypes.windll.shell32.IsUserAnAdmin() != 0)

    if not is_admin:
        print("admin permissions required")
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)
        except Exception as e:
            print(f" error elevating permissions: {e}")
            print(" please run as admin")
            sys.exit(1)

    print("program started with admin permissions")
    
    setup_keyboard_hook()
    atexit.register(uninstall_keyboard_hook)
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    main()