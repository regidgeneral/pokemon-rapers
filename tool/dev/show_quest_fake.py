"""In nội dung tab Việc (bộ nhớ giả) cho một bước: py -3 dev\\show_quest_fake.py [số bước đã xong, mặc định 11]"""
import os, struct, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
import mm_gui, mm_quest
app = mm_gui.App(fake=True)
app.withdraw()
g, p, b = app.game, app.prof, app.bridge
n = int(sys.argv[1]) if len(sys.argv) > 1 else 11
sb1 = g.sb1()
fa, va = sb1 + p.flags_off, sb1 + p.vars_off
b.write(fa, bytes(0x12C))
b.write(va, bytes(0x200))
for s in mm_quest.STEPS[:n]:
    if s['done'][0] == 'f':
        f = s['done'][1]
        b.write(fa + (f >> 3), bytes([b.read(fa + (f >> 3), 1)[0] | 1 << (f & 7)]))
    else:
        b.write(va + 2 * (s['done'][1] - 0x4000), struct.pack('<H', s['done'][2]))
b.write(sb1 + p.loc_off, bytes([0, 1]))
b.write(p.player_obj + 0x10, struct.pack('<hh', 21 + 7, 15 + 7))
b.write(p.cb2_addr, struct.pack('<I', p.cb2_overworld))
b.write(g.pocket_info(p.key_pocket)[0], struct.pack('<HH', 269, 1 ^ (g.key32() & 0xFFFF)))
app.q_follow.set(True)
app.quest_tick(force=True)
app.update()
print(app.q_text.get('1.0', 'end').strip())
app.destroy()
