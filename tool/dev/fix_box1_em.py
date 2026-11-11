"""Cứu Box 1 bị ghi lệch 56 byte (11/11): chia EXP cho kho ghi theo địa chỉ cũ lúc game vừa dời kho PC.
Gốc = Box 1 trong bản save sạch (16:38 ngày 10/11, trước khi bật chia EXP), cộng lại EXP theo battle_log.jsonl (đúng thứ
tự từng trận, tiến hoá như tool đã làm). Ô chưa có trong bản save sạch (bắt sau) lấy từ dữ liệu lệch trong RAM.
  py -3 dev\\fix_box1_em.py <file .sav sạch>          in 30 ô sẽ ghi, đối chiếu với RAM (chỉ đọc)
  py -3 dev\\fix_box1_em.py <file .sav sạch> --ghi    ghi vào RAM (có điều kiện), đọc lại kiểm checksum
Sau khi ghi: lưu game trong mGBA."""
import json, os, struct, sys, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
from mm_core import *

SHIFT = 56                                  # dữ liệu Box 1 thật bắt đầu ở (con trỏ kho + 4 - 56)
rom = Rom(EMERALD)
g = Game(Bridge(timeout=2), rom)
p = EMERALD


def save_storage(path):
    """PokemonStorage trong bản lưu mới hơn của file .sav (sector 5-13, mỗi sector 3968 byte)."""
    d = open(path, 'rb').read()
    best = None
    for slot in (0, 1):
        secs = {}
        for i in range(14):
            s = d[(slot * 14 + i) * 0x1000:(slot * 14 + i + 1) * 0x1000]
            sid, _, sig, cnt = struct.unpack_from('<HHII', s, 0xFF4)
            if sig == 0x08012025:
                secs[sid] = (s, cnt)
        if len(secs) == 14 and (best is None or secs[0][1] > best[0]):
            best = (secs[0][1], secs)
    return b''.join(best[1][i][0][:3968] for i in range(5, 14))


# Đo 11/11 trên 24 con có bản sạch: game coi các ô lệch là con hỏng và chỉ BẬT thêm bit -- byte 75 bit trong 0x07
# (bad egg / hasSpecies / isEgg), byte 15, 27, 39, 51 (bước 12 byte, có thể cả 63) bit 0x40. Byte 15, 27 (tên, đánh dấu)
# không vào checksum.
FLAG_BITS = {39: 0x40, 51: 0x40, 63: 0x40, 75: 0x07}


def unflag(c):
    """TẮT bớt các bit game đã bật (FLAG_BITS) để checksum khớp; nhận khi đúng MỘT cách khớp, không thì None.
    Bit 0x40 ở byte 27 (đánh dấu, game chỉ dùng 4 bit thấp) cũng tắt luôn."""
    pid, ot = struct.unpack_from('<II', c)
    want = struct.unpack_from('<H', c, 28)[0]

    def ok(x):
        s = 0
        for i in range(32, 80, 4):
            w = struct.unpack_from('<I', x, i)[0] ^ pid ^ ot
            s += (w & 0xFFFF) + (w >> 16)
        return s & 0xFFFF == want
    cands = [bytearray(c)]
    cands[0][27] &= ~0x40
    for pos, bits in FLAG_BITS.items():
        on = c[pos] & bits
        nxt = []
        for x in cands:
            m = on
            while True:                                          # mọi tập con của các bit đang bật (kể cả rỗng)
                y = bytearray(x)
                y[pos] &= ~m
                nxt.append(y)
                if not m:
                    break
                m = (m - 1) & on
        cands = nxt
    hits = {bytes(x) for x in cands if ok(x)}
    return hits.pop() if len(hits) == 1 else None


def retry(f):
    for _ in range(60):
        try:
            return f()
        except BridgeError:
            time.sleep(0.2)
    raise SystemExit('Không nói chuyện được với mGBA.')


def read_ram():
    """(con trỏ kho, 4 byte đầu kho, 2400 byte Box 1 hiện tại, 30 ô dữ liệu lệch) đọc trong lúc con trỏ không đổi."""
    while True:
        ptr = retry(lambda: g.b.read_u32(p.storage_ptr))
        head, box1, shifted = retry(lambda: g.b.read_many([(ptr, 4), (ptr + 4, 2400), (ptr + 4 - SHIFT, 2400)]))
        if retry(lambda: g.b.read_u32(p.storage_ptr)) == ptr:
            return ptr, head, box1, [shifted[i * 80:(i + 1) * 80] for i in range(30)]


def main():
    clean = save_storage(sys.argv[1])
    ref = [clean[4 + i * 80:4 + (i + 1) * 80] for i in range(30)]
    log = [json.loads(l) for l in open(os.path.join(HERE, 'battle_log.jsonl'), encoding='utf-8') if l.strip()]
    ever = rom.item_id('EVERSTONE')
    ptr, head, box1, shifted = read_ram()
    ram = {struct.unpack_from('<I', c)[0]: c for c in shifted if any(c)}
    out, bad, tried = [], 0, [0, 0]
    print('Kho %08X, byte đầu %s (box đang chọn phải 0-13)' % (ptr, head.hex()))
    for k in range(30):
        if any(ref[k]):
            m = box_to_party(rom, ref[k])
            src = 'save sạch'
            for e in log:                                       # cộng lại EXP từng trận như tool đã cộng
                for idx, name, lv0, lv1, gain in e['box']:
                    if idx == k:
                        if m.level != lv0:
                            print('  ! ô %d trận %s: level %d, log ghi %d' % (k + 1, e['time'], m.level, lv0))
                        share_exp_apply(rom, m, gain, ever)
                        if rom.species_name(m.species) != name or m.level != lv1:
                            print('  ! ô %d trận %s: ra %s Lv%d, log ghi %s Lv%d' % (
                                k + 1, e['time'], rom.species_name(m.species), m.level, name, lv1))
                            bad += 1
        else:
            c = shifted[k]
            if not any(c):
                out.append(bytes(80))
                print('%2d (trống)' % (k + 1))
                continue
            m = box_to_party(rom, c)
            src = 'RAM lệch'
            if not m.checksum_ok:
                fixed = unflag(c)
                if not fixed:
                    print('%2d %s: checksum sai, không dò được byte gốc' % (k + 1, rom.species_name(m.species)))
                    bad += 1
                    out.append(bytes(c))
                    continue
                m = box_to_party(rom, fixed)
                src += ', gỡ cờ game bật: chiêu %s IV %s' % ([rom.move_name(x) for x in m.moves if x], m.iv)
        cell = party_to_box(m)
        if src == 'save sạch' and any(ref[k]):
            r = ram.get(m.pid)
            if r:                                               # kiểm cách gỡ cờ trên con có bản sạch
                fx = r if box_to_party(rom, r).checksum_ok else unflag(r)
                tried[0] += 1
                same = bool(fx) and fx[28:] == cell[28:]            # bỏ qua tên/đánh dấu (byte 15, 27): không vào checksum
                tried[1] += same
                if not same:
                    print('   gỡ cờ ô %d: %s | RAM so với bản sạch: %s' % (k + 1, 'không dò được' if not fx else 'khác byte %s' % [
                        i for i in range(28, 80) if fx[i] != cell[i]], ['%d:%02x>%02x' % (i, cell[i], r[i])
                                                                        for i in range(80) if r[i] != cell[i]]))
        r = ram.get(m.pid)
        rm = box_to_party(rom, r) if r else None
        same = rm and rm.species == m.species and rm.exp == m.exp
        print('%2d %-10s Lv%3d  EXP %7d  (%s)  RAM: %s' % (
            k + 1, rom.species_name(m.species), m.level, m.exp, src,
            'khớp' if same else ('%s Lv%d EXP %d' % (rom.species_name(rm.species), rm.level, rm.exp) if rm else 'không có')))
        out.append(cell)
    new = b''.join(out)
    chk = [box_to_party(rom, new[i * 80:(i + 1) * 80]) for i in range(30) if any(new[i * 80:(i + 1) * 80])]
    print('Gỡ cờ trên con có bản sạch: %d/%d ra đúng y phần dữ liệu' % (tried[1], tried[0]))
    print('%d con, %d checksum đúng, %d chỗ không khớp' % (len(chk), sum(x.checksum_ok for x in chk), bad))
    if '--ghi' not in sys.argv:
        print('Chỉ đọc. Thêm --ghi để ghi vào game.')
        return
    if bad or not all(x.checksum_ok for x in chk):
        raise SystemExit('Không ghi: còn chỗ chưa khớp.')
    g._require_overworld()
    g._box_cas(ptr, [(ptr, bytes(head), bytes(4)), (ptr + 4, bytes(box1), new)])
    _, _, after, _ = read_ram()
    ok = sum(box_to_party(rom, after[i * 80:(i + 1) * 80]).checksum_ok for i in range(30) if any(after[i * 80:(i + 1) * 80]))
    print('Đã ghi. Đọc lại Box 1: %d/%d con checksum đúng. Giờ lưu game trong mGBA.' % (ok, len(chk)))


main()
