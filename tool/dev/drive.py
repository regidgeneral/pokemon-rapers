"""Cầm lái mGBA + tool: chụp cửa sổ, bấm phím.
py -3 drive.py shot game|tool out.png [scale]
py -3 drive.py keys "RIGHT:300 A:80 ..."    (tên phím: UP DOWN LEFT RIGHT A B START SELECT L R, :ms = giữ bao lâu)
py -3 drive.py click tool x y   (toạ độ trong vùng client của cửa sổ tool)
"""
import sys, time, ctypes
from ctypes import wintypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
u32 = ctypes.windll.user32

def find(title_part):
    res = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, l):
        if u32.IsWindowVisible(h):
            n = u32.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u32.GetWindowTextW(h, b, n + 1)
            if title_part in b.value:
                res.append((h, b.value))
        return True
    u32.EnumWindows(cb, 0)
    return res

def exe_of(h):
    pid = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    k = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)
    b = ctypes.create_unicode_buffer(260); n = wintypes.DWORD(260)
    ctypes.windll.kernel32.QueryFullProcessImageNameW(k, 0, b, ctypes.byref(n)); ctypes.windll.kernel32.CloseHandle(k)
    return b.value.lower()

def win(which):
    if which == 'game':
        c = [w for w in find('') if exe_of(w[0]).endswith('mgba.exe') and 'Scripting' not in w[1] and w[1]]
        c.sort(key=lambda w: 'AowVN' not in w[1] and 'Fire' not in w[1])
    else:
        c = [w for w in find('Pokémon Tool') if 'python' in exe_of(w[0])]
        def area(w):
            r = wintypes.RECT(); u32.GetWindowRect(w[0], ctypes.byref(r)); return (r.right - r.left) * (r.bottom - r.top)
        c.sort(key=area, reverse=True)
    return c[0][0]

def front(h):
    if u32.IsIconic(h):
        u32.ShowWindow(h, 9)
    if u32.GetForegroundWindow() == h:
        return
    # KHÔNG bấm Alt: Alt trong mGBA mở thanh menu, phím sau đó đi vào menu thay vì game
    fg = u32.GetForegroundWindow()
    a = u32.GetWindowThreadProcessId(fg, None); b = ctypes.windll.kernel32.GetCurrentThreadId()
    u32.AttachThreadInput(b, a, True)
    u32.BringWindowToTop(h); u32.SetForegroundWindow(h)
    u32.AttachThreadInput(b, a, False)
    time.sleep(0.25)
    if u32.GetForegroundWindow() != h:
        print('!! không đưa được cửa sổ lên trước', file=sys.stderr)

def client_rect(h):
    r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r))
    p = wintypes.POINT(0, 0); u32.ClientToScreen(h, ctypes.byref(p))
    return p.x, p.y, p.x + r.right, p.y + r.bottom

SC = {'UP': (0x48, True), 'DOWN': (0x50, True), 'LEFT': (0x4B, True), 'RIGHT': (0x4D, True),
      'A': (0x2C, False), 'B': (0x2D, False), 'START': (0x1C, False), 'SELECT': (0x39, False),
      'L': (0x1E, False), 'R': (0x1F, False)}   # theo config.ini của Duy: A=Z, B=X, Enter, Space, A, S

def key(name, ms):
    sc, ext = SC[name]
    f = 0x0008 | (0x0001 if ext else 0)
    u32.keybd_event(0, sc, f, 0); time.sleep(ms / 1000); u32.keybd_event(0, sc, f | 0x0002, 0); time.sleep(0.06)

cmd = sys.argv[1]
if cmd == 'shot':
    from PIL import ImageGrab
    h = win(sys.argv[2]); front(h)
    im = ImageGrab.grab(client_rect(h), all_screens=True)
    if len(sys.argv) > 4:
        s = float(sys.argv[4]); im = im.resize((int(im.width * s), int(im.height * s)))
    im.save(sys.argv[3]); print(im.size)
elif cmd == 'keys':
    front(win('game'))
    for t in sys.argv[2].split():
        n, _, ms = t.partition(':')
        if n == 'WAIT':
            time.sleep(int(ms) / 1000); continue
        key(n, int(ms or 80))
    print('ok')
elif cmd == 'click':
    h = win(sys.argv[2]); front(h)
    x0, y0, _, _ = client_rect(h)
    u32.SetCursorPos(x0 + int(sys.argv[3]), y0 + int(sys.argv[4])); time.sleep(0.1)
    u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.05); u32.mouse_event(4, 0, 0, 0, 0)
    print('ok')
elif cmd == 'list':
    for h, t in find(''):
        if t: print(h, t)
if cmd == 'aclick':
    u32.SetCursorPos(int(sys.argv[2]), int(sys.argv[3])); time.sleep(0.1)
    u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.05); u32.mouse_event(4, 0, 0, 0, 0)
    print('ok')
if cmd == 'full':
    from PIL import ImageGrab
    im = ImageGrab.grab(all_screens=True)
    if len(sys.argv) > 3:
        x0, y0, x1, y1 = map(int, sys.argv[3].split(','))
        im = im.crop((x0, y0, x1, y1))
    im.save(sys.argv[2]); print(im.size)
if cmd == 'wheel':          # wheel tool x y notch [ctrl|shift]
    h = win(sys.argv[2]); front(h)
    x0, y0, _, _ = client_rect(h)
    u32.SetCursorPos(x0 + int(sys.argv[3]), y0 + int(sys.argv[4])); time.sleep(0.1)
    mod = {'ctrl': 0x11, 'shift': 0x10}.get(sys.argv[6] if len(sys.argv) > 6 else '')
    if mod: u32.keybd_event(mod, 0, 0, 0)
    for _ in range(abs(int(sys.argv[5]))):
        u32.mouse_event(0x0800, 0, 0, 120 if int(sys.argv[5]) > 0 else -120, 0); time.sleep(0.3)
    if mod: u32.keybd_event(mod, 0, 2, 0)
    print('ok')
if cmd == 'dclick':
    h = win(sys.argv[2]); front(h)
    x0, y0, _, _ = client_rect(h)
    u32.SetCursorPos(x0 + int(sys.argv[3]), y0 + int(sys.argv[4])); time.sleep(0.1)
    for _ in range(2):
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.03); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(0.08)
    print('ok')
def in_battle(im):
    w, hh = im.size
    box = im.crop((int(w * .58), int(hh * .78), int(w * .95), int(hh * .97))).convert('L')
    d = box.getdata()
    return sum(1 for v in d if v > 230) > 0.55 * len(d)
if cmd == 'isbattle':
    from PIL import ImageGrab
    h = win('game'); front(h); print(in_battle(ImageGrab.grab(client_rect(h), all_screens=True)))
if cmd == 'walkbattle':     # đi qua lại tới khi vào trận (ô menu trắng góc dưới phải), tối đa N lượt
    from PIL import ImageGrab
    h = win('game'); front(h)
    for i in range(int(sys.argv[2])):
        key('LEFT', 45); key('RIGHT', 45)
        time.sleep(0.15)
        im = ImageGrab.grab(client_rect(h), all_screens=True)
        w, hh = im.size
        if in_battle(im):
            time.sleep(1.5); print('battle after', i + 1); break
    else:
        print('no battle')
if cmd == 'hunt':           # hunt N: gặp -> lưu ảnh tên đối thủ -> chạy; dừng khi file stop tồn tại
    from PIL import ImageGrab
    import os
    h = win('game'); front(h)
    for b in range(int(sys.argv[2])):
        for i in range(60):
            key('LEFT', 45); key('RIGHT', 45); time.sleep(0.12)
            im = ImageGrab.grab(client_rect(h), all_screens=True)
            if in_battle(im):
                break
        else:
            print('no battle'); break
        time.sleep(0.8)
        im = ImageGrab.grab(client_rect(h), all_screens=True)
        w, hh = im.size
        im.crop((0, int(hh * .05), int(w * .6), int(hh * .3))).save(sys.argv[3] + '_%d.png' % b)
        key('RIGHT', 30); key('DOWN', 30); key('A', 30); time.sleep(1.5); key('A', 30); time.sleep(1.5)
        for _ in range(10):
            if not in_battle(ImageGrab.grab(client_rect(h), all_screens=True)):
                break
            key('B', 30); key('RIGHT', 30); key('DOWN', 30); key('A', 30); time.sleep(1.5)
        print('battle', b, 'done')
if cmd == 'tkeys':          # phím vào cửa sổ đang trước (tool): tkeys "DOWN*19 ENTER"
    for t in sys.argv[2].split():
        n, _, k = t.partition('*')
        sc = {'ENTER': (0x1C, False), 'ESC': (0x01, False)}.get(n) or SC[n]
        for _ in range(int(k or 1)):
            f = 0x0008 | (0x0001 if sc[1] else 0)
            u32.keybd_event(0, sc[0], f, 0); time.sleep(0.03); u32.keybd_event(0, sc[0], f | 2, 0); time.sleep(0.05)
    print('ok')
if cmd == 'adclick':
    u32.SetCursorPos(int(sys.argv[2]), int(sys.argv[3])); time.sleep(0.15)
    for _ in range(2):
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.03); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(0.08)
    print('ok')
if cmd == 'ctrl':           # ctrl r : phím tắt mGBA
    front(win('game'))
    vk = ord(sys.argv[2].upper())
    u32.keybd_event(0x11, 0, 0, 0); u32.keybd_event(vk, 0, 0, 0); time.sleep(0.05)
    u32.keybd_event(vk, 0, 2, 0); u32.keybd_event(0x11, 0, 2, 0)
    print('ok')
if cmd == 'lua':            # lua "<code>" : gõ vào ô lệnh cửa sổ Scripting rồi bấm Run
    h = [w for w in find('Scripting') if 'mgba' in exe_of(w[0])][0][0]; front(h)
    x0, y0, x1, y1 = client_rect(h)
    u32.SetCursorPos(x0 + 480, y1 - 43); time.sleep(0.1)
    u32.mouse_event(2, 0, 0, 0, 0); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(0.1)
    for ch in sys.argv[2]:
        u32.keybd_event(0, ord(ch), 0x0004, 0); u32.keybd_event(0, ord(ch), 0x0004 | 2, 0)
    time.sleep(0.1)
    u32.keybd_event(0, 0x1C, 0x0008, 0); u32.keybd_event(0, 0x1C, 0x0008 | 2, 0)   # Enter
    time.sleep(0.5)
    from PIL import ImageGrab
    im = ImageGrab.grab((x0 + 210, y0 + 300, x1 - 10, y1 - 60), all_screens=True); im.save(sys.argv[3]); print(im.size)
