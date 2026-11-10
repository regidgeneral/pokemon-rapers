"""Thử tự lưu sau khi bắt (menu Start Emerald) + chấm IV theo dạng tiến hoá cuối + "con quan trọng", bộ nhớ giả.
  py -3 dev\\t_save_fake.py"""
import os, struct, sys, time
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
g, p, b, r = app.game, app.prof, app.bridge, app.rom
sm = p.start_menu
ok = fail = 0


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(('  ĐÚNG ' if cond else '  SAI  ') + name)


pressed = []
g.press = lambda seq: pressed.append([k for k, _ in seq if k])
g.keys_left = lambda: 0
alerts = []
app.alert = lambda *a, **kw: alerts.append(a[:2])


def save_menu(cur, acts):
    pressed.clear()
    b.write(sm['cursor'], bytes([cur, len(acts)]) + bytes(acts).ljust(9, b'\0'))
    b.write(p.fly['lock'], b'\1')                        # menu Start đang mở
    app.hunt = dict(save=dict(stage=1, t=time.time(), mtime=app._sav_mtime(), name='MAGIKARP'), kind='land')
    app.hunt_save_step()
    return pressed[-1] if pressed else []


NO_NAV = [0, 1, 2, 4, 5, 6, 7]                           # đo trong RAM thật 11/11 (chưa có PokéNav)
NAV = [0, 1, 2, 3, 4, 5, 6, 7]
check('7 mục, con trỏ ở Túi (2) -> xuống 2 lần rồi A', save_menu(2, NO_NAV) == ['DOWN', 'DOWN', 'A'])
check('7 mục, con trỏ ở Thoát (6) -> lên 2 lần rồi A', save_menu(6, NO_NAV) == ['UP', 'UP', 'A'])
check('7 mục, con trỏ đã ở Lưu (4) -> A', save_menu(4, NO_NAV) == ['A'])
check('có PokéNav (8 mục), con trỏ 0 -> xuống 5 lần', save_menu(0, NAV) == ['DOWN'] * 5 + ['A'])
check('sang bước chờ lưu', app.hunt and app.hunt['save']['stage'] == 2)
alerts.clear()
last = save_menu(0, [0, 1, 2])                           # menu lạ: không có LƯU
check('menu không có mục Lưu: không bấm A, dừng săn + báo lưu tay',
      'A' not in last and app.hunt is None and any('lưu' in str(x).lower() for x in alerts))

# chấm IV theo dạng tiến hoá cuối
check('Magikarp chấm theo Gyarados', r.grade_base(129) == r.base_stats(130))
check('Treecko chấm theo Sceptile', r.grade_base(277) == r.base_stats(279))
check('loài không tiến hoá giữ nguyên', r.grade_base(130) == r.base_stats(130))
iv = [28, 14, 28, 28, 25, 31]                            # Magikarp tool bắt lúc 11:08 (Atk 14)
gr = mm_gui.iv_grade(iv, r.grade_base(129))
check('Magikarp Atk 14: tấn công chính Atk, không còn >= 90%% (%s)' % (gr,), gr[2] == 'Atk' and gr[1] / 155 < 0.9)

# "con quan trọng"
m = FrMon(bytes(100))
m.species, m.iv = 129, [10] * 6
m.is_shiny_in_game = lambda: False
app.hunt_target = 129
app.hunt_target_shiny.set(True)
check('săn Magikarp SHINY: Magikarp thường không quan trọng', not app.hunt_important(m))
app.hunt_target_shiny.set(False)
check('săn Magikarp (không đòi shiny): Magikarp là quan trọng', app.hunt_important(m))
m.is_shiny_in_game = lambda: True
app.hunt_target_shiny.set(True)
check('Magikarp shiny luôn quan trọng', app.hunt_important(m))

print('\n%d đúng, %d sai' % (ok, fail))
app.destroy()
sys.exit(1 if fail else 0)
