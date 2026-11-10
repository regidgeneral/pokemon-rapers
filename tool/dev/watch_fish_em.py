"""Đo câu cá + trận đấu Emerald trong game thật (chỉ ĐỌC, không bấm phím, không ghi).
Ghi ra mỗi khi đổi: task đang chạy (hàm + data[0..3]), gMain.callback2, gBattlerControllerFuncs[0..3], cờ trong trận,
khoá điều khiển, phím đang giữ. Bạn tự câu bằng tay, script ghi lại hàm + từng bước của task câu cá.
  py -3 dev\\watch_fish_em.py [số giây, mặc định 600]"""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
from mm_core import *

p = EMERALD
b = Bridge(timeout=2)
TASKS, MAIN, CTL = 0x03005E00, 0x030022C0, p.battle_ctl
KEYS = {1: 'A', 2: 'B', 4: 'SEL', 8: 'START', 0x10: 'R', 0x20: 'L', 0x40: 'U', 0x80: 'D', 0x100: 'RB', 0x200: 'LB'}
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 600
t0 = time.time()
last = {}
seen_fn = {}


def keys(v):
    return '+'.join(n for m, n in KEYS.items() if v & m) or '-'


print(time.strftime('%H:%M:%S'), 'bắt đầu đo %d giây' % dur)
while time.time() - t0 < dur:
    try:
        tasks, main, ctl, lock, held = b.read_many([(TASKS, 16 * 40), (MAIN, 0x440), (CTL, 16), (p.fly['lock'], 1),
                                                    (MAIN + 0x2C, 2)])
    except (BridgeError, OSError) as e:                     # OSError: tool đang mở giữ file ipc

        print(time.strftime('%H:%M:%S'), 'bridge:', e)
        time.sleep(0.5)
        continue
    cur = {}
    act = []
    for i in range(16):
        fn, active = struct.unpack_from('<IB', tasks, 40 * i)
        if active:
            data = struct.unpack_from('<4h', tasks, 40 * i + 8)
            act.append((i, '%08x' % fn, data))
            seen_fn[fn] = seen_fn.get(fn, 0) + 1
    cur['tasks'] = tuple(act)
    cur['cb2'] = '%08x' % struct.unpack_from('<I', main, 4)[0]
    cur['inBattle'] = main[0x439] & 2
    cur['ctl'] = tuple('%08x' % x for x in struct.unpack('<4I', ctl))
    cur['lock'] = lock[0]
    cur['keys'] = keys(struct.unpack('<H', held)[0])
    sig = lambda c, k: tuple((i, fn, d[0]) for i, fn, d in c[k]) if k == 'tasks' else c.get(k)   # task: chỉ hàm + bước
    ch = [k for k in cur if not last or sig(last, k) != sig(cur, k)]
    if ch:
        print('%s %6.2f | %s' % (time.strftime('%H:%M:%S'), time.time() - t0,
                                 ' | '.join('%s=%s' % (k, cur[k]) for k in ch)))
    last = cur
    time.sleep(0.05)
print(time.strftime('%H:%M:%S'), 'xong. Hàm task đã thấy (số lần):')
for fn, n in sorted(seen_fn.items(), key=lambda x: -x[1]):
    print('  %08x %d' % (fn, n))
