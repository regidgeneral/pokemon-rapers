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

print('%d/%d qua' % (ok, ok + fail))
sys.exit(1 if fail else 0)
