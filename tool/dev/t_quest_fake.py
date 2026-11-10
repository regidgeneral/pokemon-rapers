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


rs = next(i for i, s in enumerate(S) if s['done'] == ('f', mm_quest.HMS['rocksmash']['got']))
check('Rock Smash là bước bắt buộc (đá chắn Route 111 ô 18,101) + Meteor Falls cần HM rocksmash',
      not S[rs].get('optional') and ('hm', 'rocksmash') in S[rs + 1].get('needs', []))
check('chưa làm gì -> bước 1', prog([]) == 0)
check('xong 11 bước đầu -> bước 12 (Dock ở xưởng tàu)', prog(range(11)) == 11 and S[11]['who'].startswith('Dock'))
check('xong Dock -> bước 13 (Captain Stern)', prog(range(12)) == 12 and S[12]['who'] == 'Captain Stern')
check('chưa lấy Rock Smash -> chỉ bước Rock Smash', prog(range(rs)) == rs)
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
key16 = g.key32() & 0xFFFF
kp = g.pocket_info(p.key_pocket)[0]
b.write(kp, struct.pack('<HH', 269, 1 ^ key16) + bytes(4 * 29))   # túi chính: Devon Goods (như save thật)
app.q_follow.set(True)
app.quest_tick(force=True)
app.update()
txt = app.q_text.get('1.0', 'end')
check('tab Việc: 🎯 MỤC TIÊU = chương Captain Stern, ➜ nói chuyện với Dock',
      '🎯 MỤC TIÊU: Giao Devon Goods cho Captain Stern' in txt and '➜ Vào xưởng tàu Stern, nói chuyện với Dock' in txt)
check('tab Việc: chuỗi có ✔ Briney (xong) và ⬜ bảo tàng + ✔ Có Devon Goods trong túi',
      '✔ Nhờ ông Briney chở tới Slateport' in txt and '⬜ Vào bảo tàng tầng 2' in txt and '✔ Có Devon Goods trong túi' in txt)
check('tab Việc: danh sách theo map thu gọn', '▸ Chi tiết map này' in txt and 'CÒN TRÊN MAP NÀY' not in txt
      and not app.q_marks)
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
check('bước 13 Captain Stern', '➜ Vào bảo tàng tầng 2' in txt and '✔ Vào xưởng tàu Stern' in txt)
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

# 4) chuỗi HM (Duy 11/11: "muốn dùng Rock Smash thì cần mấy huy hiệu, lấy ở đâu"): bước Meteor Falls cần Rock Smash
mf = next(i for i, s in enumerate(S) if s['map'] == (24, 0))          # METEOR FALLS
for s in S[:mf]:
    if s['done'][0] == 'f':
        f = s['done'][1]
        b.write(fa + (f >> 3), bytes([b.read(fa + (f >> 3), 1)[0] | 1 << (f & 7)]))
    else:
        b.write(va + 2 * (s['done'][1] - 0x4000), struct.pack('<H', s['done'][2]))


class M:                                                     # con trong đội giả: chỉ cần loài + chiêu
    def __init__(self, sp, moves):
        self.species, self.moves, self.empty, self.checksum_ok = sp, moves, False, True


real_party = g.party
g.party = lambda: [M(279, [33, 0, 0, 0])]                    # GROVYLE chưa biết Rock Smash
app.q_nb.select(0)
app.quest_home()
app.update()
txt = app.q_text.get('1.0', 'end')
check('Meteor Falls: 🎯 chương Mt. Chimney, ➜ Meteor Falls', '🎯 MỤC TIÊU: Chặn Team Magma' in txt and '➜ Tới Meteor Falls' in txt)
check('⬜ HM06 Rock Smash trong túi — nhận ở nhà Mauville', '⬜ HM06 Rock Smash trong túi — nhận: người trong nhà ở Mauville' in txt)
check('⬜ Huy hiệu 3 (Wattson) — mới dùng được ngoài trận', '⬜ Huy hiệu 3 (Wattson) — mới dùng được ROCK SMASH ngoài trận' in txt)
check('⬜ chưa con nào biết Rock Smash', '⬜ Chưa con nào trong đội biết ROCK SMASH' in txt)
check('đường tím tự dẫn tới thứ thiếu đầu tiên (nhà Mauville có HM06)',
      app.guide_goal()[:2] == (mm_quest.HMS['rocksmash']['map'], mm_quest.HMS['rocksmash']['xy']))
tm = g.pocket_info(app.rom.item_pocket(344) - 1)[0]
b.write(tm, struct.pack('<HH', 344, 1 ^ key16))               # có HM06
f = 0x866 + 3
b.write(fa + (f >> 3), bytes([b.read(fa + (f >> 3), 1)[0] | 1 << (f & 7)]))   # có huy hiệu 3
g.party = lambda: [M(279, [33, 249, 0, 0])]                   # Grovyle đã học Rock Smash
app.quest_home()
app.update()
txt = app.q_text.get('1.0', 'end')
check('đủ hết: ✔ HM06, ✔ huy hiệu 3, ✔ %s biết' % r.species_name(279), '✔ HM06 Rock Smash trong túi' in txt
      and '✔ Huy hiệu 3' in txt and '✔ %s biết ROCK SMASH' % r.species_name(279) in txt)
check('đủ hết: đường tím dẫn thẳng tới Meteor Falls', app.guide_goal()[:2] == (S[mf]['map'], S[mf]['xy']))
# đúng ảnh Duy 11/11: Route 112 phía dưới (19,37), mép sang Route 113 ở phía trên vách -> phải qua Fiery Path (cửa 11,36)
b.write(sb1 + p.loc_off, bytes([0, 27]))
b.write(p.player_obj + 0x10, struct.pack('<hh', 19 + 7, 37 + 7))
app.quest_home()
app.update()
rp = app.guide_route((0, 27))
check('Route 112 (19,37) -> Meteor Falls: chặng đầu là FIERY PATH (%s)' % (rp[:2] if rp else None),
      rp and rp[0] == (0, 27) and app.rom.map_name(*rp[1]) == 'FIERY PATH')
qp = app.q_cv.find_withtag('qpath')
co = app.q_cv.coords(qp[-1]) if qp else []
k = app.q_scale * 16
check('đường tím từ (19,37) tới cửa Fiery Path (11,36)', co and co[:2] == [19 * k + k // 2, 37 * k + k // 2]
      and tuple((c - k // 2) // k for c in co[-2:]) == (11, 36))
app.quest_pick_go((S[mf]['map'], (1, 1), 'thử'))
check('bấm 🧭 một dòng: đường tím đổi theo', app.guide_goal() == (S[mf]['map'], (1, 1), 'thử'))
g.party = real_party

app.q_guide.set(False)
app.quest_home()
app.update()
check('tắt dẫn đường: không vẽ đường tím', not app.q_cv.find_withtag('qpath'))

print('\n%d đúng, %d sai' % (ok, fail))
app.destroy()
sys.exit(1 if fail else 0)
