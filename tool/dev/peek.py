import sys, os, time
sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding='utf-8')
from mm_core import *
rom = Rom(EMERALD); g = Game(Bridge(), rom)
def retry(f):
    for _ in range(6):
        try: return f()
        except BridgeError: time.sleep(0.3)
    raise SystemExit('bridge busy')
for m in retry(g.party):
    if not m.empty:
        print(rom.species_name(m.species), m.level, [rom.move_name(x) for x in m.moves if x], 'hp', m.hp)
print('Balls:', [(rom.item_name(i), q) for i, q in retry(lambda: g.read_pocket(2)) if i])
