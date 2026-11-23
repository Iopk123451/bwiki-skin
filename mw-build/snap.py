
import sqlite3, shutil, os, ctypes
from ctypes import wintypes
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
def copy_locked(src, dst):
    h = k32.CreateFileW(src, 0x80000000, 1|2|4, None, 3, 0, None)
    if h == ctypes.c_void_p(-1).value: raise OSError('open fail ' + src)
    size = wintypes.LARGE_INTEGER(); k32.GetFileSizeEx(h, ctypes.byref(size))
    total = size.value; got = 0; out = bytearray()
    while got < total:
        n = wintypes.DWORD(); buf = ctypes.create_string_buffer(min(1<<20, total-got))
        if not k32.ReadFile(h, buf, min(1<<20, total-got), ctypes.byref(n), None): raise OSError('read fail')
        if n.value == 0: break
        out += buf.raw[:n.value]; got += n.value
    k32.CloseHandle(h)
    with open(dst, 'wb') as f: f.write(out)
src = r'C:\Users\Administrator\AppData\Local\Microsoft\Edge\User Data'
dst = r'C:\Users\Administrator\WorkBuddy\2026-10-24-10-36-24\mw-build\edge-copy2'
copy_locked(os.path.join(src, 'Local State'), os.path.join(dst, 'Local State'))
try:
    copy_locked(os.path.join(src, 'Default', 'Preferences'), os.path.join(dst, 'Default', 'Preferences'))
except Exception as e:
    pass
sdb = sqlite3.connect('file:' + os.path.join(src, 'Default', 'Network', 'Cookies').replace(chr(92), '/') + '?mode=ro&immutable=1', uri=True)
ddb = sqlite3.connect(os.path.join(dst, 'Default', 'Network', 'Cookies'))
sdb.backup(ddb)
ddb.close(); sdb.close()
print('snapshot ok, rows:', sqlite3.connect(os.path.join(dst, 'Default', 'Network', 'Cookies')).execute('SELECT COUNT(*) FROM cookies').fetchone()[0])
