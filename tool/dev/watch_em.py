"""Theo dõi game FireRed đang chạy: in mỗi khi map / trận / đội đổi, kiểm tự hồi máu sau trận.
Dừng sau khi thấy 2 trận xong (hoặc 30 phút).  py -3 dev\\watch_fr.py"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
from mm_core import *

rom = Rom(EMERALD)
g = Game(Bridge(timeout=2), rom)
LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tick_error.log')


def safe(f):
    for _ in range(10):
        try:
            return f()
        except Exception:
            time.sleep(0.25)
    return None


def team():
    ps = safe(g.party) or []
    return tuple((rom.species_name(m.species), m.level, m.hp, m.maxhp, m.checksum_ok) for m in ps if not m.empty)


last = {}
done, t0, end_at = 0, time.time(), None
print(time.strftime('%H:%M:%S'), 'bắt đầu theo dõi')
while time.time() - t0 < 1800 and done < 2:
    st = safe(g.battle_state)
    mp = safe(g.current_map)
    tm = team()
    cur = {'map': mp, 'battle': st, 'team': tm}
    if st and st[0]:
        foes = safe(g.enemy_party) or []
        cur['foe'] = tuple((rom.species_name(m.species), m.level, m.hp, m.checksum_ok) for m in foes if not m.empty)
    for k, v in cur.items():
        if last.get(k) != v:
            label = rom.map_name(*v) if k == 'map' and v else ''
            print(time.strftime('%H:%M:%S'), k, v, label)
    if last.get('battle') and last['battle'][0] and st and not st[0]:
        end_at = time.time()
        print(time.strftime('%H:%M:%S'), '--- trận xong, đợi về overworld xem tool hồi máu')
    if end_at and st and st[1] and not st[0] and time.time() - end_at > 4:
        full = all(hp == mx for _, _, hp, mx, _ in tm)
        print(time.strftime('%H:%M:%S'), 'SAU TRẬN: đội', tm, '-> hồi đầy' if full else '-> CHƯA hồi')
        end_at, done = None, done + 1
    if os.path.exists(LOG) and not last.get('log'):
        cur['log'] = True
        print('TICK_ERROR.LOG:', open(LOG, encoding='utf-8').read()[-1500:])
    last.update(cur)
    time.sleep(1.5)
print(time.strftime('%H:%M:%S'), 'dừng theo dõi')
