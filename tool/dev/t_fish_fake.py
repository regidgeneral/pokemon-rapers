"""Thử săn câu cá trên bộ nhớ giả Emerald: giả lập task câu cá, ghi lại phím tool bấm.  py -3 dev\\t_fish_fake.py"""
import os, struct, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
from tkinter import messagebox
for k in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
    setattr(messagebox, k, lambda *a, _k=k, **kw: print('[hộp thoại %s]' % _k, a[:2]) or False)
import mm_gui
from mm_core import *

app = mm_gui.App(fake=True)
app.withdraw()
g, p, b = app.game, app.prof, app.bridge
if not getattr(p, 'fishing', None):                 # Emerald 10/11: chưa dò task câu cá, săn đang tắt
    print('BỎ QUA: hồ sơ %s chưa có câu cá' % p.title)
    sys.exit(0)
F = p.fishing
ok = fail = 0


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(('  ĐÚNG ' if cond else '  SAI  ') + name)


# chọn map có câu cá + ô bờ cạnh nước
spot = None
for gn in app.story.maps():
    w = app.rom.wild_for_map(*gn) or {}
    if 'fish' in w and gn[0] == 0:
        t = app.story.landing_tile(*gn, 'fish')
        if t:
            enc = app.story.encounter_tiles(*gn)
            for face, d in app.HUNT_STEP.items():
                if enc.get((t[0] + d[0], t[1] + d[1])) == 'water':
                    spot = (gn, t, face)
                    break
    if spot:
        break
gn, pos, face = spot
print('map', gn, app.rom.map_name(*gn), 'ô', pos, 'hướng', face)
sb1 = g.sb1()
b.write(sb1 + p.loc_off, bytes(gn))
b.write(p.player_obj + 0x10, struct.pack('<hh', pos[0] + 7, pos[1] + 7))
b.write(p.player_obj + 0x18, bytes([face]))
key16 = g.key32() & 0xFFFF
b.write(0x02027000 + 0x400 * p.key_pocket, struct.pack('<HH', 262, 1 ^ key16))
g.set_registered_item(99)                                   # món bạn đang đăng ký (giả)

pressed, step = [], {'v': None}


def set_task(v):
    step['v'] = v
    if v is None:
        b.write(F['tasks'], bytes(40))
    else:
        b.write(F['tasks'], struct.pack('<IBBBBh', F['task_fn'], 1, 0, 0, 0, v))


def fake_press(seq):
    keys = [k for k, _ in seq if k]
    pressed.append((step['v'], keys))
    if 'SELECT' in keys and g.registered_item() == 262:
        set_task(0)


g.press = fake_press
g.keys_left = lambda: 0
app.hunt_toggle()
check('bắt đầu ở chế độ câu', app.hunt and app.hunt['kind'] == 'fish' and app.hunt['rod'] == 262)
check('đã đăng ký Old Rod vào SELECT', g.registered_item() == 262)
app.hunt_step()
check('quăng cần bằng SELECT', pressed and pressed[-1][1] == ['SELECT'])
for s in (0, 2, 3, 4, 4, 5, 6, 7, 8):
    set_task(s)
    n = len(pressed)
    app.hunt_step()
    check('bước %d (dấu chấm / cá cắn = Lua bấm): Python không bấm' % s, len(pressed) == n)
set_task(9)
app.hunt_step()
check('bước 9 (on the hook): bấm A', pressed[-1] == (9, ['A']))
set_task(10)
app.hunt_step()
check('bước 10 ("on the hook!" chờ A, đo trong game 11/11): bấm A', pressed[-1] == (10, ['A']))
set_task(None)
app.hunt_step()
check('xong lượt: quăng lại', pressed[-1][1] == ['SELECT'])
set_task(11)
app.hunt_step()
check('bước 11 (không cắn): bấm A cho qua', pressed[-1] == (11, ['A']))
set_task(None)
b.write(p.player_obj + 0x18, bytes([1 if face != 1 else 2]))
app.hunt_step()
check('bị quay mặt: quay lại phía nước', pressed[-1][1] == [{v: k for k, v in app.HUNT_FACE.items()}[face]])
b.write(p.player_obj + 0x18, bytes([face]))
app.hunt_toggle()                                          # dừng
check('dừng săn trả lại món đăng ký cũ', g.registered_item() == 99 and app.hunt is None)
# không có cần câu
b.write(0x02027000 + 0x400 * p.key_pocket, bytes(4))
app.hunt_toggle()
check('không có cần thì từ chối', app.hunt is None)
print('%d đúng, %d sai' % (ok, fail))
app.destroy()
