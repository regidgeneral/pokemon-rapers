"""Thử phần nhiệm vụ cốt truyện Emerald (mm_quest + tab Việc / Cốt truyện + đường tím), bộ nhớ giả.
  py -3 dev\\t_quest_fake.py"""
import os, struct, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
from tkinter import messagebox
for k in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
    setattr(messagebox, k, lambda *a, _k=k, **kw: print('[hộp thoại %s]' % _k, a[:2]) or False)
import mm_gui, mm_quest
from mm_core import *

app = mm_gui.App(fake=True)
app.withdraw()
g, p, b, r, st = app.game, app.prof, app.bridge, app.rom, app.story
ok = fail = 0
S = mm_quest.STEPS


def check(name, cond):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(('  ĐÚNG ' if cond else '  SAI  ') + name)


# 1) dữ liệu
maps = set(st.maps())
check('%d bước, mọi map có trong ROM' % len(S), all(s['map'] in maps for s in S))
bad = [i + 1 for i, s in enumerate(S) if not (0 <= s['xy'][0] < st.map_info(*s['map'])['w'] and
                                             0 <= s['xy'][1] < st.map_info(*s['map'])['h'])]
check('ô nhiệm vụ nằm trong map (sai: %s)' % bad, not bad)
check('cờ nằm trong vùng tool đọc (< 0x900)', all(s['done'][1] < 0x900 for s in S if s['done'][0] == 'f'))
check('biến hợp lệ (0x4000-0x40FF)', all(0x4000 <= s['done'][1] < 0x4100 for s in S if s['done'][0] == 'v'))
far = []
for i, s in enumerate(S):
    info = st.map_info(*s['map'])
    starts = [(w['x'], w['y']) for w in info['warps']] or [(info['w'] // 2, info['h'] // 2)]
    goals = {(s['xy'][0] + dx, s['xy'][1] + dy) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))}
    if not any(st.walk_path(*s['map'], a, goals) for a in starts):
        far.append(i + 1)
check('đi bộ tới được ô nhiệm vụ từ một cửa của map (không tới được: %s)' % far, len(far) <= 4)
print('     (bước không có đường từ cửa — thường là map ngoài trời vào bằng mép map / nước:', far, ')')

# 2) tính bước hiện tại
def prog(done_idx):
    fl = {S[i]['done'][1] for i in done_idx if S[i]['done'][0] == 'f'}
    vr = {S[i]['done'][1]: S[i]['done'][2] for i in done_idx if S[i]['done'][0] == 'v'}
    return mm_quest.progress(lambda f: f in fl, lambda v: vr.get(v, 0))[1]


opt = next(i for i, s in enumerate(S) if s.get('optional'))
check('chưa làm gì -> bước 1', prog([]) == 0)
check('xong 11 bước đầu -> bước 12 (Dock ở xưởng tàu)', prog(range(11)) == 11 and S[11]['who'].startswith('Dock'))
check('xong Dock -> bước 13 (Captain Stern)', prog(range(12)) == 12 and S[12]['who'] == 'Captain Stern')
check('bỏ bước tuỳ chọn (Rock Smash) -> đi tiếp bước sau nó', prog([i for i in range(opt + 1) if i != opt]) == opt + 1)
check('làm khác thứ tự: bước sau xong -> chỉ bước sau nữa', prog([0, 1, 2, 5]) == 6)
check('xong hết -> None', prog(range(len(S))) is None)

# 3) giao diện: giả lập Duy ở Slateport, đã xong 11 bước
sb1 = g.sb1()
fa, va = sb1 + p.flags_off, sb1 + p.vars_off
b.write(fa, bytes(0x12C))
b.write(va, bytes(0x200))
for s in S[:11]:
    if s['done'][0] == 'f':
        f = s['done'][1]
        b.write(fa + (f >> 3), bytes([b.read(fa + (f >> 3), 1)[0] | 1 << (f & 7)]))
    else:
        b.write(va + 2 * (s['done'][1] - 0x4000), struct.pack('<H', s['done'][2]))
b.write(sb1 + p.loc_off, bytes([0, 1]))                       # SLATEPORT CITY
b.write(p.player_obj + 0x10, struct.pack('<hh', 21 + 7, 15 + 7))
b.write(p.cb2_addr, struct.pack('<I', p.cb2_overworld))
app.q_follow.set(True)
app.quest_tick(force=True)
app.update()
txt = app.q_text.get('1.0', 'end')
check('tab Việc: "BƯỚC TIẾP THEO (12/%d)" + Dock' % len(S), 'BƯỚC TIẾP THEO (12/%d)' % len(S) in txt and 'Dock' in txt)
check('tab Việc: không còn chữ chỉ hướng (mép Đông / sang phải...)',
      not any(w in txt for w in ('mép Đông', 'mép Tây', 'mép Bắc', 'mép Nam', 'sang phải', 'sang trái', 'lên trên', 'xuống dưới')))
check('tab Việc: có chặng đường tới xưởng tàu', 'ĐƯỜNG ĐI' in txt and 'vào cửa' in txt)
check('bản đồ: vẽ đường tím từ nhân vật', bool(app.q_cv.find_withtag('qpath')))
co = app.q_cv.coords(app.q_cv.find_withtag('qpath')[-1])
k = app.q_scale * 16
yard = {(w['x'], w['y']) for w in st.map_info(0, 1)['warps'] if w['to'] == S[11]['map']}
check('đường tím bắt đầu ở nhân vật (21,15), kết thúc ở cửa xưởng tàu %s' % sorted(yard),
      co[:2] == [21 * k + k // 2, 15 * k + k // 2] and tuple((c - k // 2) // k for c in co[-2:]) in yard)
app.quest_show_step(S[12])
app.update()
check('xem chỗ nhiệm vụ: mở map bảo tàng tầng 2 + ★ ở Captain Stern',
      app.q_shown == S[12]['map'] and bool(app.q_cv.find_withtag('qtarget')))

# 3b) đúng cảnh Duy gửi ảnh 11/11: tới bước Stern mà hàng lính Aqua còn đứng chắn 2 ô trước cửa bảo tàng
s12 = S[11]['done'][1]
b.write(fa + (s12 >> 3), bytes([b.read(fa + (s12 >> 3), 1)[0] | 1 << (s12 & 7)]))
b.write(p.player_obj + 0x10, struct.pack('<hh', 31 + 7, 28 + 7))      # Duy đứng ở 31,28
for i, (lid, x, y) in enumerate(((18, 30, 27), (5, 31, 27), (19, 29, 27)), 1):
    o = p.player_obj + 0x24 * i
    e = bytearray(0x24)
    e[0], e[8], e[9], e[0xA] = 1, lid, 1, 0
    struct.pack_into('<hh', e, 0x10, x + 7, y + 7)
    b.write(o, bytes(e))
app.q_nb.select(0)
app.quest_home()
app.update()
txt = app.q_text.get('1.0', 'end')
check('bước 13 Captain Stern', 'BƯỚC TIẾP THEO (13/%d)' % len(S) in txt)
check('báo NPC chắn đường + phải nói chuyện với NPC ô 5,5 (Dock) ở Slateport',
      'CHẮN ĐƯỜNG' in txt and 'nói chuyện với NPC ở ô 5,5' in txt)
blk = app.q_cv.find_withtag('qblk')
xs = {tuple(int(c) // k for c in app.q_cv.coords(i)[:2]) for i in blk}
check('bản đồ: ✖ đỏ trên lính chắn đường đi (ô %s)' % sorted(xs), len(blk) >= 2 and xs <= {(30, 27), (31, 27)})
for i in range(1, 4):                                                  # dọn NPC giả
    b.write(p.player_obj + 0x24 * i, bytes(0x24))
app.q_nb.select(app.q_t_story)
app.quest_story()
stxt = app.q_stext.get('1.0', 'end')
check('tab Cốt truyện: 12 ✔, ➜ ở bước 13', stxt.count('✔') == 12 and '➜ 13.' in stxt)
app.q_guide.set(False)
app.quest_home()
app.update()
check('tắt dẫn đường: không vẽ đường tím', not app.q_cv.find_withtag('qpath'))

print('\n%d đúng, %d sai' % (ok, fail))
app.destroy()
sys.exit(1 if fail else 0)
