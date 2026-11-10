"""Đọc trạng thái FireRed đang chạy qua bridge (dùng chung với tool đang mở, tự thử lại).  py -3 dev\\peek_fr.py"""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')
from mm_core import *

rom = Rom(EMERALD)
g = Game(Bridge(timeout=2), rom)
p = EMERALD


def retry(f):
    for _ in range(8):
        try:
            return f()
        except BridgeError as e:
            err = e
            time.sleep(0.2)
    return 'LỖI bridge: %s' % err


sb1, sb2 = retry(g.sb1), retry(g.sb2)
print('SB1 %08X  SB2 %08X' % (sb1, sb2))
gm = retry(g.current_map)
print('map', gm, rom.map_name(*gm), '| ô', retry(g.player_xy))
cb2 = retry(lambda: g.b.read_u32(p.cb2_addr))
print('callback2 %08X (overworld %s, trận %s) | battle_state %s' % (cb2, cb2 == p.cb2_overworld, cb2 == p.cb2_battle,
                                                                   retry(g.battle_state)))
print('tiền', retry(g.money), '| ID', hex(retry(g.player_otid)), '| số con', retry(lambda: g.b.read(p.party_count, 1)[0]))
dex = retry(g.caught_dex)
print('Pokédex đã bắt', sorted(dex) if isinstance(dex, set) else dex)
for i, m in enumerate(retry(g.party)):
    if not m.empty or any(m.enc[:8]):
        print('  đội %d: %s Lv%d HP %d/%d IV %s chiêu %s checksum %s bad_egg %s' % (
            i + 1, rom.species_name(m.species), m.level, m.hp, m.maxhp, m.iv,
            [rom.move_name(x) for x in m.moves if x], m.checksum_ok, m.bad_egg))
for i, m in enumerate(retry(g.enemy_party)):
    if not m.empty:
        print('  đối thủ %d: %s Lv%d HP %d/%d checksum %s' % (i + 1, rom.species_name(m.species), m.level, m.hp, m.maxhp,
                                                             m.checksum_ok))
try:
    for k in range(5):
        it = retry(lambda: g.read_pocket(k))
        if it:
            print('  túi %s: %s' % (p.pocket_names[k], [(rom.item_name(a), q) for a, q in it]))
except Exception as e:
    print('túi lỗi', e)
st = retry(lambda: g.b.read_u32(p.storage_ptr))
print('kho ptr %08X, box 1 có %d con' % (st, sum(1 for c in retry(lambda: g.read_one_box(0)) if any(c))))
