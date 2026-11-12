"""Tool ghi Pokémon đúng lúc game đang giải mã nó tại chỗ (lỗi Metapod hỏng 09/11) — bộ nhớ giả.
Game FR: Decrypt (XOR tại chỗ) → đọc/sửa → Encrypt (XOR lại). Bridge ghi ở cuối khung hình, có thể rơi vào giữa.
py -3 dev\\t_race_fake.py"""
import os, sys, struct
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
import mm_gui
from mm_core import *

app = mm_gui.App(fake=True)
app.withdraw()
g, r, b = app.game, app.rom, app.game.b
ok = fail = 0


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(('  qua: ' if cond else 'SAI: ') + name)


SLOT = 1
addr = g.p.party_base + SLOT * MON_SIZE


def game_xor():
    """Game giải mã / mã hoá lại tại chỗ: XOR 48 byte giữa với PID ^ OTID, KHÔNG xếp lại khối."""
    raw = b._read(addr, MON_SIZE)
    pid, otid = struct.unpack_from('<II', raw, 0)
    b._write(addr + 0x20, struct.pack('<12I', *(x ^ pid ^ otid for x in struct.unpack_from('<12I', raw, 0x20))))


CLEAN = b._read(addr, MON_SIZE)


def damage():
    """Mỗi ca bắt đầu từ con lành, mất máu (để tool có lý do ghi)."""
    m = FrMon(CLEAN)
    m.hp = 1
    b._write(addr, m.to_bytes())
    return m.species


real_party = g.party
real_cas = getattr(b, '_write_cas', None)

# --- Ca 1: game giải mã ngay sau khi tool đọc và còn giải mã suốt lúc tool ghi (đúng ca Metapod)
sp = damage()
def party_then_decrypt():
    """Lần đọc đầu của tool xong thì game giải mã (heal_slots còn đọc lại đội để vẽ, lần đó không giải mã nữa)."""
    res = real_party()
    if not decrypted:
        decrypted.append(1)
        game_xor()
    return res
decrypted = []
g.party = party_then_decrypt
app.heal_slots([SLOT])
g.party = real_party
game_xor()                                   # game mã hoá lại
m = g.party()[SLOT]
check('ca 1: không hỏng dữ liệu (checksum đúng, đúng loài)', m.checksum_ok and m.species == sp)

# --- Ca 2: game đang giải mã lúc tool ghi lần đầu, khung hình sau đã mã hoá lại -> tool thử lại và hồi được
sp = damage()
calls = []
decrypted.clear()
def cas_then_reencrypt(items):
    res = real_cas(items)
    if not calls:
        game_xor()                           # khung hình sau: game xong việc, mã hoá lại
    calls.append(res)
    return res
if real_cas:
    b._write_cas = cas_then_reencrypt
g.party = party_then_decrypt
app.heal_slots([SLOT])
g.party = real_party
if real_cas:
    b._write_cas = real_cas
else:
    game_xor()
m = g.party()[SLOT]
check('ca 2: thử lại ở khung sau và hồi đầy máu', m.checksum_ok and m.species == sp and m.hp == m.maxhp)

# --- Ca 3: tool đọc trúng lúc game đang giải mã -> không được ghi lại dữ liệu rác
sp = damage()
game_xor()
app.heal_slots([SLOT])
game_xor()
m = g.party()[SLOT]
check('ca 3: đọc trúng bản đang giải mã thì không ghi', m.checksum_ok and m.species == sp)

# --- Ca 4: bình thường vẫn ghi được (hồi máu, sửa con)
sp = damage()
app.heal_slots([SLOT])
m = g.party()[SLOT]
check('ca 4: bình thường vẫn hồi máu', m.checksum_ok and m.hp == m.maxhp)

# --- move_party (Duy 12/11: ghi có điều kiện như write_mon)
b.write(g.p.cb2_addr, struct.pack('<I', g.p.cb2_overworld))
b.write(g.p.battle_flag[0], bytes([b.read(g.p.battle_flag[0], 1)[0] & ~g.p.battle_flag[1] & 0xFF]))
damage()
b._write(addr, CLEAN)
before = [m.species for m in g.party() if not m.empty]
raw0 = b._read(g.p.party_base, MON_SIZE * len(before))


def party_species():
    return [m.species for m in g.party() if not m.empty]


# ca 5: bình thường -> đổi chỗ đúng, mọi con còn lành
g.move_party(0, len(before) - 1)
ps = g.party()
check('ca 5: move_party bình thường đổi chỗ đúng', party_species() == before[1:] + before[:1]
      and all(m.checksum_ok for m in ps if not m.empty))
b._write(g.p.party_base, raw0)

# ca 6: tool đọc trúng lúc game đang giải mã con ô 2 -> từ chối, không ghi gì
game_xor()
try:
    g.move_party(0, len(before) - 1)
    refused = False
except ValueError:
    refused = True
game_xor()
check('ca 6: đọc trúng con đang giải mã -> từ chối, đội y nguyên',
      refused and b._read(g.p.party_base, len(raw0)) == raw0)

# ca 7: game giải mã ngay sau khi tool đọc, khung sau mã hoá lại -> tool thử lại, ghi đúng, không hỏng
calls.clear()
if real_cas:
    def cas_first_decrypted(items):
        if not calls:
            game_xor()                       # lần ghi đầu: con ô 2 đang giải mã -> CAS phải từ chối
        res = real_cas(items)
        if not calls:
            game_xor()                       # khung sau: game mã hoá lại
        calls.append(res)
        return res
    b._write_cas = cas_first_decrypted
g.move_party(0, len(before) - 1)
if real_cas:
    b._write_cas = real_cas
ps = g.party()
check('ca 7: lần đầu lệch thì không ghi, thử lại ghi đúng (%s)' % calls,
      calls[:1] == [False] and party_species() == before[1:] + before[:1] and all(m.checksum_ok for m in ps if not m.empty))
b._write(g.p.party_base, raw0)

print('%d/%d qua' % (ok, ok + fail))
sys.exit(1 if fail else 0)
