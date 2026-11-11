"""Thử chia EXP cho con không ra trận + kho PC, tự tiến hoá (Duy 11/11), bộ nhớ giả.  py -3 dev\\t_exp_fake.py"""
import os, random, struct, sys, tempfile
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
from tkinter import messagebox
for k in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
    setattr(messagebox, k, lambda *a, _k=k, **kw: print('[hộp thoại %s]' % _k, a[:2]) or False)
import mm_gui
from mm_core import *

mm_gui.HERE = tempfile.mkdtemp()                      # battle_log.jsonl của bài thử không lẫn vào log thật
app = mm_gui.App(fake=True)
app.withdraw()
g, p, b, r = app.game, app.prof, app.bridge, app.rom
app.alert = lambda *a, **kw: None
rng = random.Random(7)
ok = fail = 0
SP = {n: next(i for i in range(1, r.max_species + 1) if r.species_name(i) == n)
      for n in ('TREECKO', 'GROVYLE', 'SCEPTILE', 'MAGIKARP', 'WURMPLE', 'SILCOON', 'CASCOON', 'ZIGZAGOON')}
OTID = g.player_otid()


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(('  ĐÚNG ' if cond else '  SAI  ') + name)


def make(sp, exp, pid=None, otid=OTID, item=0):
    dec = bytearray(MON_SIZE)
    struct.pack_into('<II', dec, 0, pid if pid is not None else rng.getrandbits(32), otid)
    dec[8:18] = r.species_name_bytes(sp)
    dec[0x12] = 2
    struct.pack_into('<HHI', dec, 0x20, sp, item, exp)
    struct.pack_into('<4H', dec, 0x2C, 33, 0, 0, 0)
    dec[0x34] = 35
    struct.pack_into('<I', dec, 0x48, rng.getrandbits(30))
    dec[0x55] = 0xFF
    m = FrMon(fr_encrypt(dec))
    m.recalc(r)
    m.full_restore(r)
    return FrMon(m.to_bytes())


exp_lv = lambda sp, lv: r.exp_for(r.growth(sp), lv)

# 1) công thức (battle_script_commands.c:3310-3392)
karp10 = [(SP['MAGIKARP'], 10)]                       # EXP gốc 20: 20*10//7 = 28, Exp. Share = 14
m = make(SP['ZIGZAGOON'], exp_lv(SP['ZIGZAGOON'], 5))
check('EXP gốc Magikarp = 20', r.exp_yield(SP['MAGIKARP']) == 20)
check('hoang dã: 20*10//7//2 = 14', share_exp_gain(r, karp10, m, OTID, False, 197) == 14)
check('trận trainer: 14*1.5 = 21', share_exp_gain(r, karp10, m, OTID, True, 197) == 21)
m2 = make(SP['ZIGZAGOON'], 100, otid=0x12345678, item=197)
check('Lucky Egg + trainer + đổi tay: 14 -> 21 -> 31 -> 46', share_exp_gain(r, karp10, m2, OTID, True, 197) == 46)
check('2 đối thủ cộng dồn', share_exp_gain(r, karp10 * 2, m, OTID, False, 197) == 28)

# 2) tiến hoá (pokemon.c:5513-5579)
t = make(SP['TREECKO'], exp_lv(SP['TREECKO'], 16) - 5)
lv0, lv1, ev = share_exp_apply(r, t, 10, 195)
check('Treecko lên Lv16 -> Grovyle, biệt danh đổi theo', (lv0, lv1) == (15, 16) and ev == [(SP['TREECKO'], SP['GROVYLE'])]
      and t.species == SP['GROVYLE'] and FrMon(t.to_bytes()).nickname == 'GROVYLE')
t = make(SP['TREECKO'], exp_lv(SP['TREECKO'], 15))
share_exp_apply(r, t, exp_lv(SP['TREECKO'], 40) - t.exp, 195)
check('vượt nhiều mốc: Treecko -> Grovyle -> Sceptile', t.species == SP['SCEPTILE'] and t.level == 40)
t = make(SP['TREECKO'], exp_lv(SP['TREECKO'], 16) - 5, item=195)
share_exp_apply(r, t, 10, 195)
check('cầm Everstone: lên level nhưng không tiến hoá', t.level == 16 and t.species == SP['TREECKO'])
for hi, want in ((3, 'SILCOON'), (7, 'CASCOON')):
    w = make(SP['WURMPLE'], exp_lv(SP['WURMPLE'], 7) - 1, pid=(hi << 16) | 0x1234)
    share_exp_apply(r, w, 5, 195)
    check('Wurmple PID cao %% 10 = %d -> %s' % (hi, want), w.species == SP[want])
t = make(SP['TREECKO'], exp_lv(SP['TREECKO'], 100) - 3)
share_exp_apply(r, t, 10 ** 6, 195)
check('không vượt EXP Lv100', t.exp == exp_lv(SP['SCEPTILE'], 100) or t.exp == exp_lv(SP['TREECKO'], 100))
t = make(SP['TREECKO'], exp_lv(SP['TREECKO'], 20))
share_exp_apply(r, t, 1, 195)
check('không lên level thì không tiến hoá (như game)', t.species == SP['TREECKO'])

# 3) cả luồng trận (bộ nhớ giả)
fighter = make(SP['ZIGZAGOON'], exp_lv(SP['ZIGZAGOON'], 12))
bench = make(SP['TREECKO'], exp_lv(SP['TREECKO'], 16) - 5)          # ngồi ngoài, sắp lên 16
egg = make(SP['MAGIKARP'], 100)
b.write(p.party_base, fighter.to_bytes() + bench.to_bytes() + bytes(MON_SIZE * 4))
b.write(p.party_count, b'\2')
addrs, box = g.read_box()
old0 = bytes(box)
box[:] = bytes(len(box))
boxmon = make(SP['TREECKO'], exp_lv(SP['TREECKO'], 16) - 3)
box[0:80] = party_to_box(boxmon)
box[80:160] = party_to_box(make(SP['ZIGZAGOON'], exp_lv(SP['ZIGZAGOON'], 50)))
g.write_box(addrs, old0, box)
foe = make(SP['MAGIKARP'], exp_lv(SP['MAGIKARP'], 10), otid=0xBEEF)
b.write(p.enemy_base, foe.to_bytes() + bytes(MON_SIZE * 5))
b.write(p.battle_type, b'\0')
b.write(p.battle_flag[0], bytes([p.battle_flag[1]]))
b.write(p.cb2_addr, struct.pack('<I', p.cb2_battle))
app.box_exp.set(True)
app.was_battle, app.exp_snap = False, None
app.tick_battle()
check('vào trận: chụp đội + đối thủ', app.exp_snap and len(app.exp_snap[0]) == 2 and app.exp_snap[2] is False)
f2 = FrMon(fighter.to_bytes())                                      # con ra trận: game đã cộng EXP
f2.exp += 28
f2.recalc(r)
b.write(p.party_base, f2.to_bytes())
f3 = FrMon(foe.to_bytes())
f3.hp = 0
b.write(p.enemy_base, f3.to_bytes())                                # đối thủ bị hạ
b.write(p.battle_flag[0], b'\0')
app.tick_battle()
check('hết trận nhưng chưa về bản đồ: chưa ghi', app.exp_snap is not None)
b.write(p.cb2_addr, struct.pack('<I', p.cb2_overworld))
app.tick_battle()
pa = g.party()
check('con ra trận: không cộng thêm', pa[0].exp == f2.exp)
check('con ngồi ngoài: +14 EXP, Treecko -> Grovyle Lv16', pa[1].exp == bench.exp + 14 and pa[1].species == SP['GROVYLE']
      and pa[1].level == 16 and pa[1].checksum_ok)
cells = g.read_one_box(0)
k1, k2 = box_to_party(r, cells[0]), box_to_party(r, cells[1])
check('kho: Treecko +14 -> Grovyle', k1.exp == boxmon.exp + 14 and k1.species == SP['GROVYLE'] and k1.checksum_ok)
check('kho: con khác cũng +14', k2.exp == exp_lv(SP['ZIGZAGOON'], 50) + 14)
check('thanh trạng thái báo chia EXP + tiến hoá', any('chia EXP' in x for x in app.exp_msg + [app.status.cget('text')]))
log = open(os.path.join(mm_gui.HERE, 'battle_log.jsonl'), encoding='utf-8').read()
check('ghi battle_log', 'GROVYLE' in log and '"beaten"' in log)

# bắt được thì không có EXP; tắt công tắc thì không chụp
before = g.party()[1].exp
b.write(p.battle_flag[0], bytes([p.battle_flag[1]]))
b.write(p.cb2_addr, struct.pack('<I', p.cb2_battle))
b.write(p.enemy_base, foe.to_bytes())
app.was_battle = False
app.tick_battle()
b.write(p.party_base + 2 * MON_SIZE, foe.to_bytes())                 # con đối thủ đã vào đội = bắt được
b.write(p.battle_flag[0], b'\0')
b.write(p.cb2_addr, struct.pack('<I', p.cb2_overworld))
app.tick_battle()
check('bắt được: không chia EXP', g.party()[1].exp == before)
app.box_exp.set(False)
b.write(p.battle_flag[0], bytes([p.battle_flag[1]]))
app.was_battle, app.exp_snap = False, None
app.tick_battle()
check('tắt công tắc: không chụp trận', app.exp_snap is None)

print('\n%d đúng, %d sai' % (ok, fail))
app.destroy()
sys.exit(1 if fail else 0)
