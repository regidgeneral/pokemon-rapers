"""Thử nút 🔓 Mở khoá săn shiny (gói A) trên bộ nhớ giả Emerald.  py -3 dev\\t_unlock_fake.py"""
import os, struct, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
from tkinter import messagebox
messagebox.askyesno = lambda *a, **kw: True                  # bấm "Có"
for k in ('showinfo', 'showwarning', 'showerror'):
    setattr(messagebox, k, lambda *a, _k=k, **kw: print('[hộp thoại %s]' % _k, a[:2]))
import mm_gui
from mm_core import *

app = mm_gui.App(fake=True)
app.withdraw()
g, p, b = app.game, app.prof, app.bridge
app.SAV_FILE = os.path.join(HERE, 'dev', '_khong_co.sav')     # không sao lưu save thật trong bài thử
ok = fail = 0
N = 0x12C


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(('  ĐÚNG ' if cond else '  SAI  ') + name)


sb1, sb2 = g.sb1(), g.sb2()
fa = sb1 + p.flags_off
var = lambda v: struct.unpack('<H', b.read(sb1 + p.vars_off + 2 * (v - 0x4000), 2))[0]
# trạng thái đầu giống save thật 11/11: cờ trainer 0x500, vật phẩm ẩn 0x1F4, vài cờ ẩn NPC, Pokédex 0x861,
# Littleroot/Oldale/Petalburg đã thăm; biến cốt truyện Littleroot = 3; đang ở overworld
b.write(fa, bytes(N))
START = (0x500, 0x1F4, 0x02C, 0x2F0, 0x860, 0x861, 0x86F, 0x870, 0x876)
for f in START:
    b.write(fa + (f >> 3), bytes([b.read(fa + (f >> 3), 1)[0] | 1 << (f & 7)]))
b.write(sb1 + p.vars_off + 2 * (0x4050 - 0x4000), struct.pack('<H', 3))
b.write(sb2 + 0x18, bytes(3))
b.write(p.cb2_addr, struct.pack('<I', p.cb2_overworld))
b.write(p.battle_flag[0], bytes([0]))
key16 = g.key32() & 0xFFFF
b.write(0x02032000 + 0x400 * p.key_pocket, struct.pack('<HH', 262, 1 ^ key16))     # đã có Old Rod
before_all = b.read(fa, N)

app.quest_unlock_all()
flag = lambda f: b.read(fa + (f >> 3), 1)[0] >> (f & 7) & 1
check('8 huy hiệu', all(flag(f) for f in range(0x867, 0x86F)))
check('Bay: 16 thị trấn', all(flag(f) for f in range(0x86F, 0x87F)))
check('giày chạy + cờ National Dex', flag(0x8C0) and flag(0x896))
check('KHÔNG bật phá đảo (0x864)', not flag(0x864))
check('giữ cờ cũ (trainer, vật phẩm ẩn, ẩn NPC, Pokédex)', all(flag(f) for f in START))
after = b.read(fa, N)
extra = [i * 8 + k for i in range(N) for k in range(8)
         if (after[i] >> k & 1) and not (before_all[i] >> k & 1) and i * 8 + k not in UNLOCK_FLAGS_SET]
check('không bật cờ nào ngoài gói (thừa: %s)' % [hex(f) for f in extra], not extra)
check('biến National Dex 0x302', var(0x4046) == 0x302)
check('Pokédex: order 0, mode National, magic 0xDA', b.read(sb2 + 0x18, 3) == bytes([0, 1, 0xDA]))
check('biến cốt truyện giữ nguyên (Littleroot = 3)', var(0x4050) == 3)
have = {i for k in range(p.n_pockets) for i, q in g.read_pocket(k)}
check('đủ vật phẩm (thiếu: %s)' % sorted(set(UNLOCK_ITEMS) - have), set(UNLOCK_ITEMS) <= have)
check('Old Rod không bị thêm lần 2', sum(1 for i, q in g.read_pocket(p.key_pocket) if i == 262) == 1)
check('HM vào ngăn TM/HM', {339, 346} <= {i for i, q in g.read_pocket(app.rom.item_pocket(339) - 1)})
check('xe đạp/kính/Devon Scope vào ngăn chính', {259, 272, 279, 288} <= {i for i, q in g.read_pocket(p.key_pocket)})

# bấm lần 2: không thêm trùng, cờ giữ nguyên
before = b.read(fa, N)
app.quest_unlock_all()
check('bấm lại: cờ không đổi', b.read(fa, N) == before)
kp = [i for i, q in g.read_pocket(p.key_pocket)]
check('bấm lại: không thêm trùng', len(kp) == len(set(kp)))

# đang trong trận -> từ chối, không ghi
b.write(fa, bytes(N))
b.write(p.cb2_addr, struct.pack('<I', p.cb2_battle))
b.write(p.battle_flag[0], bytes([p.battle_flag[1]]))
try:
    g.unlock_all()
    check('trong trận phải từ chối', False)
except ValueError:
    check('trong trận phải từ chối', b.read(fa, N) == bytes(N))

print('\n%d đúng, %d sai' % (ok, fail))
app.destroy()
sys.exit(1 if fail else 0)
