"""Pokémon ROM-hack Tool - lõi: hồ sơ game (AowVN/FireRed), bảng dữ liệu ROM, giải mã/sửa Pokémon,
túi đồ, tiền, cầu nối tới mGBA. Địa chỉ/công thức suy ra từ chính ROM (xem ghi chú từng hồ sơ)."""
import math, os, struct, time

M32 = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IPC_DIR = os.path.join(HERE, 'ipc')
SPRITE_ROOT = os.path.join(HERE, 'sprites')
ROM_BASE = 0x08000000
MON_SIZE, PARTY_SLOTS = 100, 6

TYPE_NAMES = ['Normal', 'Giác đấu', 'Bay', 'Độc', 'Đất', 'Đá', 'Bọ', 'Ma', 'Thép', '???', 'Lửa', 'Nước',   # theo mã hệ
              'Cỏ', 'Điện', 'Siêu linh', 'Băng', 'Rồng', 'Bóng tối', '???', '???', '???', '???', '???', 'Tiên']  # CFRU: Tiên = 23
NATURES = ['Hardy', 'Lonely', 'Brave', 'Adamant', 'Naughty', 'Bold', 'Docile', 'Relaxed', 'Impish', 'Lax', 'Timid',
           'Hasty', 'Serious', 'Jolly', 'Naive', 'Modest', 'Mild', 'Quiet', 'Bashful', 'Rash', 'Calm', 'Gentle',
           'Sassy', 'Careful', 'Quirky']
LAND_W = [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]
WATER_W = ROCK_W = [60, 30, 5, 4, 1]
FISH_W = {'old': [70, 30], 'good': [60, 20, 20], 'super': [40, 40, 15, 4, 1]}

CHARMAP = {0x00: ' ', 0xAB: '!', 0xAC: '?', 0xAD: '.', 0xAE: '-', 0xB4: "'", 0xBA: '/', 0x1B: 'é', 0xF0: ':',
           0x53: 'PK', 0x54: 'MN', 0xB5: '♂', 0xB6: '♀', 0xB8: ','}   # PK MN = chữ POKé MON trong tên lớp trainer
CHARMAP.update({0xA1 + i: str(i) for i in range(10)})
CHARMAP.update({0xBB + i: chr(65 + i) for i in range(26)})
CHARMAP.update({0xD5 + i: chr(97 + i) for i in range(26)})


def decode_text(b):
    out = ''
    for x in b:
        if x == 0xFF:
            break
        out += CHARMAP.get(x, '?')
    return out


class Profile:
    """Một bộ địa chỉ/bố cục của một game. Các cặp (base0, stride): base0 là địa chỉ của mục có chỉ số 0."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ---------------------------------------------------------------- Pokémon
def catch_chance(rate, hp, maxhp, status=0, ball10=10):
    """Xác suất bắt (0..1) theo công thức FireRed; ball10 = hệ số bóng x10 (Poké Ball 10, Great 15, Ultra 20)."""
    if maxhp <= 0:
        return 0.0
    odds = (rate * ball10 // 10) * (maxhp * 3 - hp * 2) // (maxhp * 3)
    if status & 0x7 or status & 0x20:                  # ngủ / đóng băng
        odds *= 2
    elif status & (0x8 | 0x10 | 0x40 | 0x80):          # độc / bỏng / tê liệt / độc nặng
        odds = odds * 15 // 10
    if odds > 254:
        return 1.0
    if odds <= 0:
        return 0.0
    shake = 1048560 // math.isqrt(math.isqrt(16711680 // odds))
    return min(1.0, shake / 65536) ** 4                 # phải qua 4 lần lắc: Random() < shake


SHINY_ODDS = 8192                                   # shiny khi shiny_xor < 8  ->  8/65536 = 1/8192
SHINY_STEP = 0.1        # AowVN -star.gba (vá 2026-11-06, ROM 0x0973B6AA): mỗi lần gặp +0,1/8192; trước vá là 1

NATURE_STATS = ['Atk', 'Def', 'Spe', 'SpA', 'SpD']  # tính cách n: tăng n // 5, giảm n % 5; trùng nhau = trung tính


def nature_label(n):
    up, down = n // 5, n % 5
    return '%s (%s)' % (NATURES[n], 'trung tính' if up == down else '+%s -%s' % (NATURE_STATS[up], NATURE_STATS[down]))


def nature_ev_spread(n, base):
    """Kiểu EV 252/252/6 theo tính cách, thứ tự HP Atk Def Spe SpA SpD; base là chỉ số gốc cùng thứ tự.
    Tăng Atk/SpA/Def/SpD: 252 HP + 252 chỉ số đó (như bảng trainer trong ROM). Tăng Spe: 252 Spe + 252 tấn công.
    Trung tính: coi như tăng chỉ số tấn công gốc cao hơn. 6 điểm dư vào Spe, tính cách giảm Spe thì vào chỉ số thủ."""
    HP, ATK, DEF, SPE, SPA, SPD = range(6)
    stat = [ATK, DEF, SPE, SPA, SPD]
    up, down = stat[n // 5], stat[n % 5]
    attacker = ATK if base[ATK] >= base[SPA] else SPA
    if up == down:
        up, down = attacker, None
    ev = [0] * 6
    if up == SPE:
        hit = ATK if down == SPA else SPA if down == ATK else attacker
        ev[SPE], ev[hit], ev[HP] = 252, 252, 6
    else:
        ev[HP], ev[up] = 252, 252
        ev[SPE if down != SPE else (SPD if up == DEF else DEF)] = 6
    return ev


def shiny_xor(pid, otid):
    return (otid >> 16) ^ (otid & 0xFFFF) ^ (pid >> 16) ^ (pid & 0xFFFF)


class BaseMon:
    """Phần dùng chung: shiny, tính lại chỉ số, hồi máu. Lớp con lo phần đọc/ghi byte."""
    STAT_NAMES = ['HP', 'Atk', 'Def', 'Spe', 'SpA', 'SpD']
    USE_NATURE_MODS = True          # FireRed: chỉ số nhân hệ số tính cách

    def nature_key(self):
        raise NotImplementedError

    def is_shiny_pid(self):
        return shiny_xor(self.pid, self.otid) < 8

    def is_shiny_in_game(self):
        return self.is_shiny_pid()

    def _pid_matches(self, p):
        raise NotImplementedError

    def _find_pid(self, want_shiny):
        for k in range(0, 8) if want_shiny else range(8, 200):
            for hi8 in range(256):
                lo = (hi8 << 8) | (self.pid & 0xFF)
                hi = lo ^ (self.otid & 0xFFFF) ^ (self.otid >> 16) ^ k
                p = ((hi << 16) | lo) & M32
                if p != self.pid and self._pid_matches(p, want_shiny):
                    return p
        return None

    def set_shiny(self, shiny=True):
        """Đổi PID giữ nguyên byte thấp (giới tính) và tính cách."""
        self._before_shiny(shiny)
        if shiny and not self.is_shiny_pid():
            p = self._find_pid(True)
        elif not shiny and self.is_shiny_pid():
            p = self._find_pid(False)
        else:
            return
        if p is None:
            raise ValueError('không tìm được PID phù hợp')
        self.pid = p

    def _before_shiny(self, shiny):
        pass

    def recalc(self, rom):
        """Tính lại level (từ EXP) và chỉ số như CalculateMonStats của game."""
        rate = rom.growth(self.species)
        lvl = rom.level_for(rate, self.exp)
        b = rom.base_stats(self.species)
        hp = ((2 * b[0] + self.iv[0] + self.ev[0] // 4) * lvl) // 100 + lvl + 10
        if rom.profile.shedinja and self.species == rom.profile.shedinja:
            hp = 1
        st = [((2 * b[i] + self.iv[i] + self.ev[i] // 4) * lvl) // 100 + 5 for i in range(1, 6)]
        if self.USE_NATURE_MODS:
            n = self.pid % 25
            inc, dec = n // 5, n % 5
            if inc != dec:
                st[inc] = st[inc] * 110 // 100
                st[dec] = st[dec] * 90 // 100
        old_cur, old_max = self.hp, self.maxhp
        if old_cur == 0:
            cur = hp if old_max == 0 else 0
        else:
            cur = old_cur + (hp - old_max)
            if cur <= 0:
                cur = 1
        self.level, self.maxhp = lvl, hp
        self.atk, self.defn, self.spe, self.spa, self.spd = st
        self.hp = cur

    def set_level(self, rom, lvl):
        self.exp = rom.exp_for(rom.growth(self.species), max(1, min(100, lvl)))
        self.recalc(rom)

    def heal(self):
        self.hp = self.maxhp
        self.status = 0

    def max_pp(self, rom, i):
        """PP tối đa của chiêu thứ i (tính cả PP Up trong ppbonus)."""
        mv = self.moves[i]
        return rom.move_pp(mv) * (5 + ((self.ppbonus >> (2 * i)) & 3)) // 5 if mv else 0

    def full_restore(self, rom):
        """Như Trung tâm Pokémon: đầy HP, đầy PP, bỏ mọi trạng thái. Trả True nếu có thay đổi."""
        pp = [self.max_pp(rom, i) for i in range(4)]
        if self.hp == self.maxhp and not self.status and self.pp == pp:
            return False
        self.heal()
        self.pp = pp
        return True


class AowMon(BaseMon):
    """Pokémon của AowVN (FireRed hack): 100 byte không mã hoá, không xáo trộn."""
    MAX_SPECIES = 1263

    def __init__(self, raw):
        assert len(raw) == MON_SIZE
        self.raw = bytearray(raw)
        self.pid, self.otid = struct.unpack_from('<II', raw, 0)
        self.species, self.item, self.exp = struct.unpack_from('<HHI', raw, 0x20)
        self.empty = self.species == 0
        self.nickname = decode_text(raw[8:18])
        self.ppbonus, self.friendship = raw[0x28], raw[0x29]
        self.moves = list(struct.unpack_from('<4H', raw, 0x2C))
        self.pp = list(raw[0x34:0x38])
        self.ev = list(raw[0x38:0x3E])
        self.contest = list(raw[0x3E:0x44])
        self.pokerus, self.metloc = raw[0x44], raw[0x45]
        self.origins = struct.unpack_from('<H', raw, 0x46)[0]
        w = struct.unpack_from('<I', raw, 0x48)[0]
        self.iv = [(w >> (5 * k)) & 31 for k in range(6)]
        self.egg, self.abilbit = (w >> 30) & 1, w >> 31
        self.ribbons = struct.unpack_from('<I', raw, 0x4C)[0]
        self.ability_num = self.abilbit                   # FireRed: bit 31 của từ IV = ability 1 hay 2
        self.status = struct.unpack_from('<I', raw, 0x50)[0]
        self.level = raw[0x54]
        self.hp, self.maxhp, self.atk, self.defn, self.spe, self.spa, self.spd = struct.unpack_from('<7H', raw, 0x56)
        # "checksum_ok" ở đây nghĩa là dữ liệu hợp lý (FireRed hack này không dùng checksum cho từng Pokémon)
        self.checksum_ok = (not self.empty and 1 <= self.level <= 100 and 0 < self.maxhp <= 9999
                            and self.hp <= self.maxhp and self.species <= self.MAX_SPECIES)

    def nature_key(self):
        return self.pid % 25

    def _pid_matches(self, p, want_shiny):
        return p % 25 == self.pid % 25

    def set_nature(self, n):
        """Đổi PID sang tính cách n, giữ byte thấp (giới tính) và trạng thái shiny."""
        if self.pid % 25 == n:
            return
        for k in range(0, 8) if self.is_shiny_pid() else range(8, 200):
            for hi8 in range(256):
                lo = (hi8 << 8) | (self.pid & 0xFF)
                hi = lo ^ (self.otid & 0xFFFF) ^ (self.otid >> 16) ^ k
                p = ((hi << 16) | lo) & M32
                if p % 25 == n:
                    self.pid = p
                    return
        raise ValueError('không tìm được PID phù hợp')

    def to_bytes(self):
        raw = bytearray(self.raw)
        struct.pack_into('<II', raw, 0, self.pid, self.otid)
        struct.pack_into('<HHI', raw, 0x20, self.species, self.item, self.exp)
        raw[0x28], raw[0x29] = self.ppbonus, self.friendship
        struct.pack_into('<4H', raw, 0x2C, *self.moves)
        raw[0x34:0x38] = bytes(self.pp)
        raw[0x38:0x3E] = bytes(self.ev)
        raw[0x3E:0x44] = bytes(self.contest)
        raw[0x44], raw[0x45] = self.pokerus, self.metloc
        struct.pack_into('<H', raw, 0x46, self.origins)
        w = sum((self.iv[k] & 31) << (5 * k) for k in range(6)) | (self.egg << 30) | (self.abilbit << 31)
        struct.pack_into('<I', raw, 0x48, w)
        struct.pack_into('<I', raw, 0x4C, self.ribbons)
        struct.pack_into('<I', raw, 0x50, self.status)
        raw[0x54] = self.level
        struct.pack_into('<7H', raw, 0x56, self.hp, self.maxhp, self.atk, self.defn, self.spe, self.spa, self.spd)
        return bytes(raw)


# ---------------------------------------------------------------- FireRed gốc: Pokémon mã hoá
# 48 byte từ +0x20 là 4 khối 12 byte (G = loài/EXP, A = chiêu, E = EV, M = IV/khác), thứ tự theo PID % 24,
# XOR từng u32 với (PID ^ OTID); u16 +0x1C = tổng u16 của 48 byte đã giải mã. AowMon đọc đúng thứ tự GAEM không mã hoá,
# nên FrMon chỉ giải mã + xếp lại rồi dùng nguyên AowMon.
FR_ORDERS = ['GAEM', 'GAME', 'GEAM', 'GEMA', 'GMAE', 'GMEA', 'AGEM', 'AGME', 'AEGM', 'AEMG', 'AMGE', 'AMEG',
             'EGAM', 'EGMA', 'EAGM', 'EAMG', 'EMGA', 'EMAG', 'MGAE', 'MGEA', 'MAGE', 'MAEG', 'MEGA', 'MEAG']


def _xor48(data, key):
    return struct.pack('<12I', *(x ^ key for x in struct.unpack('<12I', data)))


def fr_decrypt(raw):
    """(100 byte đã giải mã, phần giữa xếp theo GAEM; checksum đúng?)."""
    raw = bytearray(bytes(raw).ljust(MON_SIZE, b'\0'))
    pid, otid = struct.unpack_from('<II', raw, 0)
    plain = _xor48(bytes(raw[0x20:0x50]), pid ^ otid)
    blocks = {c: plain[12 * i:12 * i + 12] for i, c in enumerate(FR_ORDERS[pid % 24])}
    raw[0x20:0x50] = b''.join(blocks[c] for c in 'GAEM')
    ok = sum(struct.unpack('<24H', plain)) & 0xFFFF == struct.unpack_from('<H', raw, 0x1C)[0]
    return bytes(raw), ok


def fr_encrypt(dec):
    """Ngược với fr_decrypt: tính checksum, xếp theo PID % 24, XOR."""
    raw = bytearray(dec)
    pid, otid = struct.unpack_from('<II', raw, 0)
    blocks = {c: bytes(raw[0x20 + 12 * i:0x2C + 12 * i]) for i, c in enumerate('GAEM')}
    plain = b''.join(blocks[c] for c in FR_ORDERS[pid % 24])
    struct.pack_into('<H', raw, 0x1C, sum(struct.unpack('<24H', plain)) & 0xFFFF)
    raw[0x20:0x50] = _xor48(plain, pid ^ otid)
    return bytes(raw)


class FrMon(AowMon):
    """Pokémon FireRed gốc: 100 byte trong đội (80 byte đầu = ô kho), phần giữa mã hoá. self.raw là bản ĐÃ giải mã;
    byte thật trong RAM: self.enc (lúc đọc) / to_bytes() (để ghi)."""
    MAX_SPECIES = 411

    def __init__(self, raw):
        raw = bytes(raw).ljust(MON_SIZE, b'\0')
        self.enc = raw
        dec, ok = fr_decrypt(raw)
        super().__init__(dec)
        self.bad_egg = bool(raw[0x13] & 1)
        self.checksum_ok = self.checksum_ok and ok and not self.bad_egg

    def to_bytes(self):
        dec = bytearray(super().to_bytes())
        dec[0x13] = (dec[0x13] & ~6 & 0xFF) | (2 if self.species else 0) | (4 if self.egg else 0)   # hasSpecies, isEgg
        return fr_encrypt(dec)


def fr_cell_species(cell):
    """Loài của một ô kho 80 byte (0 = trống hoặc checksum sai)."""
    if not any(cell[:0x50]):
        return 0
    dec, ok = fr_decrypt(cell[:80])
    return struct.unpack_from('<H', dec, 0x20)[0] if ok else 0


# ---------------------------------------------------------------- hồ sơ game
# Emerald Mỹ/Âu (BPEE, "Pokemon - Emerald Version (USA, Europe)", SHA1 f3ae088181bf...), dò 10/11:
# - RAM: đếm literal trong ROM (gPlayerParty 0x020244EC 1091 lần, SaveBlock ptr 0x03005D8C 829...) và đối chiếu chỗ FR
#   dùng cùng biến (đoạn code trước literal khớp -> đọc literal Emerald): warp, khoá điều khiển, gMapHeader, gFieldCallback.
# - Bảng ROM dò theo nội dung (BULBASAUR/IVYSAUR, POUND/KARATE CHOP, MASTER BALL/ULTRA BALL, EXP 0/1/8/27, TM01 = 264,
#   LITTLEROOT TOWN, Route 101 = (0,16)...). Ảnh mặt trước = bảng ảnh lưng - 0x14A0, màu = ảnh lưng + 0xDC0.
# - Hàm: callback overworld / quay lại map / FieldCallback_UseFly khớp thân hàm FR (che lệnh BL).
# - Hàm trận đấu, túi, câu cá: đo trong game 11/11 (xem ghi chú ở cb2_battle / fishing). Chưa có: con trỏ menu Start
#   (tự lưu sau khi bắt con quan trọng đang tắt, chỉ báo bạn lưu tay).
EMERALD = Profile(
    key='em', title='Emerald (USA)', code=b'BPEE', mon_cls=FrMon,
    roms=['Pokemon - Emerald Version (USA, Europe).gba'],
    party_base=0x020244EC, enemy_base=0x02024744,
    sb1_ptr=0x03005D8C, sb2_ptr=0x03005D90, loc_off=4,
    money_off=0x490, key_off=0xAC, max_money=999_999,
    pockets_addr=0x02039DD8, pocket_fmt='<IB', n_pockets=5,    # gBagPockets: {ptr u32, capacity u8}
    pocket_names=['Vật phẩm', 'Poké Ball', 'TM/HM', 'Berry', 'Vật phẩm chính'],
    default_pocket=0, key_pocket=4, qty_max={},
    species_names=(0x083185C8, 11), move_names=(0x0831977C, 13), ability_names=(0x0831B6DB, 13),
    move_data=(0x0831C898, 12), move_off=(1, 3, 4),
    item_recs=(0x085839A0, 44), item_name_off=0, item_pocket_off=26, item_pocket_shift=0,
    item_hold_off=18,
    tm_moves=0x08616040, tm_count=50,                          # u16: 50 TM rồi 8 HM
    species_info=(0x083203CC, 28),
    sp_off=dict(types=6, catch=8, gender=16, friend=18, growth=19, abil=(22, 23, 26)),   # +26 = 0: Gen 3 không có ability ẩn
    exp_table=0x0831F72C,
    max_species=411, max_item=376, max_move=355, shedinja=303,
    wild_headers=0x08552D48, map_groups=0x08486578,
    area_ptr_table=(0x085A147C, 0),                            # gRegionMapEntries {x,y,w,h, ptr tên}, chỉ số = mapsec
    sprite_dir='em', sprite_max=411,
    natdex_table=0x0831DC82,                                   # u16 theo (loài - 1); 252-276 (Unown cũ) = 387
    dex_owned_sb2=(0x28, 52),                                  # Pokédex ở SaveBlock2 + 0x18: owned +0x10, seen +0x44
    dex_seen_sb1=(0x988, 0x3B24),                              # 2 bản sao "seen" ở SaveBlock1
    battle_flag=(0x030022C0 + 0x439, 0x2), cb2_addr=0x030022C4, cb2_overworld=0x08085E5D,   # gMain.inBattle, callback2
    battle_type=0x02022FEC, battle_mons=0x02024084, battle_ctl=0x03005D60,
    # Đo trong game 11/11 (dev\watch_fish_em.py, Duy câu tay 2 trận): callback2 trong trận / túi trong trận,
    # gBattlerControllerFuncs[0] lúc chờ chọn lệnh / chọn chiêu. gBagPosition: {cb, u8 location, u8 ngăn, u16,
    # u16 con trỏ[5] +8, u16 cuộn[5] +0x12} (đọc thật: location 1 = trận, ngăn 1 = Poké Ball).
    # ctl_action sửa 11/11: 0x080597B5 là hàm chờ chữ chạy xong (đứng lúc "Wild X appeared!"), menu chọn lệnh thật đứng
    # ở 0x08057589 (đọc gMain, gọi từ 0x0805C040; đọc lúc Duy đứng ở menu: 11 lần liền đều 0x08057589).
    cb2_battle=0x08038421, cb2_bag=0x081AAD5D, ctl_action=0x08057589, ctl_move=0x08058B41, bag_state=0x0203CE58,
    # Câu cá: Task_Fishing 0x0808C8C1 chạy bảng 16 bước 0x0849755C (data[0] = bước). Emerald: 4 = dấu chấm (bấm A = hỏng),
    # 6 "Oh! A bite!" -> 7 chờ A (~0,5 giây, trễ = cá chạy), 8 có thể quay lại 3 thêm vòng chấm, 9-10 "on the hook!" chờ A,
    # 11-15 hỏng / cất cần. Đo thật: 2 -> 4 -> 7 -> 10 -> A -> vào trận.
    fishing=dict(tasks=0x03005E00, task_fn=0x0808C8C1, rods=(262, 263, 264), press_a=(6, 7)),
    ball_pocket=1, master_ball=1, ultra_ball=2,
    registered_off=0x496,                                      # món đăng ký nút SELECT: u16 SaveBlock1 + 0x496
    sprite_front=0x08301418,                                   # {ptr LZ77, u16 size, u16 tag} theo loài
    pal_normal=[(0x08303678, 0, 440)], pal_shiny=[(0x08304438, 0, 440)],
    evo_table=(0x0832531C, 5),                                 # 5 mục x 8 byte {u16 kiểu, param, loài đích, pad}
    party_count=0x020244E9,
    flags_off=0x1270, vars_off=0x139C, trainer_table=0x08310030, trainer_class_names=0x0830FCD4,   # global.h:1020-1021
    player_obj=0x02037350,
    ow_gfx=0x08505620, ow_pals=0x0850BBC8,                     # hình nhân vật: con trỏ GraphicsInfo theo gfx id; {ptr màu, tag}
    fly=dict(warp_dest=0x020322E4, field_cb=0x03005DAC, use_fly=0x080B69FD, cb2_return=0x080860C9, main_state=0x030026F8,
             lock=0x03000F2C, heal_table=0x0859F53C, heal_count=22, map_type=0x02037318 + 0x17),
    # Kho PC: gPokemonStoragePtr -> 4 byte (box đang chọn) + 14 box x 30 ô x 80 byte (mã hoá như đội)
    storage_ptr=0x03005D94, box_slots=14 * 30, box_size=80,
)
PROFILES = {p.key: p for p in (EMERALD,)}


class Rom:
    """Bảng dữ liệu đọc từ file ROM của một hồ sơ game."""
    def __init__(self, profile, path=None):
        self.profile = profile
        if path is None:
            path = next((os.path.join(ROOT, n) for n in profile.roms if os.path.exists(os.path.join(ROOT, n))), None)
            if path is None:
                raise FileNotFoundError('không thấy ROM %s trong %s' % (profile.title, ROOT))
        self.path = path
        self.d = open(path, 'rb').read()
        self.max_species, self.max_item = profile.max_species, profile.max_item
        self.pocket_names = profile.pocket_names
        self._area_list = None

    def _o(self, addr):
        return addr - ROM_BASE

    def _u16(self, o):
        return struct.unpack_from('<H', self.d, o)[0]

    def _u32(self, o):
        return struct.unpack_from('<I', self.d, o)[0]

    # --- tên và dữ liệu chiêu/vật phẩm
    def species_name(self, i):
        b, s = self.profile.species_names
        o = self._o(b) + s * i
        return decode_text(self.d[o:o + s])

    def natdex(self, sp):
        """Số Pokédex quốc gia của loài (các dạng khác nhau dùng chung số); 0 nếu game không có bảng."""
        t = getattr(self.profile, 'natdex_table', None)
        if not t or sp < 1:
            return 0
        n = struct.unpack_from('<H', self.d, self._o(t) + 2 * (sp - 1))[0]
        if n or sp > self.max_species:
            return n
        if not hasattr(self, '_dex_by_name'):                  # bảng của hack ghi 0 cho chim Galar, Gigantamax...:
            self._dex_by_name = {}                             # dùng số của loài cùng tên (như game chính thức)
            for s in range(1, self.max_species + 1):
                k = struct.unpack_from('<H', self.d, self._o(t) + 2 * (s - 1))[0]
                if k:
                    self._dex_by_name.setdefault(self.species_name(s), k)
        return self._dex_by_name.get(self.species_name(sp), 0)

    def species_name_bytes(self, i):
        """Tên loài dạng byte của game, đệm 0xFF đủ 10 byte (để ghi vào ô biệt danh)."""
        b, s = self.profile.species_names
        o = self._o(b) + s * i
        raw = bytes(self.d[o:o + s])
        raw = raw.split(b'\xff', 1)[0][:10]
        return raw + b'\xff' * (10 - len(raw))

    def move_name(self, i):
        b, s = self.profile.move_names
        o = self._o(b) + s * i
        return decode_text(self.d[o:o + s])

    def _move_byte(self, i, k):
        b, s = self.profile.move_data
        return self.d[self._o(b) + s * i + self.profile.move_off[k]]

    def move_power(self, i):
        return self._move_byte(i, 0)

    def move_accuracy(self, i):
        return self._move_byte(i, 1)

    def move_pp(self, i):
        return self._move_byte(i, 2)

    def item_name(self, i):
        p = self.profile
        o = self._o(p.item_recs[0]) + p.item_recs[1] * i + p.item_name_off
        return decode_text(self.d[o:o + 14])

    def item_pocket(self, i):
        """Số ngăn túi (1..n); 0 nếu không có. Chỉ số ngăn trong RAM = số này - 1."""
        p = self.profile
        return self.d[self._o(p.item_recs[0]) + p.item_recs[1] * i + p.item_pocket_off] >> p.item_pocket_shift

    def ability_name(self, i):
        b, s = self.profile.ability_names
        o = self._o(b) + s * i
        return decode_text(self.d[o:o + s])

    # --- bản ghi loài
    def _sp(self, sp, off):
        b, s = self.profile.species_info
        return self.d[self._o(b) + s * sp + off]

    def base_stats(self, sp):
        b, s = self.profile.species_info
        o = self._o(b) + s * sp
        return list(self.d[o:o + 6])

    def species_abilities(self, sp):
        """(ability 1, ability 2, ability ẩn) dạng ID."""
        a = self.profile.sp_off['abil']
        return self._sp(sp, a[0]), self._sp(sp, a[1]), self._sp(sp, a[2])

    def species_types(self, sp):
        t = self.profile.sp_off['types']
        return self._sp(sp, t), self._sp(sp, t + 1)

    def catch_rate(self, sp):
        return self._sp(sp, self.profile.sp_off['catch'])

    def base_friendship(self, sp):
        return self._sp(sp, self.profile.sp_off['friend'])

    def gender_ratio(self, sp):
        return self._sp(sp, self.profile.sp_off['gender'])

    def gender(self, sp, pid):
        r = self.gender_ratio(sp)
        if r == 0xFF:
            return 'Vô tính'
        if r == 0:
            return '♂'
        if r == 0xFE:
            return '♀'
        return '♀' if (pid & 0xFF) < r else '♂'

    def growth(self, sp):
        return self._sp(sp, self.profile.sp_off['growth'])

    def exp_for(self, rate, level):
        return self._u32(self._o(self.profile.exp_table) + 404 * rate + 4 * level)

    def level_for(self, rate, exp):
        for lv in range(100, 0, -1):
            if exp >= self.exp_for(rate, lv):
                return lv
        return 1
    # --- tính cách và ability của một cá thể
    def nature_text(self, m):
        k = m.nature_key()
        return '%s   (nature %d)' % (NATURES[k], k)

    def nature_name(self, m):
        return self.nature_text(m).split('   (')[0]

    def ability_of(self, m):
        """(tên ability hiện có, có phải ẩn không)."""
        a = self.species_abilities(m.species)
        n = m.ability_num
        if n >= 2:
            return self.ability_name(a[2]), True
        if n == 1 and a[1]:
            return self.ability_name(a[1]), False
        return self.ability_name(a[0]), False

    def abilities_text(self, sp):
        a = self.species_abilities(sp)
        return '%s  /  %s  /  ẩn: %s' % tuple(self.ability_name(x) if x else '—' for x in a)

    # --- danh sách để chọn
    def species_list(self):
        return [(i, self.species_name(i)) for i in range(1, self.max_species + 1) if self.species_name(i).strip()]

    def item_list(self):
        return [(i, self.item_name(i)) for i in range(1, self.max_item + 1)
                if self.item_name(i).strip() and self.item_pocket(i)]

    def move_list(self):
        out = []
        for i in range(1, self.profile.max_move):
            n = self.move_name(i)
            if n.strip() and '?' not in n:
                out.append((i, n))
        return out

    # --- ảnh
    def lz77(self, addr):
        o = self._o(addr)
        d = self.d
        assert d[o] == 0x10, 'không phải LZ77'
        size = d[o + 1] | d[o + 2] << 8 | d[o + 3] << 16
        p, out = o + 4, bytearray()
        while len(out) < size:
            flags = d[p]
            p += 1
            for bit in range(8):
                if len(out) >= size:
                    break
                if flags & (0x80 >> bit):
                    b1, b2 = d[p], d[p + 1]
                    p += 2
                    ln, disp = (b1 >> 4) + 3, ((b1 & 15) << 8 | b2) + 1
                    for _ in range(ln):
                        out.append(out[-disp])
                else:
                    out.append(d[p])
                    p += 1
        return bytes(out)

    def palette(self, sp, shiny=False):
        """16 màu RGB của loài (nhiều bảng, xem hồ sơ)."""
        p = self.profile
        tables = p.pal_shiny if shiny else p.pal_normal
        ptr = None
        for base, first, n in tables:
            if first <= sp < first + n:
                ptr = self._u32(self._o(base) + 8 * (sp - first))
                break
        if ptr is None or not 0x08000000 <= ptr < 0x08000000 + len(self.d) or self.d[self._o(ptr)] != 0x10:
            raise ValueError('không có bảng màu cho loài %d' % sp)
        cols = struct.unpack('<16H', self.lz77(ptr)[:32])
        return [((c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31) for c in cols]

    def sprite(self, sp, shiny=False):
        """Ảnh mặt trước 64x64 (PIL RGBA) đọc từ sprites\\<game>\\<loài>.png (tạo bằng gen_sprites.py); None nếu chưa có."""
        key = (sp, shiny)
        cache = self.__dict__.setdefault('_sprites', {})
        if key not in cache:
            path = os.path.join(SPRITE_ROOT, self.profile.sprite_dir, '%d%s.png' % (sp, '_s' if shiny else ''))
            try:
                from PIL import Image
                cache[key] = Image.open(path).convert('RGBA')
            except Exception:
                cache[key] = None
        return cache[key]

    # --- khu vực / Pokémon hoang dã
    def _area_names(self):
        if self._area_list is None:
            b, _ = self.profile.area_seq
            o, out = self._o(b), []
            while len(out) < 200:
                j = self.d.find(b'\xff', o)
                if j == o or j < 0 or j - o > 30:
                    break
                out.append(decode_text(self.d[o:j]))
                o = j + 1
            self._area_list = out
        return self._area_list

    def map_name(self, g, n):
        p = self.profile
        try:
            gp = self._u32(self._o(p.map_groups) + 4 * g)
            hp = self._u32(self._o(gp) + 4 * n)
            ms = self.d[self._o(hp) + 20]
            if hasattr(p, 'area_ptr_table'):
                base, off = p.area_ptr_table
                e = self._o(base) + 8 * (ms + off)
                ptr = self._u32(e + 4)
                return decode_text(self.d[self._o(ptr):self._o(ptr) + 24]) if ptr else 'Khu vực #%d' % ms
            names = self._area_names()
            i = ms - p.area_seq[1]
            return names[i] if 0 <= i < len(names) and names[i].strip() else 'Khu vực #%d' % ms
        except Exception:
            return '(không rõ)'

    def randomize_species(self, sp, tid):
        """Loài thật sẽ gặp khi Randomizer bật (chép theo hàm 0x0963EDD0 của AowVN)."""
        rz = self.profile.randomizer
        if '_rand_banned' not in self.__dict__:
            o, ban = self._o(rz['banned']), set()
            while struct.unpack_from('<H', self.d, o)[0] != 0xFEFE:
                ban.add(struct.unpack_from('<H', self.d, o)[0])
                o += 2
            self._rand_banned = ban
        if not 1 <= sp <= rz['max_sp']:
            return sp
        k = max(1, tid)
        while True:
            sp = max(1, ((sp * k) & 0xFFFFFFFF) % rz['mod'])
            if sp not in self._rand_banned:
                return sp

    def wild_maps(self):
        """[(nhóm, số, tên)] mọi map có Pokémon hoang dã."""
        d, T, out = self.d, self._o(self.profile.wild_headers), []
        for i in range(400):
            e = T + 20 * i
            if d[e] == 0xFF:
                break
            out.append((d[e], d[e + 1], self.map_name(d[e], d[e + 1])))
        return out

    def wild_for_map(self, g, n):
        """None nếu map không có Pokémon hoang dã; ngược lại dict phương thức -> (tỉ lệ gặp, danh sách ô)."""
        d, T = self.d, self._o(self.profile.wild_headers)
        for i in range(400):
            e = T + 20 * i
            if d[e] == 0xFF:
                return None
            if d[e] == g & 0xFF and d[e + 1] == n & 0xFF:
                ptrs = struct.unpack_from('<4I', d, e + 4)
                out = {}
                for key, p, cnt in zip(('land', 'water', 'rock', 'fish'), ptrs, (12, 5, 5, 10)):
                    if not p:
                        continue
                    rate = d[self._o(p)]
                    arr = self._o(struct.unpack_from('<I', d, self._o(p) + 4)[0])
                    if not 0 <= arr <= len(d) - 4 * cnt:   # con trỏ hỏng (AowVN: nước của S.S. Anne 1.4) -> bỏ qua
                        continue
                    slots = [(d[arr + 4 * j], d[arr + 4 * j + 1], struct.unpack_from('<H', d, arr + 4 * j + 2)[0]) for j in range(cnt)]
                    out[key] = (rate, slots)
                return out
        return None


# ---------------------------------------------------------------- huyền thoại lang thang do tool thả
# Huyền thoại + thần thoại Gen 1-8 (không Ultra Beast, Type: Null, Cosmog). Chọn theo TÊN, lấy mã loài nhỏ nhất = dạng gốc
# (bảng số Pokédex của hack lệch ở vài loài, vd Glastrier ở 488, Calyrex = 0). Thêm dạng riêng của hack theo mã.
LEGEND_NAMES = (
    'Articuno Zapdos Moltres Mewtwo Mew Raikou Entei Suicune Lugia Ho-Oh Celebi Regirock Regice Registeel Latias Latios '
    'Kyogre Groudon Rayquaza Jirachi Deoxys Uxie Mesprit Azelf Dialga Palkia Heatran Regigigas Giratina Cresselia Phione '
    'Manaphy Darkrai Shaymin Arceus Victini Cobalion Terrakion Virizion Tornadus Thundurus Reshiram Zekrom Landorus Kyurem '
    'Keldeo Meloetta Genesect Xerneas Yveltal Zygarde Diancie Hoopa Volcanion Solgaleo Lunala Necrozma Magearna Marshadow '
    'Zeraora Meltan Melmetal Zacian Zamazenta Eternatus Kubfu Urshifu Zarude Regieleki Regidrago Glastrier Spectrier Calyrex'
).split() + ['Tapu Koko', 'Tapu Lele', 'Tapu Bulu', 'Tapu Fini']
LEGEND_EXTRA = (1193, 1217, 1218, 1219)        # AowVN: Dark Lugia, Articuno/Zapdos/Moltres Galar (dùng trong sự kiện của hack)


def legend_species(rom):
    """Danh sách mã loài huyền thoại để thả (dạng gốc theo tên + dạng riêng của hack)."""
    first = {}
    for sp in range(1, rom.max_species + 1):
        first.setdefault(rom.species_name(sp), sp)
    out = [first[n] for n in LEGEND_NAMES if n in first]
    return out + [sp for sp in LEGEND_EXTRA if sp <= rom.max_species and sp not in out]


def make_roamer(rom, species, level, perfect=3, rng=None):
    """0x18 byte một ô roamer như hàm tạo roamer của game (0x09673CD8): IV ngẫu nhiên với `perfect` chỉ số = 31,
    PID ngẫu nhiên, HP đầy (công thức đời 3, EV 0), gặp cả trên cạn lẫn dưới nước, đặt ở route đầu của một cụm ngẫu nhiên."""
    import random
    rng = rng or random.SystemRandom()
    iv = [rng.randrange(32) for _ in range(6)]
    for k in rng.sample(range(6), perfect):
        iv[k] = 31
    ivw = sum(v << (5 * k) for k, v in enumerate(iv))        # thứ tự đời 3: HP, Atk, Def, Spe, SpA, SpD
    hp = (2 * rom.base_stats(species)[0] + iv[0]) * level // 100 + level + 10
    base, cnt, per = rom.profile.roam_sets
    mapnum = rom.d[rom._o(base) + per * rng.randrange(cnt)]
    return (struct.pack('<IIHHBBBB', ivw, rng.getrandbits(32), species, hp, level, 0, 1, 1)
            + bytes(6) + bytes([3, mapnum]))


# ---------------------------------------------------------------- Exp. Share cho kho PC
def exp_share_gain(b, L, Lp, s=2, t=10, e=10, f=10, v=10):
    """EXP một con nhận khi hạ 1 đối thủ — ExpCalculator của CFRU (công thức co giãn Gen 5/7, số nguyên).
    b: EXP gốc Gen 7 của đối thủ, L: level đối thủ, Lp: level người nhận, s: 1 = ra trận, 2 = chỉ nhờ Exp. Share;
    t/e/f/v (phần mười): đổi tay 15, Lucky Egg 15, thân thiết >= 220 thì 12, lẽ ra đã tiến hoá 12.
    Đã khớp 12/12 số đo trong game (04/11)."""
    x = (b * L) // (5 * s)
    x = x * (2 * L + 10) ** 2 // ((L + Lp + 10) ** 2 * math.isqrt(L + Lp + 10))
    x = x * math.isqrt(2 * L + 10) + 1
    return max(1, min(1640000, x * t * e * v // 1000 * f // 10))


# IsLevelUpEvolutionMethod của CFRU: các kiểu tiến hoá có param = level
EVO_LEVEL_METHODS = {4, 8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 21, 22, 23, 28, 31, 32, 35}


def could_have_evolved(rom, sp, level):
    """CouldHaveEvolvedViaLevelUp của CFRU: có mục tiến hoá theo level mà level hiện tại đã đạt (dừng ở method 0)."""
    tb, per = rom.profile.evo_table
    o = rom._o(tb) + sp * per * 8
    for k in range(per):
        method, param = struct.unpack_from('<HH', rom.d, o + k * 8)
        if method == 0:
            break
        if (method & 0xFF) in EVO_LEVEL_METHODS and level >= param:
            return True
    return False


def prev_evolutions(rom):
    """{loài: {các loài tiến hoá thẳng ra nó}} theo bảng tiến hoá DPE (mọi kiểu tiến hoá). Dựng một lần cho mỗi ROM."""
    cache = rom.__dict__.get('_prev_evo')
    if cache is None:
        tb, per = rom.profile.evo_table
        cache = {}
        for s in range(1, rom.max_species + 1):
            o = rom._o(tb) + s * per * 8
            for k in range(per):
                method, _, to = struct.unpack_from('<HHH', rom.d, o + k * 8)
                if method == 0:
                    break
                if 1 <= to <= rom.max_species and to != s:
                    cache.setdefault(to, set()).add(s)
        rom._prev_evo = cache
    return cache


def wild_ancestors(rom, sp, wild):
    """Các loài trước sp trong chuỗi tiến hoá mà gặp được hoang dã (wild = tập loài gặp được), gần sp nhất trước."""
    prev, out, seen, q = prev_evolutions(rom), [], {sp}, [sp]
    while q:
        nxt = []
        for s in q:
            for p in sorted(prev.get(s, ())):
                if p not in seen:
                    seen.add(p)
                    nxt.append(p)
                    if p in wild:
                        out.append(p)
        q = nxt
    return out


def level_evolution(rom, sp, level):
    """Loài đích nếu đã đủ cấp theo kiểu tiến hoá chỉ cần cấp (method 4); game duyệt đủ 16 mục, mục khớp sau cùng thắng."""
    tb, per = rom.profile.evo_table
    o = rom._o(tb) + sp * per * 8
    target = None
    for k in range(per):
        method, param, to = struct.unpack_from('<HHH', rom.d, o + k * 8)
        if method == 4 and level >= param and 1 <= to <= rom.max_species:
            target = to
    return target


def box_evolve(rom, box):
    """Đổi loài (sửa box tại chỗ) cho con đủ cấp, theo cả chuỗi nếu vượt nhiều mốc. Bỏ qua trứng và con cầm Everstone
    (mã hiệu ứng 38, game cũng chặn ở 0x09655B64). Biệt danh chỉ đổi nếu đang là tên loài cũ, chiêu giữ nguyên.
    Trả về [(ô, loài cũ, loài mới)]."""
    p = rom.profile
    recs, size = rom._o(p.item_recs[0]), p.item_recs[1]
    out = []
    for o in range(0, len(box) - p.box_size + 1, p.box_size):
        first = sp = struct.unpack_from('<H', box, o + p.box_species)[0]
        if not 1 <= sp <= p.max_species or struct.unpack_from('<I', box, o + 0x36)[0] >> 30 & 1:
            continue
        item = struct.unpack_from('<H', box, o + p.box_item)[0]
        if item <= p.max_item and rom.d[recs + size * item + p.item_hold_off] == 38:
            continue
        exp = struct.unpack_from('<I', box, o + p.box_exp)[0]
        seen = {sp}
        while True:
            to = level_evolution(rom, sp, rom.level_for(rom.growth(sp), exp))
            if to is None or to in seen:
                break
            sp = to
            seen.add(sp)
        if sp == first:
            continue
        struct.pack_into('<H', box, o + p.box_species, sp)
        if bytes(box[o + 8:o + 18]).split(b'\xff', 1)[0] == rom.species_name_bytes(first).split(b'\xff', 1)[0]:
            box[o + 8:o + 18] = rom.species_name_bytes(sp)
        out.append((o // p.box_size, first, sp))
    return out


def box_exp_share(rom, foes, box, player_otid):
    """Cộng EXP cho mọi Pokémon trong kho PC như một con đứng ngoài nhận Exp. Share (s = 2), lần lượt từng đối thủ
    bị hạ (level người nhận tính lại giữa các đối thủ). Không có giới hạn level (CFRU mặc định không bật).
    foes: [(loài, level)]; box: bytearray kho (sửa tại chỗ). Trả về số con được cộng."""
    p = rom.profile
    tb = rom._o(p.base_exp_table)
    yields = [rom.d[tb + 2 * sp] | rom.d[tb + 2 * sp + 1] << 8 for sp, _ in foes]
    count = 0
    for o in range(0, len(box) - p.box_size + 1, p.box_size):
        sp = struct.unpack_from('<H', box, o + p.box_species)[0]
        if not 1 <= sp <= p.max_species:
            continue
        exp = struct.unpack_from('<I', box, o + p.box_exp)[0]
        rate = rom.growth(sp)
        top = rom.exp_for(rate, 100)
        if exp >= top:
            continue
        t = 15 if struct.unpack_from('<I', box, o + 4)[0] != player_otid else 10
        e = 15 if struct.unpack_from('<H', box, o + p.box_item)[0] == p.lucky_egg else 10
        f = 12 if box[o + p.box_friend] >= 220 else 10
        for y, (_, lf) in zip(yields, foes):
            lp = rom.level_for(rate, exp)
            if lp >= 100:
                break
            v = 12 if could_have_evolved(rom, sp, lp) else 10
            exp = min(top, exp + exp_share_gain(y, lf, lp, 2, t, e, f, v))
        struct.pack_into('<I', box, o + p.box_exp, exp)
        count += 1
    return count


# ---------------------------------------------------------------- chuyển đổi đội <-> kho PC (FireRed: ô kho = 80 byte đầu)
BOX_MON_SIZE, BOX_CAPACITY = 80, 30
cell_species = fr_cell_species


def party_to_box(m):
    """Ô kho 80 byte = 80 byte đầu của con trong đội (đã mã hoá), như game."""
    return m.to_bytes()[:BOX_MON_SIZE]


def box_to_party(rom, b):
    """Ô kho -> con trong đội như game (BoxMonToMon): tính level + chỉ số, hồi đầy, không giữ thư."""
    raw = bytearray(bytes(b[:BOX_MON_SIZE]).ljust(MON_SIZE, b'\0'))
    raw[0x55] = 0xFF
    crc = fr_decrypt(raw)[1]
    m = FrMon(raw)
    m.recalc(rom)
    m.full_restore(rom)
    # ô kho không có level/HP nên lúc tạo luôn bị coi là "chưa hợp lệ"; kiểm lại sau khi đã tính level + HP
    m.checksum_ok = (crc and not m.bad_egg and not m.empty and 1 <= m.level <= 100 and 0 < m.maxhp <= 9999
                     and m.species <= m.MAX_SPECIES)
    return m


# cách sắp xếp kho (Duy 07/11): mã -> tên hiện trên giao diện; hoà nhau thì theo Pokédex
SORT_MODES = [('dex', 'Pokédex'), ('shiny', 'Shiny trước'), ('iv', 'IV cao trước'), ('level', 'Level cao trước')]


def sort_box_cells(rom, cells, by='dex'):
    """Xếp các ô kho, dồn về đầu. by = 'dex' (số Pokédex quốc gia; cùng loài: shiny trước, rồi IV cao) /
    'shiny' (shiny trước, rồi như dex) / 'iv' (tổng IV giảm dần) / 'level' (level giảm dần, rồi EXP)."""
    def key(c):
        sp = cell_species(c)
        m = box_to_party(rom, c)
        dex = (rom.natdex(sp), sp, not m.is_shiny_in_game(), -sum(m.iv))
        return {'dex': dex, 'shiny': (not m.is_shiny_in_game(),) + dex, 'iv': (-sum(m.iv),) + dex,
                'level': (-m.level, -m.exp) + dex}[by]
    filled = []
    for i, c in enumerate(cells):
        if any(c):
            if not 1 <= cell_species(c) <= rom.max_species:
                raise ValueError('Box %d, ô %d có dữ liệu lạ, không sắp xếp.' % (i // BOX_CAPACITY + 1, i % BOX_CAPACITY + 1))
            filled.append(c)
    return sorted(filled, key=key) + [bytes(BOX_MON_SIZE)] * (len(cells) - len(filled))


# ---------------------------------------------------------------- cầu nối mGBA
class BridgeError(Exception):
    pass


class _Snapshot:
    """Bản chụp bộ nhớ cho một nhịp làm mới: đọc trước nhiều vùng trong một lệnh, các lần đọc sau nằm gọn trong
    vùng đã chụp thì lấy luôn (mỗi lệnh qua bridge ~50 ms, giao diện đứng trong lúc chờ). Ghi bất kỳ = bỏ bản chụp."""
    _snap = None

    def snapshot(self, pairs):
        data = self._read_many(pairs)
        self._snap = (self._snap or []) + [(a, d) for (a, _), d in zip(pairs, data)]

    def end_snapshot(self):
        self._snap = None

    def _cached(self, addr, n):
        for a, d in self._snap or ():
            if a <= addr and addr + n <= a + len(d):
                return d[addr - a:addr - a + n]
        return None

    def read(self, addr, n):
        hit = self._cached(addr, n)
        return hit if hit is not None else self._read(addr, n)

    def read_many(self, pairs):
        hits = [self._cached(a, n) for a, n in pairs]
        return hits if all(h is not None for h in hits) else self._read_many(pairs)

    def write(self, addr, data):
        self._snap = None
        self._write(addr, data)

    def write_many(self, pairs):
        self._snap = None
        self._write_many(pairs)

    def write_cas(self, items):
        """items = [(địa chỉ, byte cũ, byte mới)]: ghi tất cả chỉ khi MỌI vùng còn đúng byte cũ (kiểm + ghi cùng
        một khung hình). True = đã ghi. Dùng cho Pokémon: game giải mã tại chỗ, ghi chen vào giữa là hỏng con."""
        self._snap = None
        return self._write_cas(items)

    def read_u32(self, addr):
        return struct.unpack('<I', self.read(addr, 4))[0]


class Bridge(_Snapshot):
    """Nói chuyện với mm_bridge.lua qua cmd.txt / resp.txt."""
    def __init__(self, ipc_dir=IPC_DIR, timeout=3.0):
        self.dir, self.timeout, self.n = ipc_dir, timeout, 0
        os.makedirs(ipc_dir, exist_ok=True)

    def _send(self, ops):
        self.n += 1
        cid = '%d-%d' % (int(time.time() * 1000), self.n)
        resp = os.path.join(self.dir, 'resp.txt')
        try:
            os.remove(resp)
        except OSError:
            pass
        tmp = os.path.join(self.dir, 'cmd.tmp')
        with open(tmp, 'w', newline='\n') as f:
            f.write(cid + '\n' + '\n'.join(ops))
        for _ in range(50):                       # Lua có thể đang mở cmd.txt -> thử lại
            try:
                os.replace(tmp, os.path.join(self.dir, 'cmd.txt'))
                break
            except OSError:
                time.sleep(0.02)
        end = time.time() + self.timeout
        while time.time() < end:
            try:
                with open(resp, 'r') as f:
                    lines = f.read().split('\n')
            except OSError:
                lines = []
            if len(lines) >= 3 and lines[0] == cid and lines[-1] == 'END':   # END = Lua đã ghi xong
                if lines[1] != 'OK':
                    raise BridgeError(lines[1])
                return lines[2:-1]
            time.sleep(0.02)
        raise BridgeError('mGBA không trả lời (đã nạp mm_bridge.lua chưa?)')

    def _read(self, addr, n):
        return bytes.fromhex(self._send(['R %08x %d' % (addr, n)])[0])

    def _read_many(self, pairs):
        """Đọc nhiều chỗ trong cùng một lệnh: Lua làm hết trong một khung hình."""
        return [bytes.fromhex(x) for x in self._send(['R %08x %d' % p for p in pairs])]

    def _write(self, addr, data):
        self._send(['W %08x %s' % (addr, bytes(data).hex())])

    def _write_many(self, pairs):
        """Ghi nhiều chỗ trong cùng một lệnh: Lua làm hết trong một khung hình."""
        self._send(['W %08x %s' % (a, bytes(d).hex()) for a, d in pairs])

    def _write_cas(self, items):
        res = self._send(['C %08x %s %s' % (a, bytes(o).hex(), bytes(n).hex()) for a, o, n in items])
        return res == ['1']


class FakeBridge(_Snapshot):
    """Bộ nhớ giả để kiểm thử không cần mGBA."""
    def __init__(self):
        self.mem = {}

    def _read(self, addr, n):
        return bytes(self.mem.get(addr + i, 0) for i in range(n))

    def _read_many(self, pairs):
        return [self._read(a, n) for a, n in pairs]

    def _write(self, addr, data):
        for i, b in enumerate(data):
            self.mem[addr + i] = b

    def _write_many(self, pairs):
        for a, d in pairs:
            self._write(a, d)

    def _write_cas(self, items):
        if any(self._read(a, len(o)) != bytes(o) for a, o, _ in items):
            return False
        self._write_many([(a, n) for a, _, n in items])
        return True


# ---------------------------------------------------------------- mở khoá săn shiny, gói A (Duy chốt 11/11)
# Số lấy từ pokeemerald (pret): include/constants/flags.h, vars.h, include/global.h, src/event_data.c; xem NHAT_KY 11/11.
# Gói A = đi lại tự do, KHÔNG đụng cốt truyện: không cờ trainer/vật phẩm/huyền thoại, không cờ ẩn NPC, không biến cốt
# truyện, KHÔNG bật FLAG_SYS_GAME_CLEAR (22 script kiểm cờ này và giả định cốt truyện đã xong). Vẫn chơi tiếp cốt truyện được.
UNLOCK_FLAGS_SET = (
    list(range(0x867, 0x86F))            # FLAG_BADGE01-08_GET (flags.h:1359-1366): dùng HM ngoài trận
    + list(range(0x86F, 0x87F))          # FLAG_VISITED_* 16 thị trấn (flags.h:1370-1385): Bay
    + [0x8C0,                            # FLAG_SYS_B_DASH (flags.h:1462): giày chạy
       0x896])                           # FLAG_SYS_NATIONAL_DEX (flags.h:1414), cùng biến + SaveBlock2 bên dưới
UNLOCK_VARS = {0x4046: 0x302}            # VAR_NATIONAL_DEX (vars.h:90) = 0x302 (event_data.c:67)
NATDEX_BYTES = (0x18, bytes([0, 1, 0xDA]))   # SaveBlock2.pokedex: order 0, mode 1 = National, nationalMagic 0xDA (event_data.c:66-70)
# HM01-08, Old/Good/Super Rod, Mach + Acro Bike, Go-Goggles (sa mạc Route 111: Route111/scripts.inc:190),
# Devon Scope (Kecleon chặn Route 119/120 + gym Fortree: kecleon.inc:51, FortreeCity/scripts.inc:58). Mã đọc từ ROM theo tên.
UNLOCK_ITEMS = (339, 340, 341, 342, 343, 344, 345, 346, 262, 263, 264, 259, 272, 279, 288)


# ---------------------------------------------------------------- trạng thái game
class Game:
    def __init__(self, bridge, rom):
        self.b, self.rom, self.p = bridge, rom, rom.profile

    def snapshot_tick(self):
        """Chụp trước mọi vùng mà vòng làm mới mỗi giây hay đọc: 2 lệnh qua bridge thay cho ~25 lệnh lẻ."""
        p, opt = self.p, lambda k: getattr(self.p, k, None)
        pairs = [(p.sb1_ptr, 4), (p.sb2_ptr, 4), (p.party_base, MON_SIZE * PARTY_SLOTS),
                 (p.enemy_base, MON_SIZE * PARTY_SLOTS)]
        if opt('cb2_addr'):
            pairs.append((p.cb2_addr, 4))
        if opt('battle_flag'):
            pairs.append((p.battle_flag[0], 1))
        if opt('dex_caught'):
            pairs.append(tuple(p.dex_caught))
        if opt('randomizer'):
            pairs.append((p.randomizer['flag_ram'][1], 512))           # cờ 0x900-0x18FF của hack
        if opt('roamers'):
            pairs.append((p.roamers[0], 0x18 * p.roamers[1]))
        if opt('fly'):
            pairs += [(p.fly['lock'], 1), (p.fly['map_type'], 1)]
        if opt('player_obj'):
            pairs.append((p.player_obj, 0x24))
        if opt('party_count'):
            pairs.append((p.party_count, 1))
        self.b.snapshot(pairs)
        sb1, sb2 = self.sb1(), self.sb2()
        rel = [(sb1 + p.loc_off, 2), (sb2 + 0xA, 4)]
        if opt('dex_owned_sb2'):
            rel.append((sb2 + p.dex_owned_sb2[0], p.dex_owned_sb2[1]))
        if opt('flags_off'):
            rel.append((sb1 + p.flags_off, 0x900 // 8))
        if opt('shiny_boost_off'):
            rel.append((sb1 + p.shiny_boost_off, 4))
        self.b.snapshot(rel)

    def sb1(self):
        return self.b.read_u32(self.p.sb1_ptr)

    def sb2(self):
        return self.b.read_u32(self.p.sb2_ptr)

    def key32(self):
        return self.b.read_u32(self.sb2() + self.p.key_off)

    # Pokémon
    def _party_at(self, base):
        raw = self.b.read(base, MON_SIZE * PARTY_SLOTS)
        return [self.p.mon_cls(raw[i * MON_SIZE:(i + 1) * MON_SIZE]) for i in range(PARTY_SLOTS)]

    def party(self):
        return self._party_at(self.p.party_base)

    def enemy_party(self):
        return self._party_at(self.p.enemy_base)

    def current_map(self):
        """(nhóm, số) map hiện tại trong SaveBlock1."""
        raw = self.b.read(self.sb1() + self.p.loc_off, 2)
        return raw[0], raw[1]

    def caught_dex(self):
        """Tập số Pokédex đã bắt; None nếu game này chưa hỗ trợ."""
        sb = getattr(self.p, 'dex_owned_sb2', None)
        if not sb:
            return None
        raw = self.b.read(self.sb2() + sb[0], sb[1])
        return {i + 1 for i in range(len(raw) * 8) if raw[i >> 3] >> (i & 7) & 1}

    def battle_state(self):
        """(đang trong trận?, đang ở overworld?) hoặc None nếu game này chưa hỗ trợ."""
        bf = getattr(self.p, 'battle_flag', None)
        if not bf:
            return None
        addr, bit = bf
        return bool(self.b.read(addr, 1)[0] & bit), self.b.read_u32(self.p.cb2_addr) == self.p.cb2_overworld

    def mark_dex(self, species):
        """Bật cờ đã thấy + đã bắt của các loài (game cũng làm vậy khi tiến hoá).
        owned/seen ở SaveBlock2 + 0x28/+0x5C, thêm 2 bản sao "seen" ở SaveBlock1 (hồ sơ: dex_seen_sb1)."""
        sb1, sb2 = self.sb1(), self.sb2()
        for sp in species:
            n = self.rom.natdex(sp) - 1
            if 0 <= n < 386:
                for base in (sb2 + 0x28, sb2 + 0x5C) + tuple(sb1 + o for o in self.p.dex_seen_sb1):
                    a = base + (n >> 3)
                    self.b.write(a, bytes([self.b.read(a, 1)[0] | 1 << (n & 7)]))

    def exp_share_on(self):
        """Exp. Share đang bật trong game? None nếu game này chưa hỗ trợ."""
        f = getattr(self.p, 'exp_share_flag', None)
        if not f:
            return None
        first, base = self.p.randomizer['flag_ram']
        return bool(self.b.read(base + (f - first) // 8, 1)[0] >> (f & 7) & 1)

    def read_box(self):
        """(danh sách địa chỉ các box, bytearray toàn bộ kho PC nối liền theo thứ tự box)."""
        addrs = [self.box_addr(i) for i in range(self.p.box_slots // BOX_CAPACITY)]
        size = BOX_CAPACITY * self.p.box_size
        return addrs, bytearray(b''.join(self.b.read_many([(a, size) for a in addrs])))

    def write_box(self, addrs, old, new):
        """Chỉ ghi lại các box có thay đổi."""
        size = BOX_CAPACITY * self.p.box_size
        for i, a in enumerate(addrs):
            o = i * size
            if new[o:o + size] != old[o:o + size]:
                self.b.write(a, new[o:o + size])

    def box_addr(self, box):
        """FireRed: gPokemonStoragePtr -> 4 byte rồi 14 box liền nhau."""
        return self.b.read_u32(self.p.storage_ptr) + 4 + box * BOX_CAPACITY * BOX_MON_SIZE

    def read_one_box(self, box):
        """30 ô của một box, mỗi ô 80 byte (mã hoá)."""
        raw = self.b.read(self.box_addr(box), BOX_CAPACITY * BOX_MON_SIZE)
        return [raw[i * BOX_MON_SIZE:(i + 1) * BOX_MON_SIZE] for i in range(BOX_CAPACITY)]

    def _require_overworld(self):
        st = self.battle_state()
        if not st or st[0] or not st[1]:
            raise ValueError('Chỉ thao tác được khi đang đi trên bản đồ (không trong trận, không mở menu).')

    def _party_now(self):
        """Đội hiện tại; dừng lại nếu số con không khớp bộ đếm của game."""
        party = [m for m in self.party() if not m.empty]
        n = self.b.read(self.p.party_count, 1)[0]
        if n != len(party):
            raise ValueError('Số con trong đội không khớp (%d/%d), không thao tác.' % (n, len(party)))
        return party

    def move_party(self, src, dst):
        """Chuyển con ở vị trí src tới vị trí dst của đội, các con giữa dồn lại (như "Đổi chỗ" của game nhưng chèn)."""
        self._require_overworld()
        party = self._party_now()
        if not (0 <= src < len(party) and 0 <= dst < len(party)):
            raise ValueError('Vị trí ngoài đội (%d con).' % len(party))
        party.insert(dst, party.pop(src))
        self.b.write(self.p.party_base, b''.join(bytes(m.enc) for m in party))   # byte gốc trong RAM, không mã hoá lại

    def move_item(self, idx, src, dst):
        """Chuyển món ở vị trí src tới vị trí dst trong ngăn túi idx, các món giữa dồn lại; số lượng giữ nguyên."""
        self._require_overworld()
        items = self.read_pocket(idx)
        if not (0 <= src < len(items) and 0 <= dst < len(items)):
            raise ValueError('Vị trí ngoài ngăn túi (%d món).' % len(items))
        items.insert(dst, items.pop(src))
        self.write_pocket(idx, items)

    def deposit(self, slot):
        """Gửi con ở vị trí slot của đội vào ô trống đầu tiên của kho, tính từ Box 1. Trả về (box, ô), tính từ 0."""
        self._require_overworld()
        party = self._party_now()
        m = party[slot]
        if m.raw[0x55] != 0xFF:
            raise ValueError('Con này đang giữ thư, hãy gỡ thư trước.')
        rest = party[:slot] + party[slot + 1:]
        if not any(x.hp > 0 and not x.egg for x in rest):
            raise ValueError('Phải còn ít nhất 1 con chiến đấu được trong đội.')
        addrs, cells = self.read_box()
        free = next((i for i in range(len(cells) // BOX_MON_SIZE)
                     if not any(cells[i * BOX_MON_SIZE:(i + 1) * BOX_MON_SIZE])), None)     # ô trống = toàn 0
        if free is None:
            raise ValueError('Kho đã đầy.')
        box, cell = divmod(free, BOX_CAPACITY)
        data = b''.join(bytes(x.enc) for x in rest) + bytes(MON_SIZE * (PARTY_SLOTS - len(rest)))
        self.b.write_many([(addrs[box] + cell * BOX_MON_SIZE, party_to_box(m)),
                           (self.p.party_base, data), (self.p.party_count, bytes([len(rest)]))])
        return box, cell

    def withdraw(self, box, cell):
        """Lấy con ở ô cell của box về cuối đội. Trả về con vừa lấy."""
        self._require_overworld()
        party = self._party_now()
        if len(party) >= PARTY_SLOTS:
            raise ValueError('Đội đã đủ %d con.' % PARTY_SLOTS)
        c = self.read_one_box(box)[cell]
        if not 1 <= cell_species(c) <= self.p.max_species:
            raise ValueError('Ô này đang trống.')
        m = box_to_party(self.rom, c)
        self.b.write_many([(self.p.party_base + len(party) * MON_SIZE, m.to_bytes()),
                           (self.box_addr(box) + cell * BOX_MON_SIZE, bytes(BOX_MON_SIZE)),
                           (self.p.party_count, bytes([len(party) + 1]))])
        return m

    def release(self, box, cell):
        """Thả con ở ô cell của box (xoá trắng ô)."""
        self._require_overworld()
        c = self.read_one_box(box)[cell]
        if not any(c):
            raise ValueError('Ô này đang trống.')
        self.b.write(self.box_addr(box) + cell * BOX_MON_SIZE, bytes(BOX_MON_SIZE))

    def sort_boxes(self, by='dex'):
        """Sắp xếp cả kho (by: xem SORT_MODES), ghi các box đổi trong cùng một khung hình. Trả về số con."""
        self._require_overworld()
        addrs, data = self.read_box()
        cells = [bytes(data[i:i + BOX_MON_SIZE]) for i in range(0, len(data), BOX_MON_SIZE)]
        new = sort_box_cells(self.rom, cells, by)
        self._require_overworld()
        pairs = []
        for i, a in enumerate(addrs):
            row = b''.join(new[i * BOX_CAPACITY:(i + 1) * BOX_CAPACITY])
            if row != b''.join(cells[i * BOX_CAPACITY:(i + 1) * BOX_CAPACITY]):
                pairs.append((a, row))
        if pairs:
            self.b.write_many(pairs)
        return sum(1 for c in cells if any(c))

    def flags(self):
        """Hàm cờ -> 0/1 (None nếu ngoài vùng) theo cờ hiện tại trong RAM; một lệnh đọc."""
        raw = self.b.read(self.sb1() + self.p.flags_off, 0x900 // 8)        # 0x900 cờ đầu, ở SaveBlock1

        def get(f):
            return raw[f >> 3] >> (f & 7) & 1 if 0 <= f >> 3 < len(raw) else None
        return get

    def unlock_all(self):
        """Gói mở khoá (UNLOCK_*): cờ + biến + National Dex ghi trong một khung hình, chỉ khi RAM còn y lúc đọc (game
        đổi giữa chừng thì đọc lại, thử lại); xong thì thêm vật phẩm còn thiếu. Trả về tên vật phẩm đã thêm."""
        self._require_overworld()
        n = 0x12C                                              # NUM_FLAG_BYTES Emerald (0x1270..0x139C)
        for _ in range(5):
            sb1, sb2 = self.sb1(), self.sb2()
            fa, va = sb1 + self.p.flags_off, sb1 + self.p.vars_off
            old = self.b.read(fa, n)
            new = bytearray(old)
            for f in UNLOCK_FLAGS_SET:
                new[f >> 3] |= 1 << (f & 7)
            items = [(fa, old, bytes(new))]
            for v, val in UNLOCK_VARS.items():
                a = va + 2 * (v - 0x4000)
                items.append((a, self.b.read(a, 2), struct.pack('<H', val)))
            a = sb2 + NATDEX_BYTES[0]
            items.append((a, self.b.read(a, len(NATDEX_BYTES[1])), NATDEX_BYTES[1]))
            if self.b.write_cas(items):
                break
            time.sleep(0.05)
        else:
            raise ValueError('Cờ trong game đổi liên tục, chưa ghi được. Đứng yên rồi thử lại.')
        have = {i for k in range(self.p.n_pockets) for i, q in self.read_pocket(k) if q}
        added = []
        for it in UNLOCK_ITEMS:
            if it not in have:
                self.set_item(it, 1)
                added.append(self.rom.item_name(it))
        return added

    def player_xy(self):
        """Ô người chơi đang đứng trên map (toạ độ object trừ lề 7 ô)."""
        x, y = struct.unpack('<hh', self.b.read(self.p.player_obj + 0x10, 4))
        return x - 7, y - 7

    # bấm phím qua mm_bridge.lua (lệnh K/S, cộng với phím thật, không cần mGBA đứng trước)
    KEYS = dict(A=1, B=2, SELECT=4, START=8, RIGHT=0x10, LEFT=0x20, UP=0x40, DOWN=0x80, R=0x100, L=0x200)

    def press(self, seq):
        """seq = [(tên phím hoặc None = chờ, số khung)]: Lua giữ lần lượt từng phím đủ số khung."""
        if not hasattr(self.b, '_send'):
            raise BridgeError('bộ nhớ giả không bấm phím được')
        self.b._send(['K %x %d' % (self.KEYS[k] if k else 0, n) for k, n in seq])

    def keys_left(self):
        """Số khung phím còn trong hàng của Lua (0 = bấm xong)."""
        return int(self.b._send(['S 0 0'])[0])

    # tự bắt (AowVN)
    def battle_ui(self):
        """'action' (chờ chọn lệnh) / 'move' (chờ chọn chiêu) / 'bag' (túi đang mở) / None (chữ, hoạt cảnh...)."""
        p = self.p
        cb2 = self.b.read_u32(p.cb2_addr)
        if cb2 == p.cb2_bag:
            return 'bag'
        if cb2 != p.cb2_battle:                 # màn Pokédex / biệt danh sau khi bắt: controller còn giá trị cũ
            return None
        f = self.b.read_u32(p.battle_ctl)
        return {p.ctl_action: 'action', p.ctl_move: 'move'}.get(f)

    def lead_moves(self):
        """[(chiêu, PP)] của con mình đang ra trận (gBattleMons[0])."""
        raw = self.b.read(self.p.battle_mons, 0x2A)
        return [(struct.unpack_from('<H', raw, 0x0C + 2 * i)[0], raw[0x24 + i]) for i in range(4)]

    def battle_lead_hp(self):
        """(HP, HP tối đa) của con mình đang ra trận (gBattleMons[0]: +0x28 HP, +0x2C max; đo 07/11 khớp game)."""
        return struct.unpack('<HxxH', self.b.read(self.p.battle_mons + 0x28, 6))   # HP, level, thân thiết, max

    def heal_battle_lead(self):
        """Hồi đầy HP con mình đang ra trận ngay trong trận (chỉ HP; hết trận tool tự hồi phục cả đội như cũ)."""
        mx = struct.unpack('<H', self.b.read(self.p.battle_mons + 0x2C, 2))[0]
        if mx:
            self.b.write(self.p.battle_mons + 0x28, struct.pack('<H', mx))
        return mx

    def ball_index(self, item):
        """(vị trí của bóng trong ngăn Poké Ball, số món trong ngăn, số lượng bóng); vị trí None nếu hết."""
        items = [(i, q) for i, q in self.read_pocket(self.p.ball_pocket) if i and q]
        for k, (i, q) in enumerate(items):
            if i == item:
                return k, len(items), q
        return None, len(items), 0

    def set_bag_cursor(self, idx, n):
        """Ghi gBagPosition để lần mở Túi tới mở đúng ngăn Poké Ball, con trỏ ở đầu ngăn. Emerald: chưa đo số dòng
        hiện được nên không đặt thẳng món idx; hunt_catch bấm xuống tới đúng món (theo bag_cursor)."""
        p, k = self.p, self.p.ball_pocket
        raw = bytearray(self.b.read(p.bag_state, 0x1C))
        raw[5] = k
        struct.pack_into('<H', raw, 8 + 2 * k, 0)
        struct.pack_into('<H', raw, 0x12 + 2 * k, 0)
        self.b.write(p.bag_state, bytes(raw))

    def bag_cursor(self):
        """(ngăn, món đang chọn) của Túi (gBagPosition Emerald: ngăn u8 +5, con trỏ[5] +8, cuộn[5] +0x12)."""
        raw = self.b.read(self.p.bag_state, 0x1C)
        k = raw[5]
        if k > 4:
            return k, None
        return k, struct.unpack_from('<H', raw, 8 + 2 * k)[0] + struct.unpack_from('<H', raw, 0x12 + 2 * k)[0]

    def player_look(self):
        """(gfx id, hướng 1 xuống/2 lên/3 trái/4 phải) của người chơi."""
        raw = self.b.read(self.p.player_obj, 0x19)
        return raw[5], raw[0x18] & 0xF

    # câu cá (FireRed)
    def fishing_step(self):
        """Bước của task câu cá đang chạy (xem ghi chú `fishing` trong hồ sơ), None nếu không đang câu."""
        f = self.p.fishing
        raw = self.b.read(f['tasks'], 16 * 40)
        for i in range(16):
            fn, active = struct.unpack_from('<IB', raw, 40 * i)
            if active and fn == f['task_fn']:
                return struct.unpack_from('<h', raw, 40 * i + 8)[0]
        return None

    def set_auto_fish(self, on):
        """Bật/tắt lệnh A của mm_bridge.lua: Lua tự bấm A trong đúng khung hình task câu cá tới bước fishing['press_a']
        (cá cắn chỉ chờ ~30 khung; fast forward thì Python không kịp). Lua bản cũ -> BridgeError 'ERR cmd'."""
        if not hasattr(self.b, '_send'):                       # bộ nhớ giả: không có Lua
            return
        f = self.p.fishing
        self.b._send(['A %08x %x %s' % (f['tasks'], f['task_fn'], ','.join(map(str, f['press_a']))) if on else 'A 0 0 0'])

    def registered_item(self):
        return struct.unpack('<H', self.b.read(self.sb1() + self.p.registered_off, 2))[0]

    def set_registered_item(self, item):
        self.b.write(self.sb1() + self.p.registered_off, struct.pack('<H', item))

    def rods(self):
        """Các cần câu đang có trong ngăn Vật phẩm chính (tốt nhất sau cùng)."""
        have = {i for i, q in self.read_pocket(self.p.key_pocket)}
        return [r for r in self.p.fishing['rods'] if r in have]

    # bay + roamer (AowVN)
    def fly_points(self):
        """[(nhóm, số map, x, y)] các điểm bay của game (bảng heal location, thứ tự như game)."""
        f = self.p.fly
        o = self.rom._o(f['heal_table'])
        return [struct.unpack_from('<bbhh', self.rom.d, o + 8 * i) for i in range(f['heal_count'])]

    def fly(self, g, n, x, y):
        """Bay y như chọn một điểm trên bản đồ Fly của game: đặt đích warp + gFieldCallback = FieldCallback_UseFly +
        callback2 = CB2_ReturnToField trong cùng một khung hình; game tự chạy hiệu ứng bay rồi warp.
        Trả về None nếu đã bay, ngược lại là lý do không bay (đang trận, menu, nói chuyện, đang lặn)."""
        f = self.p.fly
        baddr, bbit = self.p.battle_flag
        cb2, lock, mtype, bt = self.b.read_many([(self.p.cb2_addr, 4), (f['lock'], 1), (f['map_type'], 1), (baddr, 1)])
        if struct.unpack('<I', cb2)[0] != self.p.cb2_overworld or bt[0] & bbit:
            return 'Chỉ bay được khi đang đi trên bản đồ (không trong trận, không mở menu).'
        if lock[0]:
            return 'Game đang bận (nói chuyện, mở menu, sự kiện): đóng hết rồi bấm lại.'
        # Duy 07/11: tool bay VÀO hang được nên phải bay RA được (trước đây chỉ cho ngoài trời như game -> kẹt trong
        # Cerulean Cave). Chỉ chặn lúc đang lặn (kiểu map 5 = dưới nước).
        if mtype[0] == 5:
            return 'Đang lặn dưới nước: nổi lên rồi bay.'
        self.b.write_many([(f['warp_dest'], struct.pack('<bbbbhh', g, n, -1, 0, x, y)),
                           (f['field_cb'], struct.pack('<I', f['use_fly'])),
                           (f['main_state'], b'\0'),
                           (self.p.cb2_addr, struct.pack('<I', f['cb2_return']))])
        return None

    def roamers(self):
        """Các Pokémon huyền thoại đang lang thang (roamer CFRU): list dict, bỏ ô trống. FireRed gốc: chưa hỗ trợ -> []."""
        if not getattr(self.p, 'roamers', None):
            return []
        base, cnt = self.p.roamers
        raw = self.b.read(base, 0x18 * cnt)
        out = []
        for i in range(cnt):
            e = raw[0x18 * i:0x18 * i + 0x18]
            ivw, pid, sp, hp, lv, st, land, water = struct.unpack_from('<IIHHBBBB', e)
            if sp and 1 <= sp <= self.rom.max_species:
                out.append(dict(slot=i, species=sp, level=lv, hp=hp, status=st, pid=pid,
                                iv=[(ivw >> (5 * k)) & 31 for k in range(6)], land=bool(land), water=bool(water),
                                map=(e[0x16], e[0x17])))
        return out

    def shiny_counter(self):
        """Bộ đếm tăng tỉ lệ shiny của AowVN."""
        return self.b.read_u32(self.sb1() + self.p.shiny_boost_off)

    def reset_shiny_counter(self):
        self.b.write(self.sb1() + self.p.shiny_boost_off, bytes(4))

    def player_otid(self):
        """ID 32 bit của người chơi (TID | SID<<16). Pokémon hoang dã đời 3 mang luôn ID này."""
        return self.b.read_u32(self.sb2() + 0xA)

    def write_mon(self, slot, mon, tries=5):
        """Ghi con ở ô slot, chỉ khi byte trong RAM còn y như lúc đọc (mon.enc). Game đang giải mã con đó thì
        byte khác -> đợi khung sau thử lại; vẫn khác (game đã đổi con này) -> báo lỗi, không ghi."""
        if not mon.checksum_ok:
            raise ValueError('Dữ liệu ô %d đọc lúc game đang xử lý (checksum sai), hãy tải lại.' % (slot + 1))
        addr, new = self.p.party_base + slot * MON_SIZE, mon.to_bytes()
        for _ in range(tries):
            if self.b.write_cas([(addr, mon.enc, new)]):
                return
            time.sleep(0.05)
        raise ValueError('Ô %d vừa đổi trong game, hãy tải lại rồi thử lại.' % (slot + 1))

    def rand_tid(self):
        """TID 32 bit nếu Randomizer đang bật trong game, ngược lại None."""
        rz = getattr(self.p, 'randomizer', None)
        if not rz:
            return None
        first, base = rz['flag_ram']
        flag = lambda f: self.b.read(base + (f - first) // 8, 1)[0] >> (f & 7) & 1
        if not flag(rz['flag_on']) or flag(rz['flag_off']):
            return None
        return self.b.read_u32(self.sb2() + 0xA)

    # tiền
    def money(self):
        return self.b.read_u32(self.sb1() + self.p.money_off) ^ self.key32()

    def set_money(self, v):
        v = max(0, min(self.p.max_money, int(v)))
        self.b.write(self.sb1() + self.p.money_off, struct.pack('<I', v ^ self.key32()))

    # túi đồ
    def pocket_info(self, idx):
        raw = self.b.read(self.p.pockets_addr + 8 * idx, 8)
        ptr, cap = struct.unpack_from(self.p.pocket_fmt, raw, 0)
        if not (0x02000000 <= ptr and cap > 0 and ptr + 4 * cap <= 0x02040000):
            raise BridgeError('ngăn túi %d không hợp lệ (ptr=%08x cap=%d)' % (idx, ptr, cap))
        return ptr, cap

    def read_pocket(self, idx):
        ptr, cap = self.pocket_info(idx)
        key16 = self.key32() & 0xFFFF
        raw = self.b.read(ptr, cap * 4)
        out = []
        for i in range(cap):
            item, q = struct.unpack_from('<HH', raw, 4 * i)
            if item:
                out.append((item, q ^ key16))
        return out

    def write_pocket(self, idx, entries):
        ptr, cap = self.pocket_info(idx)
        if len(entries) > cap:
            raise BridgeError('ngăn túi đầy (%d/%d ô)' % (len(entries), cap))
        key16 = self.key32() & 0xFFFF
        raw = bytearray()
        for i in range(cap):
            item, q = entries[i] if i < len(entries) else (0, 0)
            raw += struct.pack('<HH', item, (q ^ key16) & 0xFFFF)
        self.b.write(ptr, bytes(raw))

    def pocket_max_qty(self, idx):
        if idx == self.p.key_pocket:
            return 1
        return self.p.qty_max.get(idx, 999)

    def set_item(self, item, qty):
        """Đặt số lượng vật phẩm (0 = xoá). Trả về chuỗi mô tả."""
        pocket = self.rom.item_pocket(item)
        if not 1 <= pocket <= self.p.n_pockets:
            raise BridgeError('vật phẩm %d không có ngăn túi' % item)
        idx = pocket - 1
        entries = self.read_pocket(idx)
        qty = max(0, min(self.pocket_max_qty(idx), int(qty)))
        pos = next((k for k, (i, _) in enumerate(entries) if i == item), None)
        if pos is None:
            if qty:
                entries.append((item, qty))
        elif qty:
            entries[pos] = (item, qty)
        else:
            del entries[pos]
        self.write_pocket(idx, entries)
        return '%s ×%d (ngăn %s)' % (self.rom.item_name(item), qty, self.p.pocket_names[idx])
