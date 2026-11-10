"""Bài thử FrMon (mã hoá Pokémon FireRed) không cần mGBA:  py -3 dev\\t_frmon.py"""
import os, random, struct, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mm_core import *

rom = Rom(EMERALD)
rng = random.Random(1)
ok = fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print('SAI:', name)


def make(sp, lv, pid, otid):
    dec = bytearray(MON_SIZE)
    struct.pack_into('<II', dec, 0, pid, otid)
    dec[8:18] = rom.species_name_bytes(sp)
    dec[0x12] = 2                                   # ngôn ngữ
    struct.pack_into('<HHI', dec, 0x20, sp, 0, rom.exp_for(rom.growth(sp), lv))
    struct.pack_into('<4H', dec, 0x2C, 33, 45, 0, 0)
    dec[0x34:0x38] = bytes([35, 40, 0, 0])
    struct.pack_into('<I', dec, 0x48, rng.getrandbits(30))
    dec[0x55] = 0xFF
    m = FrMon(fr_encrypt(dec))                      # checksum đúng sẵn
    m.recalc(rom)
    m.full_restore(rom)
    return m


# 1) giải mã(mã hoá(x)) = x với đủ 24 thứ tự khối
for k in range(240):
    dec = bytearray(rng.getrandbits(8) for _ in range(MON_SIZE))
    struct.pack_into('<I', dec, 0, k * 7919 + rng.getrandbits(16))
    enc = fr_encrypt(bytes(dec))
    back, crc = fr_decrypt(enc)
    check('vòng mã hoá %d' % k, crc and back[0x20:0x50] == bytes(dec[0x20:0x50]) and back[:0x1C] == bytes(dec[:0x1C]))
    check('mã hoá lại trùng byte %d' % k, fr_encrypt(back) == enc)

# 2) FrMon: đọc -> ghi lại không đổi byte; sửa chỉ số -> checksum vẫn đúng
for sp, lv in ((1, 5), (6, 50), (150, 70), (277, 12), (303, 30)):
    m = make(sp, lv, rng.getrandbits(32), rng.getrandbits(32))
    raw = m.to_bytes()
    m2 = FrMon(raw)
    check('loài %d đọc lại' % sp, m2.species == sp and m2.level == lv and m2.checksum_ok)
    check('loài %d ghi lại trùng byte' % sp, m2.to_bytes() == raw)
    check('cờ hasSpecies loài %d' % sp, raw[0x13] & 2)
    m2.iv = [31] * 6
    m2.set_shiny(True)
    m3 = FrMon(m2.to_bytes())
    check('loài %d sau khi sửa: checksum + shiny + IV' % sp, m3.checksum_ok and m3.is_shiny_pid() and m3.iv == [31] * 6
          and m3.pid % 25 == m.pid % 25)
    if sp == 303:
        check('Shedinja HP 1', m3.maxhp == 1)

# 3) kho: đội -> ô 80 byte -> đội
m = make(25, 33, 0x12345678, 0x0BADF00D)
cell = party_to_box(m)
check('ô kho 80 byte', len(cell) == 80 and cell_species(cell) == 25)
b = box_to_party(rom, cell)
check('lấy từ kho: loài/level/HP', b.species == 25 and b.level == 33 and b.hp == b.maxhp > 0 and b.checksum_ok)
check('lấy từ kho: không thư', b.to_bytes()[0x55] == 0xFF)
check('ô trống', cell_species(bytes(80)) == 0 and FrMon(bytes(100)).empty)
bad = bytearray(cell)
bad[0x30] ^= 0xFF
check('ô hỏng -> loài 0', cell_species(bytes(bad)) == 0)

# 4) dữ liệu ROM
check('tên loài', [rom.species_name(i) for i in (1, 25, 151, 277, 411)] == ['BULBASAUR', 'PIKACHU', 'MEW', 'TREECKO', 'CHIMECHO'])
check('chỉ số Bulbasaur', rom.base_stats(1) == [45, 49, 49, 45, 65, 65])
check('dex Treecko 252', rom.natdex(277) == 252)
# Emerald Mỹ/Âu (dò 10/11)
check('ability Bulbasaur', rom.ability_name(rom.species_abilities(1)[0]) == 'OVERGROW')
check('chiêu 33 Tackle', rom.move_name(33) == 'TACKLE' and rom.move_power(33) == 35 and rom.move_pp(33) == 35)
check('vật phẩm', rom.item_name(1) == 'MASTER BALL' and rom.item_pocket(1) == 2 and rom.item_pocket(259) == 5
      and rom.item_name(376) == 'OLD SEA MAP')
check('TM01 Focus Punch, HM01 Cut', struct.unpack_from('<H', rom.d, rom._o(EMERALD.tm_moves))[0] == 264
      and struct.unpack_from('<H', rom.d, rom._o(EMERALD.tm_moves) + 100)[0] == 15)
check('EXP Lv 100 Medium Fast', rom.exp_for(0, 100) == 1000000 and rom.exp_for(5, 100) == 1250000)
check('Bulbasaur tiến hoá Lv16', level_evolution(rom, 1, 16) == 2)
check('Route 101 có Pokémon', rom.wild_for_map(0, 16) is not None)
check('tên map', rom.map_name(0, 9) == 'LITTLEROOT TOWN' and rom.map_name(0, 0) == 'PETALBURG CITY'
      and rom.map_name(0, 16) == 'ROUTE 101')
check('màu Bulbasaur', len(rom.palette(1)) == 16 and rom.palette(1) != rom.palette(1, True))
check('ảnh mặt trước', rom.lz77(struct.unpack_from('<I', rom.d, rom._o(EMERALD.sprite_front) + 8)[0])[:1] is not None)
import mm_story
_st = mm_story.Story(rom)
check('hình nhân vật overworld 0-244', all(_st.ow_sprite(g) is not None for g in range(245))
      and _st.ow_sprite(0).size == (16, 32) and _st.ow_sprite(94).size == (48, 48))
print('Route 101:', rom.map_name(0, 16), [(rom.species_name(s), lo, hi) for lo, hi, s in rom.wild_for_map(0, 16)['land'][1]][:4])
print('%d đúng, %d sai' % (ok, fail))
sys.exit(1 if fail else 0)
