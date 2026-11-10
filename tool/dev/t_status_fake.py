"""Thử xoá trạng thái xấu trong trận (Game.cure_battle_status + tick_battle), bộ nhớ giả.  py -3 dev\\t_status_fake.py"""
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
ok = fail = 0


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(('  ĐÚNG ' if cond else '  SAI  ') + name)


def battle(status, ctl=p.ctl_action, double=False, status2=0):
    b.write(p.battle_flag[0], bytes([p.battle_flag[1]]))
    b.write(p.cb2_addr, struct.pack('<I', p.cb2_battle))
    b.write(p.battle_ctl, struct.pack('<I', ctl))
    b.write(p.battle_type, bytes([1 if double else 0]))
    for k, st in ((0, status), (2, status2)):
        a = p.battle_mons + 0x58 * k
        b.write(a, struct.pack('<H', 277))                   # TREECKO
        b.write(a + 0x4C, struct.pack('<I', st))


st1 = lambda k=0: struct.unpack('<I', b.read(p.battle_mons + 0x58 * k + 0x4C, 4))[0]
battle(0x2)                                              # đo thật 11/11: Treecko ngủ, status1 = 2
check('ngủ ở menu chọn lệnh -> xoá', g.cure_battle_status() == [('TREECKO', 'ngủ')] and st1() == 0)
battle(0x40, ctl=0x080597B5)                             # đang chờ chữ / hoạt cảnh
check('không ở menu chọn lệnh -> không ghi', g.cure_battle_status() == [] and st1() == 0x40)
battle(0x88)
check('độc nặng (bit độc + bộ đếm) -> xoá hết', g.cure_battle_status() and st1() == 0)
battle(0x10, double=True, status2=0x20)
check('trận đôi: xoá cả 2 con mình', len(g.cure_battle_status()) == 2 and st1() == 0 and st1(2) == 0)
battle(0x20, status2=0x40)
g.cure_battle_status()
check('trận đơn: không đụng ô 2', st1(2) == 0x40)
# qua vòng làm mới của giao diện: bật/tắt Tự hồi
app.was_battle = True
battle(0x40)
app.auto_heal.set(False)
app.tick_battle()
check('tắt Tự hồi: giữ nguyên trạng thái', st1() == 0x40)
app.auto_heal.set(True)
app.tick_battle()
check('bật Tự hồi: tick_battle xoá + báo', st1() == 0 and 'tê liệt' in app.status.cget('text'))

# câu hỏi đặt biệt danh sau khi bắt (Duy 11/11): tự bấm B = NO
nk = p.nickname
SCRIPT_F3 = 0x082DBDAF                                   # chỗ duy nhất có lệnh 0xF3 trong vùng battle script
pressed = []
g.press = lambda seq: pressed.append([k for k, _ in seq if k])
g.keys_left = lambda: 0


def nick(ptr, state, on=True):
    pressed.clear()
    battle(0)
    b.write(nk['curr_instr'], struct.pack('<I', ptr))
    b.write(nk['comm'], bytes([state]))
    app.skip_nick.set(on)
    app.tick_battle()
    return pressed


check('ROM: lệnh ở 0x082DBDAF là 0xF3', app.rom.d[SCRIPT_F3 - ROM_BASE] == 0xF3)
check('đang chờ YES/NO đặt tên -> bấm B', nick(SCRIPT_F3, 1) == [['B']])
check('tắt công tắc -> không bấm', nick(SCRIPT_F3, 1, on=False) == [])
check('lệnh 0xF3 nhưng chưa tới bước chờ (0) -> không bấm', nick(SCRIPT_F3, 0) == [])
check('đã vào màn đặt tên / xong (2, 4) -> không bấm', nick(SCRIPT_F3, 2) == [] and nick(SCRIPT_F3, 4) == [])
check('lệnh khác (chờ = 1) -> không bấm', nick(SCRIPT_F3 + 5, 1) == [] or app.rom.d[SCRIPT_F3 + 5 - ROM_BASE] == 0xF3)
check('con trỏ rác (RAM) -> không bấm', nick(0x02000000, 1) == [])

print('\n%d đúng, %d sai' % (ok, fail))
app.destroy()
sys.exit(1 if fail else 0)
