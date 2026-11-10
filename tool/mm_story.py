"""Nhiệm vụ / sự kiện map của AowVN (FireRed + CFRU), đọc thẳng từ ROM, chỉ đọc.

Map: bảng nhóm `map_groups` (nhóm 0 của hack nằm riêng, các nhóm 1..42 đúng cỡ FireRed).
Sự kiện mỗi map: NPC 24 byte, lối chuyển map 8 byte, ô kích hoạt 16 byte, biển/vật phẩm ẩn 12 byte.
Script: giải mã theo bảng lệnh FireRed; gặp lệnh lạ thì dừng nhánh và ghi lại, không đoán.
"""
import struct
from mm_core import ROM_BASE
from mm_items import VI_CHARS

# ---------------------------------------------------------------- bảng lệnh script FireRed
# số byte tham số; None = lệnh kết thúc nhánh; mã đặc biệt xử lý riêng (0x5C trainerbattle)
ARGS = {
    0x00: 0, 0x01: 0, 0x02: None, 0x03: None, 0x04: 4, 0x05: 4, 0x06: 5, 0x07: 5, 0x08: 1, 0x09: 1, 0x0A: 2, 0x0B: 2,
    0x0C: None, 0x0D: None, 0x0E: 1, 0x0F: 5, 0x10: 2, 0x11: 5, 0x12: 5, 0x13: 5, 0x14: 2, 0x15: 8, 0x16: 4,
    0x17: 4, 0x18: 4, 0x19: 4, 0x1A: 4, 0x1B: 2, 0x1C: 2, 0x1D: 5, 0x1E: 5, 0x1F: 5, 0x20: 8, 0x21: 4, 0x22: 4,
    0x23: 4, 0x24: 4, 0x25: 2, 0x26: 4, 0x27: 0, 0x28: 2, 0x29: 2, 0x2A: 2, 0x2B: 2, 0x2C: 4, 0x2D: 0, 0x2E: 0,
    0x2F: 2, 0x30: 0, 0x31: 2, 0x32: 0, 0x33: 3, 0x34: 2, 0x35: 0, 0x36: 2, 0x37: 1, 0x38: 1, 0x39: 7, 0x3A: 7,
    0x3B: 7, 0x3C: 2, 0x3D: 7, 0x3E: 7, 0x3F: 7, 0x40: 7, 0x41: 7, 0x42: 4, 0x43: 0, 0x44: 4, 0x45: 4, 0x46: 4,
    0x47: 4, 0x48: 2, 0x49: 4, 0x4A: 4, 0x4B: 2, 0x4C: 2, 0x4D: 2, 0x4E: 2, 0x4F: 6, 0x50: 8, 0x51: 2, 0x52: 4,
    0x53: 2, 0x54: 4, 0x55: 2, 0x56: 4, 0x57: 6, 0x58: 4, 0x59: 4, 0x5A: 0, 0x5B: 3, 0x5D: 0, 0x5E: 0, 0x5F: 0,
    0x60: 2, 0x61: 2, 0x62: 2, 0x63: 6, 0x64: 2, 0x65: 3, 0x66: 0, 0x67: 4, 0x68: 0, 0x69: 0, 0x6A: 0, 0x6B: 0,
    0x6C: 0, 0x6D: 0, 0x6E: 2, 0x6F: 4, 0x70: 5, 0x71: 5, 0x72: 4, 0x73: 4, 0x74: 4, 0x75: 4, 0x76: 0, 0x77: 1,
    0x78: 4, 0x79: 14, 0x7A: 2, 0x7B: 4, 0x7C: 2, 0x7D: 3, 0x7E: 1, 0x7F: 3, 0x80: 3, 0x81: 3, 0x82: 3, 0x83: 3,
    0x84: 3, 0x85: 5, 0x86: 4, 0x87: 4, 0x88: 4, 0x89: 2, 0x8A: 3, 0x8B: 0, 0x8C: 0, 0x8D: 0, 0x8E: 0, 0x8F: 2,
    0x90: 5, 0x91: 5, 0x92: 5, 0x93: 3, 0x94: 2, 0x95: 3, 0x96: 2, 0x97: 1, 0x98: 2, 0x99: 2, 0x9A: 1, 0x9B: 4,
    0x9C: 2, 0x9D: 3, 0x9E: 2, 0x9F: 2, 0xA0: 0, 0xA1: 4, 0xA2: 8, 0xA3: 0, 0xA4: 2, 0xA5: 0, 0xA6: 1, 0xA7: 2,
    0xA8: 5, 0xA9: 4, 0xAA: 9, 0xAB: 2, 0xAC: 4, 0xAD: 4, 0xAE: 0, 0xAF: 4, 0xB0: 4, 0xB1: 8, 0xB2: 0, 0xB3: 2,
    0xB4: 2, 0xB5: 2, 0xB6: 5, 0xB7: 0, 0xB8: 4, 0xB9: None, 0xBA: 4, 0xBB: 5, 0xBC: 5, 0xBD: 4, 0xBE: 4, 0xBF: 5,
    0xC0: 2, 0xC1: 2, 0xC2: 2, 0xC3: 1, 0xC4: 7, 0xC5: 0, 0xC6: 3, 0xC7: 1, 0xC8: 4, 0xC9: 0, 0xCA: 0, 0xCB: 0,
    0xCC: 3, 0xCD: 2, 0xCE: 2, 0xCF: None, 0xD0: 2, 0xD1: 7, 0xD2: 3, 0xD3: 4, 0xD4: 5,
}
TB_EXTRA = {0: 8, 1: 12, 2: 12, 3: 4, 4: 12, 5: 8, 6: 16, 7: 12, 8: 16, 9: 8}   # trainerbattle: byte sau (trainer, local)
COND = {0: '<', 1: '==', 2: '>', 3: '<=', 4: '>=', 5: '!='}
HM_MOVES = {15: 'Cut', 19: 'Fly', 57: 'Surf', 70: 'Strength', 148: 'Flash', 249: 'Rock Smash', 127: 'Waterfall', 291: 'Dive'}
DIRS = {1: 'Nam', 2: 'Bắc', 3: 'Tây', 4: 'Đông', 5: 'lặn xuống', 6: 'nổi lên'}
FLAG_TRAINER, FLAG_HIDDEN = 0x500, 0x1F4          # Emerald: cờ trainer = 0x500 + id, vật phẩm ẩn = 0x1F4 + số
PRI_METAS, PRI_PALS = 512, 6                      # Emerald: tileset chính 512 ô/512 khối, 6 bảng màu (FR: 640/7)
VAR_RESULT = 0x800D
# mã điều khiển chữ: 0xFC + mã con -> số byte tham số; 0xFD + số -> chuỗi đệm
FC_ARGS = {0x01: 1, 0x02: 1, 0x03: 1, 0x04: 3, 0x05: 1, 0x06: 1, 0x07: 0, 0x08: 1, 0x09: 0, 0x0A: 0, 0x0B: 2, 0x0C: 1,
           0x0D: 1, 0x0E: 1, 0x0F: 0, 0x10: 2, 0x11: 2, 0x12: 1, 0x13: 1, 0x14: 1}
FD_NAMES = {0x01: '[Tên bạn]', 0x02: '[…]', 0x03: '[…]', 0x04: '[…]', 0x06: '[Đối thủ]'}


def is_rom(a):
    return 0x08000000 <= a < 0x0A000000


class Story:
    def __init__(self, rom):
        self.rom, self.d, self.p = rom, rom.d, rom.profile
        self._maps, self._scripts = None, {}

    # ------------------------------------------------------------ đọc thô
    def o(self, a):
        return a - ROM_BASE

    def u8(self, a):
        return self.d[self.o(a)]

    def u16(self, a):
        return struct.unpack_from('<H', self.d, self.o(a))[0]

    def s16(self, a):
        return struct.unpack_from('<h', self.d, self.o(a))[0]

    def u32(self, a):
        return struct.unpack_from('<I', self.d, self.o(a))[0]

    def text(self, a, limit=600):
        """Lời thoại tiếng Việt tại a (bỏ mã màu/dừng, thay tên đệm)."""
        if not is_rom(a):
            return ''
        d, i, out = self.d, self.o(a), []
        end = min(len(d), i + limit)
        while i < end:
            x = d[i]
            i += 1
            if x == 0xFF:
                break
            if x == 0xFC:
                c = d[i]
                i += 1 + FC_ARGS.get(c, 0)
            elif x == 0xFD:
                out.append(FD_NAMES.get(d[i], '[…]'))
                i += 1
            elif x in (0xFA, 0xFB, 0xFE):
                out.append(' ')
            else:
                out.append(VI_CHARS.get(x, ''))
        return ' '.join(''.join(out).split())

    # ------------------------------------------------------------ danh sách map
    def _header_ok(self, hp):
        if not is_rom(hp):
            return False
        layout, ev, scr, con = (self.u32(hp + 4 * k) for k in range(4))
        if not (is_rom(layout) and is_rom(ev)):
            return False
        w, h = self.u32(layout), self.u32(layout + 4)
        return 1 <= w <= 255 and 1 <= h <= 255

    def maps(self):
        """[(nhóm, số)] mọi map thật. Nhóm 1..42: cỡ = khoảng cách tới mảng nhóm kế; nhóm 0 (hack dời đi): dò tới khi hết hợp lệ."""
        if self._maps is None:
            base = self.p.map_groups
            gps = []
            while is_rom(self.u32(base + 4 * len(gps))) and len(gps) < 100:
                gps.append(self.u32(base + 4 * len(gps)))
            out = []
            for g, gp in enumerate(gps):
                nxt = [x for x in gps + [base] if x > gp]
                cap = (min(nxt) - gp) // 4 if nxt and min(nxt) - gp < 4 * 400 else 400
                for n in range(cap):
                    if not self._header_ok(self.u32(gp + 4 * n)):
                        break
                    out.append((g, n))
            self._maps = out
        return self._maps

    def header(self, g, n):
        return self.u32(self.u32(self.p.map_groups + 4 * g) + 4 * n)

    def map_info(self, g, n):
        """Toàn bộ sự kiện của map (đã giải mã script)."""
        hp = self.header(g, n)
        layout, ev, mscr, con = (self.u32(hp + 4 * k) for k in range(4))
        info = dict(g=g, n=n, name=self.rom.map_name(g, n), header=hp, dark=bool(self.u8(hp + 21)),
                    w=self.u32(layout), h=self.u32(layout + 4), npcs=[], warps=[], triggers=[], signs=[],
                    hidden=[], connections=[], map_scripts=[])
        no, nw, nc, nb = (self.u8(ev + k) for k in range(4))
        po, pw, pc, pb = (self.u32(ev + 4 + 4 * k) for k in range(4))
        for i in range(no if is_rom(po) else 0):
            a = po + 24 * i
            sp = self.u32(a + 16)
            info['npcs'].append(dict(id=self.u8(a), gfx=self.u8(a + 1), x=self.s16(a + 4), y=self.s16(a + 6),
                                     trainer=self.u8(a + 12), sight=self.u8(a + 14), script=sp,
                                     flag=self.u16(a + 20), facts=self.script(sp) if is_rom(sp) else None))
        for i in range(nw if is_rom(pw) else 0):
            a = pw + 8 * i
            info['warps'].append(dict(x=self.s16(a), y=self.s16(a + 2), to=(self.u8(a + 7), self.u8(a + 6)), warp=self.u8(a + 5)))
        for i in range(nc if is_rom(pc) else 0):
            a = pc + 16 * i
            sp = self.u32(a + 12)
            info['triggers'].append(dict(x=self.s16(a), y=self.s16(a + 2), var=self.u16(a + 6), val=self.u16(a + 8),
                                         script=sp, facts=self.script(sp) if is_rom(sp) else None))
        for i in range(nb if is_rom(pb) else 0):
            a = pb + 12 * i
            x, y, kind, arg = self.s16(a), self.s16(a + 2), self.u8(a + 5), self.u32(a + 8)
            if kind == 7:
                info['hidden'].append(dict(x=x, y=y, item=arg & 0xFFFF, flag=FLAG_HIDDEN + (arg >> 16 & 0xFF),
                                           qty=max(1, arg >> 24 & 0x7F)))
            elif kind <= 4 and is_rom(arg):
                info['signs'].append(dict(x=x, y=y, script=arg, facts=self.script(arg)))
        if is_rom(con) and 0 < self.u32(con) < 16 and is_rom(self.u32(con + 4)):
            for i in range(self.u32(con)):
                a = self.u32(con + 4) + 12 * i
                info['connections'].append(dict(dir=DIRS.get(self.u8(a), '?'), to=(self.u8(a + 8), self.u8(a + 9)),
                                                offset=struct.unpack_from('<i', self.d, self.o(a + 4))[0]))
        if is_rom(mscr):
            a = mscr
            while self.u8(a) and a < mscr + 80:
                t, ptr = self.u8(a), self.u32(a + 1)
                a += 5
                if not is_rom(ptr):
                    break
                if t in (2, 4):                            # bảng {biến, giá trị, script}: chạy khi biến == giá trị
                    b = ptr
                    while self.u16(b) and b < ptr + 8 * 32:
                        sp = self.u32(b + 4)
                        info['map_scripts'].append(dict(type=t, var=self.u16(b), val=self.u16(b + 2), script=sp,
                                                        facts=self.script(sp) if is_rom(sp) else None))
                        b += 8
                else:
                    info['map_scripts'].append(dict(type=t, var=None, val=None, script=ptr, facts=self.script(ptr)))
        return info

    # ------------------------------------------------------------ tên
    def trainer_name(self, tid):
        p = self.p
        if not getattr(p, 'trainer_table', None):
            return 'Trainer #%d' % tid
        a = p.trainer_table + 40 * tid
        cls = self.u8(a + 1)
        name = self.text(a + 4, 12)
        cname = self.text(p.trainer_class_names + 13 * cls, 13) if getattr(p, 'trainer_class_names', None) else ''
        return ('%s %s' % (cname, name)).strip() or 'Trainer #%d' % tid

    def mart_items(self, a):
        out = []
        while is_rom(a) and self.u16(a) and len(out) < 64:
            out.append(self.rom.item_name(self.u16(a)))
            a += 2
        return out

    def hm_item(self, move):
        """Vật phẩm TM/HM dạy chiêu (bảng thật: 120 TM rồi 8 HM, tên 'TMxx'/'HMxx'), None nếu không có."""
        if '_hm' not in self.__dict__:
            self._hm = {}
            tm = getattr(self.p, 'tm_moves', None)
            if tm:
                ids = {self.rom.item_name(i): i for i in range(1, 800)}
                n_tm = self.p.tm_count
                for k in range(n_tm + 8):
                    name = 'TM%02d' % (k + 1) if k < n_tm else 'HM%02d' % (k - n_tm + 1)
                    self._hm.setdefault(self.u16(tm + 2 * k), ids.get(name))
        return self._hm.get(move)

    def pretty(self, cond):
        """'cờ 0821 đã bật' -> 'có huy hiệu 2'."""
        if cond.startswith('cờ 08') and len(cond) > 7:
            f = int(cond[3:7], 16)
            if 0x820 <= f <= 0x827:
                return ('có' if 'đã' in cond else 'chưa có') + ' huy hiệu %d' % (f - 0x81F)
            if f == 0x82C:                                 # FireRed FLAG_SYS_GAME_CLEAR
                return 'sau khi vào Đại sảnh Danh vọng' if 'đã' in cond else 'trước khi phá đảo'
        return cond

    # ------------------------------------------------------------ tổng hợp cho giao diện
    SECTIONS = ('Đi tiếp', 'Chướng ngại', 'NPC: cho / đổi / bán', 'Vật phẩm nhặt được', 'Vật phẩm ẩn', 'Trainer',
                'Sự kiện tự chạy', 'Biển báo', 'Người dân')

    def rows(self, g, n):
        """Các dòng hiển thị của map: dict(sec, x, y, title, status, detail, map). status = (loại, cờ) để tô theo cờ hiện tại."""
        if ('rows', g, n) in self._scripts:
            return self._scripts[('rows', g, n)]
        info, R, out = self.map_info(g, n), self.rom, []
        item = R.item_name

        def add(sec, x, y, title, status=None, detail='', to=None, **kw):
            out.append(dict(sec=sec, x=x, y=y, title=title, status=status, detail=detail, map=(g, n), to=to, **kw))

        def badges(fs):                                    # huy hiệu bắt buộc (cờ 0x820.. "đã bật" trong điều kiện)
            return sorted({int(c[3:7], 16) - 0x81F for f in fs for c in f[-1]
                           if c.startswith('cờ 082') and 'đã bật' in c and 0x820 <= int(c[3:7], 16) <= 0x827})

        def conds(fs):
            cs = sorted({self.pretty(c) for f in fs for c in f[-1] if not c.startswith('biến 800D')})
            return ('  [khi: %s]' % '; '.join(cs)) if cs else ''

        def texts(fs):
            return '\n'.join('• %s%s' % (f[1], conds([f])) for f in fs if f[0] == 'text')

        if info['dark']:
            hm = self.hm_item(148)
            add('Chướng ngại', None, None, 'Hang tối: cần Flash%s để thấy đường' % (' (%s)' % item(hm) if hm else ''),
                detail='Header map bật cờ "tối" (+21). Huy hiệu cần để dùng Flash ngoài trận: chưa chắc.')
        seen = set()
        for c in info['connections']:
            seen.add(c['to'])
            add('Đi tiếp', None, None, '%s → %s' % ('Dive (%s)' % c['dir'] if c['dir'] in ('lặn xuống', 'nổi lên')
                                                     else 'Ra khỏi map', R.map_name(*c['to'])),   # Duy 11/11: không nói hướng
                detail='Nối trực tiếp (đi bộ qua mép map).', to=c['to'])
        for w in info['warps']:
            if w['to'] in seen or w['to'][0] >= 200:
                continue
            seen.add(w['to'])
            try:
                dark = self.u8(self.header(*w['to']) + 21)
            except Exception:
                dark = 0
            add('Đi tiếp', w['x'], w['y'], 'Cửa → %s%s' % (R.map_name(*w['to']), ' (tối: cần Flash)' if dark else ''),
                detail='', to=w['to'], dark=bool(dark))
        for e in info['npcs']:
            fs = e['facts'] or []
            if not fs:
                continue
            f_obj = ('obj', e['flag']) if e['flag'] >= 0x20 else None    # cờ < 0x20 là cờ tạm, đổi map là mất
            kinds = {f[0] for f in fs}
            tr = [f for f in fs if f[0] == 'trainer' and f[2] != 5]
            give = [f for f in fs if f[0] in ('give_item', 'give_mon', 'give_egg', 'take_item', 'mart', 'give_money',
                                              'take_money', 'give_coins', 'take_coins')]
            need = [f for f in fs if f[0] == 'need_item']
            hm = [f for f in need if item(f[1]).startswith('HM')] + [f for f in fs if f[0] == 'need_move']
            wild = [f for f in fs if f[0] == 'wild' and f[1] not in (0, 0xFFFF)]
            detail = texts(fs)
            if tr:
                t = tr[0]
                add('Trainer', e['x'], e['y'], '%s (#%d)' % (self.trainer_name(t[1]), t[1]), ('trainer', t[1]),
                    '• %s\n%s' % (t[3], detail) if t[3] else detail)
            if any(f[0] == 'find_item' for f in fs):
                f = next(f for f in fs if f[0] == 'find_item')
                add('Vật phẩm nhặt được', e['x'], e['y'], '%s ×%d' % (item(f[1]), f[2]), f_obj, 'Bóng vật phẩm trên đất.')
            if hm and not tr:
                self.hm_item(0)
                mv_of = {v: k for k, v in self._hm.items() if v}
                names = ', '.join('%s (%s)' % (item(f[1]), R.move_name(mv_of[f[1]])) if f[0] == 'need_item' and f[1] in mv_of
                                  else item(f[1]) if f[0] == 'need_item' else 'chiêu %s' % R.move_name(f[1]) for f in hm)
                moves = [mv_of.get(f[1]) if f[0] == 'need_item' else f[1] for f in hm]
                add('Chướng ngại', e['x'], e['y'], 'Cần %s%s' % (names, conds(hm)), f_obj, detail,
                    need=[f[1] for f in hm if f[0] == 'need_item'], badges=badges(hm), move=next((m for m in moves if m), None))
            if wild:
                w = wild[0]
                req = [item(f[1]) for f in need if not item(f[1]).startswith('HM')]
                add('Chướng ngại', e['x'], e['y'], 'Pokémon chặn đường / đặc biệt: %s Lv%d%s' % (
                    R.species_name(w[1]), w[2], ('  · cần %s' % ', '.join(req)) if req else ''), f_obj, detail,
                    need=[f[1] for f in need if not item(f[1]).startswith('HM')], badges=badges(need), mon=(w[1], w[2]))
            if give or (need and not hm and not wild):
                parts = []
                for lab, ks in (('Cho', ('give_item', 'give_mon', 'give_egg', 'give_money', 'give_coins')),
                                ('Cần', ('need_item', 'need_money', 'need_coins')), ('Lấy đi', ('take_item', 'take_money', 'take_coins')),
                                ('Bán', ('mart',))):
                    xs = []
                    for f in fs:
                        if f[0] not in ks:
                            continue
                        if f[0] in ('give_item', 'need_item', 'take_item'):
                            xs.append('%s ×%d' % (item(f[1]), f[2]))
                        elif f[0] in ('give_mon', 'give_egg'):
                            xs.append('%s%s' % (R.species_name(f[1]), ' Lv%d' % f[2] if f[0] == 'give_mon' else ' (trứng)'))
                        elif f[0] == 'mart':
                            xs.append(', '.join(self.mart_items(f[1])))
                        elif 'money' in f[0]:
                            xs.append('%dĐ' % f[1])
                        else:
                            xs.append('%d xu' % f[1])
                    xs = list(dict.fromkeys(xs))
                    if xs:
                        parts.append('%s: %s' % (lab, '; '.join(xs)))
                sets = {f[1] for f in fs if f[0] == 'set_flag'}
                gate = sorted({int(c[3:7], 16) for f in give for c in f[-1] if c.startswith('cờ ') and 'chưa bật' in c} & sets)
                add('NPC: cho / đổi / bán', e['x'], e['y'], ' · '.join(parts) + conds(give + need),
                    ('done', gate[0]) if gate else None, detail, parts=parts, badges=badges(give + need),
                    gives=any(f[0] in ('give_item', 'give_mon', 'give_egg') for f in fs), shop=any(f[0] == 'mart' for f in fs),
                    buy=any(f[0] in ('take_money', 'take_coins') for f in fs),
                    say=next((f[1] for f in fs if f[0] == 'text'), ''))
            if not (tr or give or need or wild or 'find_item' in kinds or hm):
                tx = [f[1] for f in fs if f[0] == 'text']
                if tx:
                    add('Người dân', e['x'], e['y'], tx[0][:120], f_obj, detail)
        for h in info['hidden']:
            add('Vật phẩm ẩn', h['x'], h['y'], '%s ×%d' % (item(h['item']), h['qty']), ('obj', h['flag']),
                'Đứng sát ô (x, y) rồi bấm A (hoặc dùng Itemfinder).')

        def summary(fs):
            xs = []
            for f in fs:
                if f[0] == 'trainer' and f[2] != 5:
                    xs.append('đấu %s' % self.trainer_name(f[1]))
                elif f[0] in ('give_item', 'find_item'):
                    xs.append('nhận %s' % item(f[1]))
                elif f[0] == 'give_mon':
                    xs.append('nhận %s' % R.species_name(f[1]))
                elif f[0] == 'wild' and f[1] not in (0, 0xFFFF):
                    xs.append('gặp %s Lv%d' % (R.species_name(f[1]), f[2]))
                elif f[0] == 'warp':
                    xs.append('chuyển tới %s' % R.map_name(*f[1]))
                elif f[0] == 'need_item':
                    xs.append('cần %s' % item(f[1]))
            return list(dict.fromkeys(xs))

        for t in info['triggers']:
            fs = t['facts'] or []
            xs = summary(fs)
            tx = [f[1] for f in fs if f[0] == 'text']
            if xs or tx:
                add('Sự kiện tự chạy', t['x'], t['y'], 'Bước vào ô (khi biến %04X = %d): %s' % (
                    t['var'], t['val'], ', '.join(xs) if xs else tx[0][:100]), None, texts(fs))
        for m in info['map_scripts']:
            fs = m['facts'] or []
            xs = summary(fs)
            if xs:
                add('Sự kiện tự chạy', None, None, 'Khi vào map%s: %s' % (
                    ' (biến %04X = %d)' % (m['var'], m['val']) if m['var'] else '', ', '.join(xs)), None, texts(fs))
        for sg in info['signs']:
            tx = [f[1] for f in sg['facts'] if f[0] == 'text']
            if tx:
                add('Biển báo', sg['x'], sg['y'], tx[0][:120], None, texts(sg['facts']))
        self._scripts[('rows', g, n)] = out
        return out

    # ------------------------------------------------------------ trạng thái + hướng dẫn dễ hiểu
    @staticmethod
    def status(row, flag):
        """(chữ, đã xong?) theo cờ hiện tại; None nếu không theo dõi được."""
        st = row['status']
        if not st or flag is None:
            return None
        kind, v = st
        on = flag(FLAG_TRAINER + v if kind == 'trainer' else v)
        if on is None:
            return None
        sec = row['sec']
        if kind == 'trainer':
            return ('Đã thắng' if on else 'Chưa đấu'), bool(on)
        if kind == 'done':
            return ('Đã nhận' if on else 'Chưa nhận'), bool(on)
        if sec in ('Vật phẩm nhặt được', 'Vật phẩm ẩn'):
            return ('Đã nhặt' if on else 'Chưa nhặt'), bool(on)
        if sec == 'Chướng ngại':
            return ('Đã mở' if on else 'Còn chặn'), bool(on)
        return ('Đã rời đi' if on else 'Còn ở đó'), bool(on)

    OBSTACLE = {15: 'cây nhỏ chặn đường', 249: 'tảng đá nứt chặn đường', 70: 'tảng đá lớn chặn đường', 57: 'mặt nước',
                127: 'thác nước', 392: 'vách đá cần leo', 291: 'chỗ nước sâu'}

    def guide(self, g, n, flag, have):
        """Hướng dẫn cho người mới: [(tiêu đề, [mục])], mục = dict(text, rows, done). have = tập id vật phẩm đang có."""
        R, item = self.rom, self.rom.item_name
        info, rows = self.map_info(g, n), self.rows(g, n)
        st = {id(r): self.status(r, flag) for r in rows}
        done = lambda r: bool(st[id(r)] and st[id(r)][1])
        tracked = lambda r: st[id(r)] is not None
        pos = lambda r: 'ô %d,%d' % (r['x'], r['y']) if r['x'] is not None else ''

        def need_text(items, bad):
            xs = ['%s %s' % (item(i), '✔ đã có' if i in have else '✘ chưa có') for i in items]
            for k in bad:
                on = flag(0x81F + k) if flag else None
                xs.append('huy hiệu %d %s' % (k, '✔' if on else '✘ chưa có' if on is not None else ''))
            return ', '.join(xs)
        flash = self.hm_item(148)
        nxt, todo, ways, ok = [], [], [], []
        if info['dark']:
            nxt.append(dict(text='Map này là HANG TỐI: dạy chiêu Flash (%s) cho 1 con trong đội, rồi dùng Flash ngoài bản đồ để thấy đường.'
                                 % need_text([flash] if flash else [], []), rows=[], done=None))
        for r in rows:
            if r['sec'] == 'Đi tiếp' and r.get('dark'):
                nxt.append(dict(text='Lối vào %s (%s) là HANG TỐI: cần Flash — %s.' % (R.map_name(*r['to']), pos(r),
                                                                                      need_text([flash] if flash else [], [])),
                                rows=[r], done=None))
        obs = {}
        for r in rows:
            if r['sec'] == 'Chướng ngại' and r['x'] is not None and not done(r):
                obs.setdefault(r['title'], []).append(r)
        for title, rs in obs.items():
            r0 = rs[0]
            if r0.get('mon'):
                sp, lv = r0['mon']
                t = '%s Lv%d ở %s' % (R.species_name(sp), lv, pos(r0))
                if r0.get('need'):
                    t += ': cần %s' % need_text(r0['need'], r0.get('badges', []))
                nxt.append(dict(text=t + '.', rows=rs, done=False if tracked(r0) else None))
            else:
                what = self.OBSTACLE.get(r0.get('move'), 'chướng ngại')
                t = '%s%s ở %s: cần %s.' % ('%d ' % len(rs) if len(rs) > 1 else '', what,
                                           '; '.join(pos(r) for r in rs), need_text(r0.get('need', []), r0.get('badges', [])))
                nxt.append(dict(text=t[0].upper() + t[1:], rows=rs, done=None))
        clean = lambda ps: ' · '.join(p.split('  [khi:')[0] for p in ps)
        for r in rows:
            if r['sec'] == 'NPC: cho / đổi / bán' and r.get('gives') and not r.get('buy') and not done(r):
                t = 'Nói chuyện với người ở %s — %s' % (pos(r), clean(r.get('parts', [])))
                if r.get('badges'):
                    t += ' (cần %s)' % need_text([], r['badges'])
                nxt.append(dict(text=t + '.', rows=[r], done=False if tracked(r) else None))
        for sec, verb in (('Vật phẩm ẩn', 'Đồ giấu (đứng sát ô rồi bấm A)'), ('Vật phẩm nhặt được', 'Bóng vật phẩm'),
                          ('Trainer', 'Trainer chưa đấu')):
            for r in rows:
                if r['sec'] == sec and not done(r):
                    name = r['title'].split(' (#')[0]
                    todo.append(dict(text='%s: %s — %s' % (verb, name, pos(r)), rows=[r], done=False if tracked(r) else None))
        for r in rows:
            if r['sec'] == 'NPC: cho / đổi / bán' and (r.get('buy') or not r.get('gives')):
                say = r.get('say', '')
                say = ' “%s”' % (say[:90] + ('…' if len(say) > 90 else '')) if say else ''
                kind = 'Mua bán' if r.get('buy') or r.get('shop') else 'Người/vật'
                todo.append(dict(text='%s ở %s:%s — %s' % (kind, pos(r), say, clean(r.get('parts', []))), rows=[r], done=None))
            if r['sec'] == 'Sự kiện tự chạy' and r['x'] is not None:
                t = r['title'].split(': ', 1)[-1]
                todo.append(dict(text='Sự kiện khi bước vào %s: %s (có thể đã xảy ra rồi)' % (pos(r), t), rows=[r], done=None))
        for r in rows:
            if r['sec'] == 'Đi tiếp' and not r.get('dark'):
                t = r['title'].replace('Cửa → ', 'Cửa (%s) → ' % pos(r) if r['x'] is not None else 'Cửa → ')
                ways.append(dict(text=t, rows=[r] if r['x'] is not None else [], done=None, to=r['to']))
        groups = {}
        for r in rows:
            if done(r):
                label = {'Trainer': 'Đã thắng', 'Chướng ngại': 'Đã mở', 'NPC: cho / đổi / bán': 'Đã nhận từ NPC',
                         'Người dân': None, 'Vật phẩm ẩn': 'Đã nhặt', 'Vật phẩm nhặt được': 'Đã nhặt'}.get(r['sec'])
                if label:
                    groups.setdefault(label, []).append(r)
        for label, rs in groups.items():
            ok.append(dict(text='%s: %s' % (label, ', '.join(r['title'].split(' (#')[0].split('  [')[0] for r in rs)), rows=rs, done=True))
        out = [('➜ VIỆC NÊN LÀM TIẾP', nxt or [dict(text='Không thấy chướng ngại hay nhiệm vụ nào trên map này.', rows=[], done=None)]),
               ('⬜ CÒN TRÊN MAP NÀY', todo), ('🚪 LỐI ĐI', ways), ('✅ ĐÃ XONG', ok)]
        return [(t, es) for t, es in out if es]

    # ------------------------------------------------------------ hình nhân vật (overworld)
    def ow_sprite(self, gfx, facing=1):
        """Ảnh RGBA đứng yên theo hướng (khung 0 xuống, 1 lên, 2 trái; phải = lật trái); None nếu không đọc được."""
        from PIL import Image, ImageOps
        key = ('ow', gfx, facing)
        if key in self._scripts:
            return self._scripts[key]
        im = None
        try:
            p = self.p
            gi = self.u32(p.ow_gfx + 4 * gfx)
            tt, pt, rt, size, w, h = struct.unpack_from('<HHHHhh', self.d, self.o(gi))
            if tt == 0xFFFF and 0 < w <= 128 and 0 < h <= 128 and not w % 8 and not h % 8:   # Emerald có xe/tàu 48x48, 96x40, 88x32
                pal = None
                for k in range(512):
                    ptr, tag = self.u32(p.ow_pals + 8 * k), self.u16(p.ow_pals + 8 * k + 4)
                    if tag == pt:
                        pal = [((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)
                               for c in struct.unpack_from('<16H', self.d, self.o(ptr))]
                        break
                    if not is_rom(ptr) or tag == 0x11FF:
                        break
                imgs = self.u32(gi + 0x1C)
                frames = 1 if not is_rom(self.u32(imgs + 8 * 2)) else 3
                f = {1: 0, 2: 1, 3: 2, 4: 2}.get(facing, 0) if frames == 3 else 0
                data = self.o(self.u32(imgs + 8 * f))
                if pal and 0 <= data < len(self.d):
                    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                    px, tw = im.load(), w // 8
                    for t in range(w * h // 64):
                        tx, ty = t % tw, t // tw
                        for yy in range(8):
                            for xx in range(8):
                                b = self.d[data + 32 * t + yy * 4 + xx // 2]
                                c = b & 15 if xx % 2 == 0 else b >> 4
                                if c:
                                    px[tx * 8 + xx, ty * 8 + yy] = pal[c] + (255,)
                    if facing == 4 and frames == 3:
                        im = ImageOps.mirror(im)
        except Exception:
            im = None
        self._scripts[key] = im
        return im

    # ------------------------------------------------------------ vẽ bản đồ từ ROM
    def _tileset(self, ts):
        key = ('ts', ts)
        if key not in self._scripts:
            comp = self.u8(ts)
            tp = self.u32(ts + 4)
            tiles = self.rom.lz77(tp) if comp else None
            self._scripts[key] = dict(tiles=tiles, tptr=tp, pals=self.u32(ts + 8), metas=self.u32(ts + 12), cache={})
        return self._scripts[key]

    def map_image(self, g, n):
        """Ảnh PIL của map (16 px mỗi ô) vẽ từ layout + 2 tileset (Emerald: 512 ô/512 khối/6 bảng màu ở tileset chính)."""
        from PIL import Image
        key = ('img', g, n)
        if key in self._scripts:
            return self._scripts[key]
        d = self.d
        lay = self.u32(self.header(g, n))
        w, h, _, blocks, pri, sec = struct.unpack_from('<iiIIII', d, self.o(lay))
        P, Q = self._tileset(pri), self._tileset(sec)

        def pal(addr, i):
            return [((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)
                    for c in struct.unpack_from('<16H', d, self.o(addr) + 32 * i)]
        pals = [pal(P['pals'], i) for i in range(PRI_PALS)] + [pal(Q['pals'], i) for i in range(PRI_PALS, 16)]

        def tile(t):
            ts, k = (P, t) if t < PRI_METAS else (Q, t - PRI_METAS)
            if ts['tiles'] is not None:
                return ts['tiles'][32 * k:32 * k + 32]
            o = self.o(ts['tptr']) + 32 * k
            return d[o:o + 32]
        metas = {}

        def meta(mid):
            if mid not in metas:
                ts, k = (P, mid) if mid < PRI_METAS else (Q, mid - PRI_METAS)
                ent = struct.unpack_from('<8H', d, self.o(ts['metas']) + 16 * k)
                img = Image.new('RGB', (16, 16))
                px = img.load()
                for layer in (0, 1):
                    for q in range(4):
                        v = ent[layer * 4 + q]
                        tb, hf, vf, pi = tile(v & 0x3FF), v >> 10 & 1, v >> 11 & 1, v >> 12
                        ox, oy = (q & 1) * 8, (q >> 1) * 8
                        for yy in range(8):
                            for xx in range(8):
                                b = tb[yy * 4 + xx // 2] if len(tb) == 32 else 0
                                c = b & 15 if xx % 2 == 0 else b >> 4
                                if layer and not c:
                                    continue
                                px[ox + (7 - xx if hf else xx), oy + (7 - yy if vf else yy)] = pals[pi][c]
                metas[mid] = img
            return metas[mid]
        im = Image.new('RGB', (w * 16, h * 16))
        raw = struct.unpack_from('<%dH' % (w * h), d, self.o(blocks))
        for y in range(h):
            for x in range(w):
                im.paste(meta(raw[y * w + x] & 0x3FF), (x * 16, y * 16))
        self._scripts[key] = im
        return im

    # Emerald: thuộc tính khối u16 ở tileset +0x10, hành vi = 8 bit thấp. Hành vi có lượt gặp theo pokeemerald
    # (cỏ cao/cỏ dài/cát sâu/hang/trong nhà/đỉnh núi/cỏ tro; nước ao/sâu/biển). CHƯA kiểm trong game (10/11).
    MB_LAND = {0x02, 0x03, 0x06, 0x08, 0x0B, 0x0C, 0x24}
    MB_WATER = {0x10, 0x11, 0x12, 0x14, 0x15}

    def encounter_tiles(self, g, n):
        """{(x, y): 'land'|'water'} ô có thể gặp Pokémon hoang dã theo hành vi khối (xem MB_LAND / MB_WATER),
        chỉ tính kiểu mà map có bảng Pokémon (nước: Surf hoặc câu)."""
        key = ('enc', g, n)
        if key not in self._scripts:
            wild = self.rom.wild_for_map(g, n) or {}
            lay = self.u32(self.header(g, n))
            w, h, _, blocks, pri, sec = struct.unpack_from('<iiIIII', self.d, self.o(lay))
            raw = struct.unpack_from('<%dH' % (w * h), self.d, self.o(blocks))
            attr = {}
            out = {}
            for i, v in enumerate(raw):
                mid = v & 0x3FF
                if mid not in attr:
                    ts, k = (pri, mid) if mid < PRI_METAS else (sec, mid - PRI_METAS)
                    mb = self.u16(self.u32(ts + 0x10) + 2 * k) & 0xFF
                    attr[mid] = 'land' if mb in self.MB_LAND else 'water' if mb in self.MB_WATER else None
                if attr[mid] in wild or attr[mid] == 'water' and 'fish' in wild:   # câu cá = nhìn ra ô nước
                    out[i % w, i // w] = attr[mid]
            self._scripts[key] = out
        return self._scripts[key]

    def flag_setters(self, flag):
        """[(map, kiểu 'npc'/'trigger'/'sign'/'map', x, y)] mọi chỗ script bật cờ `flag` (Duy 11/11: NPC chắn đường chỉ đi
        khi cờ ẩn của nó bật — vd hàng lính Aqua trước bảo tàng Slateport đi khi nói chuyện với Dock ở xưởng tàu).
        Quét mọi map một lần rồi giữ lại."""
        idx = self._scripts.get('setters')
        if idx is None:
            idx = {}
            for g, n in self.maps():
                try:
                    info = self.map_info(g, n)
                except Exception:
                    continue
                for kind, key in (('npc', 'npcs'), ('trigger', 'triggers'), ('sign', 'signs'), ('map', 'map_scripts')):
                    for e in info[key]:
                        for f in e.get('facts') or []:
                            if f[0] == 'set_flag':
                                idx.setdefault(f[1], []).append(((g, n), kind, e.get('x'), e.get('y')))
            self._scripts['setters'] = idx
        return idx.get(flag, [])

    def item_gates(self, g, n):
        """[(x, y, vật phẩm)] ô kích hoạt chỉ cho đi qua khi có vật phẩm (vd bão cát Route 111 cần Go-Goggles)."""
        key = ('gates', g, n)
        if key not in self._scripts:
            self._scripts[key] = [(t['x'], t['y'], f[1]) for t in self.map_info(g, n)['triggers']
                                  for f in (t['facts'] or []) if f[0] == 'need_item']
        return self._scripts[key]

    def reach(self, g, n, starts, blocked=()):
        """Tập ô đi bộ tới được từ các ô starts (cùng luật va chạm + độ cao như walk_path), không đi vào ô blocked.
        Duy 11/11: Route 112 phía dưới không lên thẳng mép sang Route 113 được, phải qua Fiery Path."""
        from collections import deque
        lay = self.u32(self.header(g, n))
        w, h, _, blocks = struct.unpack_from('<iiII', self.d, self.o(lay))
        raw = struct.unpack_from('<%dH' % (w * h), self.d, self.o(blocks))
        if isinstance(starts, tuple) and len(starts) == 2 and isinstance(starts[0], int):
            starts = [starts]
        seen = {p for p in starts if 0 <= p[0] < w and 0 <= p[1] < h}
        q = deque(seen)
        while q:
            p = q.popleft()
            ep = raw[p[1] * w + p[0]] >> 12
            for nx, ny in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and (nx, ny) not in blocked:
                    v = raw[ny * w + nx]
                    e = v >> 12
                    if not v >> 10 & 3 and (e == ep or e in (0, 15) or ep in (0, 15)):
                        seen.add((nx, ny))
                        q.append((nx, ny))
        return seen

    def walk_path(self, g, n, start, goals, blocked=()):
        """[(x, y)...] đường ngắn nhất từ start tới một ô trong goals trên lưới va chạm của map (Duy 11/11: vẽ đường tới
        nhiệm vụ). Ô đi được = va chạm (bit 10-11) = 0; đổi độ cao (bit 12-15) chỉ qua ô độ cao 0/15 như game (đất <-> nước
        cần Surf). Ô đích luôn vào được (cửa, NPC). blocked = ô có NPC đứng (không đi qua). Không tính gờ nhảy một chiều.
        Theo độ cao không có đường -> thử bỏ độ cao; vẫn không -> None."""
        from collections import deque
        lay = self.u32(self.header(g, n))
        w, h, _, blocks = struct.unpack_from('<iiII', self.d, self.o(lay))
        raw = struct.unpack_from('<%dH' % (w * h), self.d, self.o(blocks))
        goals = {p for p in goals if 0 <= p[0] < w and 0 <= p[1] < h}
        if not goals or not (0 <= start[0] < w and 0 <= start[1] < h):
            return None
        for strict in (True, False):
            prev, q = {start: None}, deque([start])
            while q:
                p = q.popleft()
                if p in goals:
                    out = []
                    while p is not None:
                        out.append(p)
                        p = prev[p]
                    return out[::-1]
                ep = raw[p[1] * w + p[0]] >> 12
                for nx, ny in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)):
                    if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in prev:
                        continue
                    v = raw[ny * w + nx]
                    if (nx, ny) not in goals:
                        if v >> 10 & 3 or (nx, ny) in blocked:
                            continue
                        e = v >> 12
                        if strict and e != ep and e not in (0, 15) and ep not in (0, 15):
                            continue
                    prev[(nx, ny)] = p
                    q.append((nx, ny))
        return None

    def landing_tile(self, g, n, kind):
        """Ô đáp khi bay tới map để săn: ô gặp kiểu `kind` ('land' = cỏ; 'water' = ô đi được sát nước), đi được
        (va chạm = bit 10-11 của khối = 0), thuộc vùng đi được lớn nhất (khỏi kẹt trong khoảnh cỏ bị cây chắn),
        không trùng NPC/ô sự kiện/warp; ưu tiên ô giữa bãi (nhiều ô cùng kiểu xung quanh). None nếu không có."""
        d = self.d
        lay = self.u32(self.header(g, n))
        w, h, _, blocks = struct.unpack_from('<iiII', d, self.o(lay))
        raw = struct.unpack_from('<%dH' % (w * h), d, self.o(blocks))
        free = {(i % w, i // w) for i, v in enumerate(raw) if not v >> 10 & 3}
        info = self.map_info(g, n)
        busy = {(e['x'], e['y']) for k in ('npcs', 'triggers', 'warps', 'signs') for e in info[k]}
        enc = self.encounter_tiles(g, n)
        if kind == 'land':
            want = {p for p, t in enc.items() if t == 'land'} & free
        else:                                                   # đứng trên bờ, cạnh ô nước có Pokémon
            want = {(x + dx, y + dy) for (x, y), t in enc.items() if t == 'water'
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))} & free - set(enc)
        want -= busy
        seen, best = set(), set()
        for s in free:                                          # vùng liền nhau lớn nhất (4 hướng)
            if s in seen:
                continue
            comp, st = set(), [s]
            while st:
                p = st.pop()
                if p in seen or p not in free:
                    continue
                seen.add(p)
                comp.add(p)
                st += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
            if len(comp & want) > len(best & want) or (len(comp & want) == len(best & want) and len(comp) > len(best)):
                best = comp
        cand = sorted(best & want, key=lambda p: (p[1], p[0]))
        if not cand:
            return None
        return max(cand, key=lambda p: sum((p[0] + dx, p[1] + dy) in want for dx in (-1, 0, 1) for dy in (-1, 0, 1)))

    def wild_overlay(self, g, n):
        """Ảnh RGBA cùng cỡ map_image: tô mờ xanh lá ô gặp trên đất, xanh dương ô gặp dưới nước."""
        from PIL import Image, ImageDraw
        key = ('encimg', g, n)
        if key not in self._scripts:
            base = self.map_image(g, n)
            im = Image.new('RGBA', base.size, (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            col = {'land': ((255, 240, 0, 70), (255, 214, 0, 255)), 'water': ((40, 140, 255, 80), (0, 90, 255, 255))}
            T = self.encounter_tiles(g, n)
            for (x, y), t in T.items():
                fill, edge = col[t]
                X, Y = x * 16, y * 16
                dr.rectangle((X, Y, X + 15, Y + 15), fill=fill)
                for dx, dy, box in ((-1, 0, (X, Y, X + 1, Y + 15)), (1, 0, (X + 14, Y, X + 15, Y + 15)),   # viền ở mép vùng
                                    (0, -1, (X, Y, X + 15, Y + 1)), (0, 1, (X, Y + 14, X + 15, Y + 15))):
                    if T.get((x + dx, y + dy)) != t:
                        dr.rectangle(box, fill=edge)
            self._scripts[key] = im
        return self._scripts[key]

    # ------------------------------------------------------------ giải mã script
    def script(self, start):
        """Danh sách sự kiện rút ra từ script (theo mọi nhánh): (loại, dữ liệu..., điều kiện)."""
        if start in self._scripts:
            return self._scripts[start]
        facts, seen = [], set()
        stack = [(start, ())]
        steps = 0
        while stack and steps < 4000:
            a, conds = stack.pop()
            var = {}                                       # 0x8000.. đặt bằng setorcopyvar/setvar (macro giveitem)
            last = None                                    # phép kiểm vừa làm, để gán cho goto_if/call_if
            while steps < 4000:
                steps += 1
                if a in seen or not is_rom(a):
                    break
                seen.add(a)
                op = self.u8(a)
                if op == 0x5C:                             # trainerbattle
                    t = self.u8(a + 1)
                    if t not in TB_EXTRA:
                        facts.append(('unknown', a, op, conds))
                        break
                    tid = self.u16(a + 2)
                    tx = self.u32(a + 6) if t != 3 else 0
                    facts.append(('trainer', tid, t, self.text(tx, 200) if tx else '', conds))
                    if t in (1, 2, 6, 8):
                        sp = self.u32(a + 6 + TB_EXTRA[t] - 4)
                        stack.append((sp, conds + ('sau khi thắng trainer #%d' % tid,)))
                    a += 6 + TB_EXTRA[t]
                    continue
                n = ARGS.get(op, -1)
                if n == -1:
                    facts.append(('unknown', a, op, conds))
                    break
                if n is None:
                    break
                arg = a + 1
                a += 1 + n
                if op in (0x04, 0x05):                     # call / goto
                    stack.append((self.u32(arg), conds)) if op == 0x04 else None
                    if op == 0x05:
                        a = self.u32(arg)
                elif op in (0x06, 0x07):                   # goto_if / call_if
                    c, tgt = self.u8(arg), self.u32(arg + 1)
                    yes = self._cond(last, c, True)
                    no = self._cond(last, c, False)
                    stack.append((tgt, conds + ((yes,) if yes else ())))
                    if no:
                        conds = conds + (no,)
                elif op in (0x16, 0x1A):                   # setvar / setorcopyvar
                    var[self.u16(arg)] = self.u16(arg + 2)
                elif op == 0x09 or op == 0x08:             # callstd / gotostd
                    std = self.u8(arg)
                    if std in (0, 1) and 0x8000 in var:    # 0: nhận đồ (NPC cho), 1: nhặt bóng vật phẩm
                        facts.append(('give_item' if std == 0 else 'find_item', var[0x8000], var.get(0x8001, 1), conds))
                    if op == 0x08:
                        break
                elif op == 0x0F and self.u8(arg) == 0:     # loadword 0, text (msgbox)
                    tx = self.text(self.u32(arg + 1))
                    if tx:
                        facts.append(('text', tx, conds))
                elif op == 0x67:
                    tx = self.text(self.u32(arg))
                    if tx:
                        facts.append(('text', tx, conds))
                elif op == 0x2B:
                    last = ('flag', self.u16(arg))
                elif op in (0x29, 0x2A):
                    facts.append(('set_flag' if op == 0x29 else 'clear_flag', self.u16(arg), conds))
                elif op == 0x21:
                    v, val = self.u16(arg), self.u16(arg + 2)
                    if last and last[0] == 'item' and v == VAR_RESULT:
                        last = ('itemres', last[1], val)
                    else:
                        last = ('var', v, val)
                elif op == 0x47:                           # checkitem
                    last = ('item', self.u16(arg), self.u16(arg + 2))
                    facts.append(('need_item', self.u16(arg), self.u16(arg + 2), conds))
                elif op == 0x45:
                    facts.append(('take_item', self.u16(arg), self.u16(arg + 2), conds))
                elif op == 0x44:
                    facts.append(('give_item', self.u16(arg), self.u16(arg + 2), conds))
                elif op == 0x7C:                           # checkpartymove
                    facts.append(('need_move', self.u16(arg), conds))
                elif op == 0x79:
                    facts.append(('give_mon', self.u16(arg), self.u8(arg + 2), conds))
                elif op == 0x7A:
                    facts.append(('give_egg', self.u16(arg), conds))
                elif op == 0xB6:
                    facts.append(('wild', self.u16(arg), self.u8(arg + 2), conds))
                elif op == 0x86:
                    facts.append(('mart', self.u32(arg), conds))
                elif op in (0x25, 0x26):
                    facts.append(('special', self.u16(arg if op == 0x25 else arg + 2), conds))
                elif op in (0x39, 0x3A, 0x3B, 0x3D, 0xD1):
                    facts.append(('warp', (self.u8(arg), self.u8(arg + 1)), conds))
                elif op == 0x60:
                    last = ('trainer', self.u16(arg))
                elif op in (0x90, 0x91, 0x92):
                    facts.append(({0x90: 'give_money', 0x91: 'take_money', 0x92: 'need_money'}[op], self.u32(arg), conds))
                elif op in (0xB4, 0xB5, 0xB3):
                    facts.append(({0xB4: 'give_coins', 0xB5: 'take_coins', 0xB3: 'need_coins'}[op], self.u16(arg), conds))
        self._scripts[start] = facts
        return facts

    def _cond(self, last, c, taken):
        """Mô tả điều kiện của nhánh goto_if/call_if (taken = nhánh nhảy)."""
        if not last:
            return None
        sym = COND.get(c, '?')
        if last[0] in ('flag', 'trainer'):                 # kết quả so: cờ bật = 1 (==), tắt = 0 (<)
            if sym in ('==', '>='):
                on = taken
            elif sym in ('<', '!='):
                on = not taken
            else:
                return None
            if last[0] == 'flag':
                return 'cờ %04X %s' % (last[1], 'đã bật' if on else 'chưa bật')
            return 'trainer #%d %s' % (last[1], 'đã thắng' if on else 'chưa thắng')
        if last[0] == 'itemres':                           # checkitem rồi compare VAR_RESULT, v
            if sym == '==':
                have = (last[2] == 1) if taken else (last[2] != 1)
            elif sym == '!=':
                have = (last[2] != 1) if taken else (last[2] == 1)
            else:
                return None
            return '%s có %s' % ('đã' if have else 'chưa', self.rom.item_name(last[1]))
        if last[0] == 'var':
            s = sym if taken else {'==': '!=', '!=': '==', '<': '>=', '>=': '<', '>': '<=', '<=': '>'}[sym]
            return 'biến %04X %s %d' % (last[1], s, last[2])
        return None
