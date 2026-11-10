"""Danh mục vật phẩm AowVN: đọc từ ROM (bản ghi 44 byte ở item_recs), giải mã mô tả tiếng Việt, chia nhóm theo công dụng.
Bản ghi: tên +0, giá u16 +16, mã hiệu ứng khi cầm +18, tham số +19, con trỏ mô tả +20, ngăn +26.
Công dụng do mình viết theo mã hiệu ứng; số nhân "chuẩn" là luật chính thức, chưa đo trong ROM này."""
import struct
import unicodedata

from mm_core import CHARMAP, ROM_BASE, TYPE_NAMES, decode_text

ATK, TYPE, DEF, HEAL, SPEED, EVO, MEGA, TM, OTHER = (
    'Tăng tấn công', 'Tăng theo hệ', 'Phòng thủ', 'Hồi phục', 'Tốc độ/chí mạng', 'Tiến hoá', 'Mega/Z', 'TM', 'Khác')
ALL = 'Tất cả'
GROUPS = (ALL, ATK, TYPE, DEF, HEAL, SPEED, EVO, MEGA, TM, OTHER)

# Bảng chữ tiếng Việt của AowVN: đọc từ font trong ROM (0x081F3100), đối chiếu với chữ trong mô tả.
VI_CHARS = dict(CHARMAP)
VI_CHARS.update(zip(range(0x01, 0x10), 'ầấẩậềếểễằặẳẵồốổ'))
VI_CHARS.update(zip(range(0x11, 0x25), 'ừứửữđàáýạèéêẽìịỉĩòóô'))
VI_CHARS.update(zip(range(0x26, 0x2C), 'ùúủũụự'))
VI_CHARS.update(zip(range(0x50, 0x53), 'ẻảã'))
VI_CHARS.update(zip(range(0x5E, 0x69), 'ẹệờớởỡợỏõọâ'))
VI_CHARS.update({0x55: 'POK', 0x56: 'é', 0x57: 'BL', 0x58: 'OC', 0x59: 'K', 0x5A: 'ắ', 0x6F: 'í', 0x2F: 'ỳ'})
VI_CHARS.update({0xB0: '...', 0xB1: '"', 0xB2: '"', 0xB3: "'", 0xB7: 'Đ', 0xB8: ','})
VI_CHARS.update(zip(range(0xF1, 0xF7), 'ẫỗộăơư'))
VI_CHARS.update({0xFA: ' ', 0xFB: ' ', 0xFE: ' '})                 # các mã xuống dòng

STATS = {1: 'HP', 2: 'Tấn công', 3: 'Phòng thủ', 4: 'Tốc độ', 5: 'Tấn công đặc biệt', 6: 'Phòng thủ đặc biệt'}

# đồ cầm tăng một hệ cố định: mã hiệu ứng -> tên hệ
TYPE_HOLD = {31: 'Bọ', 46: 'Đất', 47: 'Đá', 48: 'Cỏ', 49: 'Bóng tối', 50: 'Giác đấu', 51: 'Điện', 52: 'Nước', 53: 'Bay',
             54: 'Độc', 55: 'Băng', 56: 'Ma', 57: 'Siêu linh', 58: 'Lửa', 59: 'Rồng', 60: 'Normal'}

# mã hiệu ứng khi cầm -> (nhóm, công dụng); {t} = hệ theo tham số, {p} = tham số
HOLD = {
    1: (HEAL, 'Tự hồi HP khi HP xuống thấp (một lần).'),
    2: (HEAL, 'Tự khỏi tê liệt (một lần).'),
    3: (HEAL, 'Tự tỉnh ngủ (một lần).'),
    4: (HEAL, 'Tự khỏi trúng độc (một lần).'),
    5: (HEAL, 'Tự khỏi bỏng (một lần).'),
    6: (HEAL, 'Tự khỏi đóng băng (một lần).'),
    7: (HEAL, 'Tự hồi PP cho chiêu đã dùng hết (một lần).'),
    8: (HEAL, 'Tự khỏi rối loạn (một lần).'),
    9: (HEAL, 'Tự khỏi mọi trạng thái xấu (một lần).'),
    10: (HEAL, 'Tự hồi HP khi HP thấp; không hợp khẩu vị thì bị rối loạn.'),
    11: (HEAL, 'Tự hồi HP khi HP thấp; không hợp khẩu vị thì bị rối loạn.'),
    12: (HEAL, 'Tự hồi HP khi HP thấp; không hợp khẩu vị thì bị rối loạn.'),
    13: (HEAL, 'Tự hồi HP khi HP thấp; không hợp khẩu vị thì bị rối loạn.'),
    14: (HEAL, 'Tự hồi HP khi HP thấp; không hợp khẩu vị thì bị rối loạn.'),
    15: (ATK, 'Tăng Tấn công khi HP xuống thấp (một lần).'),
    16: (DEF, 'Tăng Phòng thủ khi HP xuống thấp (một lần).'),
    17: (SPEED, 'Tăng Tốc độ khi HP xuống thấp (một lần).'),
    18: (ATK, 'Tăng Tấn công đặc biệt khi HP xuống thấp (một lần).'),
    19: (DEF, 'Tăng Phòng thủ đặc biệt khi HP xuống thấp (một lần).'),
    20: (SPEED, 'Tăng tỉ lệ chí mạng khi HP xuống thấp (một lần).'),
    21: (OTHER, 'Tăng mạnh một chỉ số ngẫu nhiên khi HP xuống thấp (một lần).'),
    22: (DEF, 'Giảm độ chính xác của chiêu đối thủ.'),
    23: (OTHER, 'Hồi lại chỉ số vừa bị giảm (một lần).'),
    26: (SPEED, 'Đôi lúc được ra đòn trước.'),
    27: (OTHER, 'Tăng thân thiết nhanh hơn.'),
    28: (HEAL, 'Tự khỏi mê hoặc (một lần).'),
    30: (OTHER, 'Chiêu đánh có thể làm đối thủ chùn bước; cũng dùng để tiến hoá.'),
    32: (OTHER, 'Nhân đôi tiền thưởng sau trận.'),
    33: (OTHER, 'Giảm tỉ lệ gặp Pokémon hoang dã.'),
    34: (TYPE, 'Latios/Latias: tăng sức mạnh chiêu hệ Rồng và Siêu linh.'),
    35: (ATK, 'Clamperl: tăng Tấn công đặc biệt; cũng dùng để tiến hoá.'),
    36: (DEF, 'Clamperl: tăng Phòng thủ đặc biệt; cũng dùng để tiến hoá.'),
    37: (OTHER, 'Luôn bỏ chạy được khỏi trận hoang dã.'),
    38: (EVO, 'Giữ không cho con đang cầm tiến hoá.'),
    39: (DEF, 'Có thể trụ lại 1 HP thay vì bị hạ.'),
    40: (OTHER, 'Tăng EXP nhận được (×1.5).'),
    41: (SPEED, 'Tăng tỉ lệ chí mạng.'),
    43: (HEAL, 'Hồi một ít HP mỗi lượt.'),
    44: (EVO, 'Dùng để tiến hoá Seadra.'),
    45: (ATK, 'Pikachu: nhân đôi Tấn công và Tấn công đặc biệt.'),
    61: (EVO, 'Dùng để tiến hoá Porygon.'),
    62: (HEAL, 'Hồi HP theo sát thương đã gây.'),
    63: (SPEED, 'Chansey: tăng tỉ lệ chí mạng.'),
    64: (DEF, 'Ditto: tăng Phòng thủ.'),
    65: (ATK, 'Cubone/Marowak: nhân đôi Tấn công.'),
    66: (SPEED, "Farfetch'd: tăng tỉ lệ chí mạng."),
    68: (DEF, 'Đối thủ đánh trúng bằng chiêu tiếp xúc sẽ mất HP.'),
    69: (SPEED, 'Ditto: tăng Tốc độ.'),
    70: (DEF, 'Tăng Phòng thủ đặc biệt, nhưng chỉ dùng được chiêu tấn công.'),
    71: (DEF, 'Con chưa tiến hoá hết: tăng Phòng thủ và Phòng thủ đặc biệt.'),
    72: (TYPE, 'Tăng sức mạnh chiêu hệ {t}; Arceus đổi sang hệ này.'),
    73: (MEGA, 'Đá Mega hoặc Z đặc biệt: chỉ đúng loài mới dùng được.'),
    74: (ATK, 'Tăng sát thương mọi chiêu (chuẩn ×1.3), mất một ít HP mỗi lần đánh.'),
    75: (OTHER, 'Tự làm con đang cầm bị trúng độc nặng.'),
    76: (OTHER, 'Tự làm con đang cầm bị bỏng.'),
    77: (HEAL, 'Hệ Độc: hồi HP mỗi lượt. Hệ khác: mất HP.'),
    78: (OTHER, 'Kéo dài Bão cát do con này tạo ra.'),
    79: (OTHER, 'Kéo dài Mưa do con này tạo ra.'),
    80: (OTHER, 'Kéo dài Trời nắng do con này tạo ra.'),
    81: (OTHER, 'Kéo dài Mưa đá do con này tạo ra.'),
    83: (OTHER, 'Tăng độ chính xác.'),
    84: (DEF, 'Miễn sát thương thời tiết và chiêu dạng bột.'),
    85: (ATK, 'Dính đòn siêu hiệu quả: tăng mạnh Tấn công và Tấn công đặc biệt (một lần).'),
    86: (TYPE, 'Genesect: đổi hệ của Techno Blast sang {t}.'),
    87: (TYPE, 'Silvally: đổi sang hệ {t}.'),
    88: (TYPE, 'Dialga: tăng sức mạnh chiêu hệ Thép và Rồng.'),
    89: (TYPE, 'Palkia: tăng sức mạnh chiêu hệ Nước và Rồng.'),
    90: (TYPE, 'Giratina: tăng sức mạnh chiêu hệ Ma và Rồng.'),
    91: (OTHER, 'Con này bị mê thì đối thủ cũng bị mê.'),
    92: (ATK, 'Tăng sát thương chiêu siêu hiệu quả (chuẩn ×1.2).'),
    93: (MEGA, 'Groudon/Kyogre: biến hình Primal.'),
    94: (TYPE, 'Tăng sức mạnh một chiêu hệ {t} rồi mất.'),
    95: (DEF, 'Giảm sát thương chiêu hệ {t} siêu hiệu quả (một lần).'),
    97: (OTHER, 'Luôn đánh sau.'),
    98: (OTHER, 'Giảm Tốc độ, mất miễn nhiễm hệ Đất.'),
    99: (OTHER, 'Tăng sát thương của chiêu trói.'),
    101: (DEF, 'Không dính hiệu ứng từ chiêu tiếp xúc.'),
    102: (ATK, 'Dính chiêu hệ Nước: tăng Tấn công đặc biệt (một lần).'),
    103: (DEF, 'Bay lên, miễn chiêu hệ Đất đến khi bị đánh trúng.'),
    104: (HEAL, 'Tăng lượng HP hồi từ chiêu hút máu.'),
    105: (ATK, 'Dính chiêu hệ Điện: tăng Tấn công (một lần).'),
    106: (DEF, 'Bị đánh trúng thì tự đổi con (một lần).'),
    107: (OTHER, 'Giảm cân nặng.'),
    108: (OTHER, 'Kéo dài chiêu trói.'),
    109: (DEF, 'Dính chiêu hệ Nước: tăng Phòng thủ đặc biệt (một lần).'),
    111: (ATK, 'Dùng một chiêu liên tiếp thì sức mạnh tăng dần.'),
    112: (ATK, 'Tăng sát thương chiêu vật lý (chuẩn ×1.1).'),
    113: (DEF, 'Bị đánh trúng thì buộc đối thủ đổi con (một lần).'),
    114: (OTHER, 'Bỏ miễn nhiễm hệ của con đang cầm.'),
    115: (OTHER, 'Luôn đổi con được, kể cả khi bị chặn.'),
    116: (ATK, 'Dính chiêu hệ Băng: tăng Tấn công (một lần).'),
    117: (OTHER, 'Mất HP mỗi lượt, có thể dính sang đối thủ.'),
    118: (OTHER, 'Kéo dài sân do con này tạo ra.'),
    119: (ATK, 'Tăng sát thương chiêu đặc biệt (chuẩn ×1.1).'),
    122: (DEF, 'Dính chiêu vật lý: tăng Phòng thủ (một lần).'),
    123: (DEF, 'Dính chiêu đặc biệt: tăng Phòng thủ đặc biệt (một lần).'),
    124: (SPEED, 'Tăng độ chính xác nếu đánh sau đối thủ.'),
    125: (SPEED, 'Bị Intimidate: tăng Tốc độ (một lần).'),
    126: (OTHER, 'Bỏ qua lượt tích sức của chiêu hai lượt (một lần).'),
    127: (SPEED, 'Tăng độ chính xác của chiêu kế tiếp khi HP thấp (một lần).'),
    128: (HEAL, 'Tự hồi HP khi dính đòn siêu hiệu quả (một lần).'),
    130: (MEGA, 'Đá Z: cho dùng Z-Move.'),
    131: (OTHER, 'Đổi Ability của Pokémon (xem mô tả trong game).'),
    132: (DEF, 'Bị giảm chỉ số thì tự đổi con (một lần).'),
    133: (SPEED, 'Khi có Trick Room: giảm Tốc độ (một lần).'),
    134: (SPEED, 'Đánh trượt: tăng mạnh Tốc độ (một lần).'),
    135: (DEF, 'Miễn hiệu ứng bẫy trên sân.'),
    136: (DEF, 'Không chịu tác động của thời tiết.'),
    137: (ATK, 'Dùng chiêu âm thanh: tăng Tấn công đặc biệt (một lần).'),
}

# vật phẩm không có mã hiệu ứng khi cầm (hoặc cần nhóm riêng): id -> (nhóm, công dụng, '' = dùng mô tả trong game)
ITEMS = {
    63: (DEF, 'Tăng vĩnh viễn điểm HP (EV).'),
    64: (ATK, 'Tăng vĩnh viễn điểm Tấn công (EV).'),
    65: (DEF, 'Tăng vĩnh viễn điểm Phòng thủ (EV).'),
    66: (SPEED, 'Tăng vĩnh viễn điểm Tốc độ (EV).'),
    67: (ATK, 'Tăng vĩnh viễn điểm Tấn công đặc biệt (EV).'),
    70: (DEF, 'Tăng vĩnh viễn điểm Phòng thủ đặc biệt (EV).'),
    73: (DEF, 'Trong trận: chặn đối thủ giảm chỉ số.'),
    74: (SPEED, 'Trong trận: tăng tỉ lệ chí mạng.'),
    75: (ATK, 'Trong trận: tăng Tấn công.'),
    76: (DEF, 'Trong trận: tăng Phòng thủ.'),
    77: (SPEED, 'Trong trận: tăng Tốc độ.'),
    79: (ATK, 'Trong trận: tăng Tấn công đặc biệt.'),
    609: (DEF, 'Tăng một ít điểm HP (EV).'),
    610: (ATK, 'Tăng một ít điểm Tấn công (EV).'),
    611: (DEF, 'Tăng một ít điểm Phòng thủ (EV).'),
    612: (ATK, 'Tăng một ít điểm Tấn công đặc biệt (EV).'),
    613: (DEF, 'Tăng một ít điểm Phòng thủ đặc biệt (EV).'),
    614: (SPEED, 'Tăng một ít điểm Tốc độ (EV).'),
}
ITEMS.update({i: (HEAL, '') for i in list(range(13, 38)) + [38, 39, 40, 41, 45] + list(range(514, 521))})
ITEMS.update({i: (EVO, '') for i in list(range(93, 103)) + [105, 112, 113, 115, 116, 117, 118, 119, 120, 234]})
ITEMS.update({i: (MEGA, '') for i in (176, 187, 199, 218, 232, 233)})   # đá Mega trong ROM không có mã hiệu ứng khi cầm

# vừa có công dụng khi cầm, vừa dùng để tiến hoá
ALSO_EVO = {'Razor Claw', 'Razor Fang', "King's Rock", 'DeepSeaTooth', 'DeepSeaScale', 'Metal Coat'}


def fold(text):
    """Bỏ dấu, chữ thường: gõ 'tan cong' vẫn tìm được 'Tấn công'."""
    text = text.lower().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')


def type_name(t):
    return TYPE_NAMES[t] if t < len(TYPE_NAMES) else str(t)


def decode_vi(raw):
    out = ''
    for x in raw:
        if x == 0xFF:
            break
        out += VI_CHARS.get(x, '')
    return ' '.join(out.split())


def _hold_use(hold, param, name):
    """(nhóm, công dụng) theo mã hiệu ứng khi cầm; None nếu không có."""
    if hold == 29:
        if param == 2:
            return SPEED, 'Tăng Tốc độ (chuẩn ×1.5), khoá vào 1 chiêu đến khi đổi con.'
        stat = 'Tấn công đặc biệt' if param == 1 else 'Tấn công'
        return ATK, 'Tăng mạnh %s (chuẩn ×1.5), khoá vào 1 chiêu đến khi đổi con.' % stat
    if hold == 24:
        if param in STATS:
            return OTHER, 'Không tăng sát thương: nhận thêm điểm %s (EV) khi thắng, giảm Tốc độ khi cầm.' % STATS[param]
        return OTHER, 'Không tăng sát thương: nhân đôi EV nhận được, giảm Tốc độ khi cầm.'
    if hold in TYPE_HOLD:
        return TYPE, 'Tăng sức mạnh chiêu hệ %s.' % TYPE_HOLD[hold]
    if hold == 96:
        if param:                   # Passho Berry: ROM gán mã 96 (giống Custap) chứ không phải 95 như các quả giảm hệ khác
            return DEF, 'Giảm sát thương chiêu hệ %s siêu hiệu quả; ROM gán mã hiệu ứng khác các quả cùng loại, có thể không chạy đúng.' % type_name(param)
        return SPEED, 'Đi trước trong lượt khi HP thấp (một lần).'
    if hold == 120:
        side = 'Phòng thủ' if param in (1, 2) else 'Phòng thủ đặc biệt'
        terrain = {1: 'Điện', 2: 'Cỏ', 3: 'Sương', 4: 'Siêu linh'}.get(param, '?')
        return DEF, 'Có sân %s: tăng %s (một lần).' % (terrain, side)
    if hold == 121:
        return DEF, 'Dính chiêu %s: đối thủ mất HP (một lần).' % ('đặc biệt' if param else 'vật lý')
    if hold == 129:
        return TYPE, 'Tăng sức mạnh chiêu hệ Thép; cũng dùng để tiến hoá.'
    if hold in HOLD:
        group, text = HOLD[hold]
        return group, text.format(t=type_name(param), p=param)
    return None


class ItemInfo:
    def __init__(self, id, name, groups, use, desc, price, pocket):
        self.id, self.name, self.groups, self.use, self.desc = id, name, groups, use, desc
        self.price, self.pocket = price, pocket
        self.key = fold(' '.join((name, use, desc) + tuple(groups)))

    def match(self, group, words):
        return (group == ALL or group in self.groups) and all(w in self.key for w in words)


def load_items(rom):
    """Tất cả vật phẩm chọn được trong túi (cùng bộ với rom.item_list()), theo số ID."""
    p = rom.profile
    base, size = rom._o(p.item_recs[0]), p.item_recs[1]
    d, out = rom.d, []
    for i, name in rom.item_list():
        rec = d[base + size * i: base + size * (i + 1)]
        price, hold, param, ptr = struct.unpack_from('<HBBI', rec, 16)
        o = ptr - ROM_BASE
        desc = decode_vi(d[o:o + 300]) if 0 <= o < len(d) else ''
        pocket = rec[p.item_pocket_off]
        use, groups = '', [OTHER]
        got = _hold_use(hold, param, name)
        if i in ITEMS:
            groups, use = [ITEMS[i][0]], ITEMS[i][1]
        elif got:
            groups, use = [got[0]], got[1]
        if name in ALSO_EVO:
            groups = groups + [EVO]
        if name.startswith(('TM', 'HM')) and name[2:].isdigit():
            n = int(name[2:]) - 1 + (p.tm_count if name.startswith('HM') else 0)   # bảng chiêu: các TM rồi 8 HM
            mv = struct.unpack_from('<H', d, rom._o(p.tm_moves) + 2 * n)[0]
            groups = [TM]
            use = 'Dạy chiêu %s: hệ %s, sức mạnh %s, chính xác %s, PP %d.' % (
                rom.move_name(mv), type_name(d[rom._o(p.move_data[0]) + p.move_data[1] * mv + 2]),   # hệ ở +2
                rom.move_power(mv) or '-', rom.move_accuracy(mv) or '-', rom.move_pp(mv))
        out.append(ItemInfo(i, name, groups, use, desc, price, pocket))
    return out
