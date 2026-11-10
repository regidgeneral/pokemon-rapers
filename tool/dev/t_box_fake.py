"""Thử gửi/lấy/thả/sắp xếp kho + đổi chỗ đội trên bộ nhớ giả FireRed (không cần mGBA).  py -3 dev\\t_box_fake.py"""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
import mm_gui
from mm_core import *

app = mm_gui.App(fake=True)
app.withdraw()
g, r = app.game, app.rom
ok = fail = 0


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    if not cond:
        print('SAI:', name)


def team():
    return [r.species_name(m.species) for m in g.party() if not m.empty]


def box1():
    return [r.species_name(cell_species(c)) if cell_species(c) else '-' for c in g.read_one_box(0)][:10]


print('đội:', team(), '| box 1:', box1())
check('đội đầu', team() == ['CHARIZARD', 'PIKACHU', 'LAPRAS'])
check('kho đầu', box1()[:7] == ['BULBASAUR', 'CHARMANDER', 'SQUIRTLE', 'PIDGEY', 'RATTATA', 'PIKACHU', 'PIKACHU'])
box, cell = g.deposit(1)
check('gửi Pikachu vào ô 8', (box, cell) == (0, 7) and team() == ['CHARIZARD', 'LAPRAS'] and box1()[7] == 'PIKACHU')
m = g.withdraw(0, 0)
check('lấy Bulbasaur', m.species == 1 and team() == ['CHARIZARD', 'LAPRAS', 'BULBASAUR'] and box1()[0] == '-')
p = [x for x in g.party() if not x.empty]
check('con lấy về checksum đúng + đủ HP', p[2].checksum_ok and p[2].hp == p[2].maxhp > 0)
g.move_party(2, 0)
check('kéo Bulbasaur lên đầu', team() == ['BULBASAUR', 'CHARIZARD', 'LAPRAS'])
check('đội sau khi kéo vẫn đúng checksum', all(x.checksum_ok for x in g.party() if not x.empty))
n = g.sort_boxes('dex')
check('sắp xếp kho', n == 7 and box1()[:7] == ['CHARMANDER', 'SQUIRTLE', 'PIDGEY', 'RATTATA', 'PIKACHU', 'PIKACHU', 'PIKACHU'])
g.release(0, 6)
check('thả 1 Pikachu', box1()[:7] == ['CHARMANDER', 'SQUIRTLE', 'PIDGEY', 'RATTATA', 'PIKACHU', 'PIKACHU', '-'])
m = app.game.party()[1]
m.set_level(r, 60)
m.iv = [31] * 6
m.set_shiny(True)
g.b.write(g.p.party_base + MON_SIZE, m.to_bytes())
x = g.party()[1]
check('sửa Charizard Lv60 shiny IV 31', x.level == 60 and x.is_shiny_pid() and x.iv == [31] * 6 and x.checksum_ok)
print('đội:', team(), '| box 1:', box1())
print('%d đúng, %d sai' % (ok, fail))
app.destroy()
