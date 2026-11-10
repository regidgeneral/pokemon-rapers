"""Sinh tool/mm_quest.py: các bước cốt truyện Emerald (tới Đại sảnh Danh vọng), số cờ/biến + mã map tra từ pokeemerald.
  py -3 dev\\gen_quest.py <thư mục pokeemerald> mm_quest.py
  pokeemerald: git clone -n --depth 1 --filter=blob:none https://github.com/pret/pokeemerald.git rồi sparse-checkout
  include/constants/flags.h, include/constants/vars.h, data/maps/ (đủ cho script này). Sửa bước = sửa danh sách S rồi chạy lại.
  Duy 11/11: mỗi chương = 1 mục tiêu; mỗi bước có điều kiện (HM: đĩa + huy hiệu + con biết chiêu; vật phẩm; số huy hiệu)."""
import json, os, re, sys
PE, OUT = sys.argv[1], sys.argv[2]
C = os.path.join(PE, 'include', 'constants')
defs = {}
for fn in ('flags.h', 'vars.h'):
    for line in open(os.path.join(C, fn), encoding='utf-8'):
        m = re.match(r'#define\s+(\w+)\s+(.+?)\s*(//.*)?$', line)
        if m:
            defs[m.group(1)] = m.group(2)
defs['SYSTEM_FLAGS'] = '0x860'           # flags.h:1348 "(TRAINER_FLAGS_END + 1) // 0x860"


def val(name):
    e = defs[name]
    e = re.sub(r'\b([A-Z_][A-Z0-9_]*)\b', lambda m: str(val(m.group(1))), e)
    return eval(e)


groups = json.load(open(os.path.join(PE, 'data', 'maps', 'map_groups.json')))
gn = {f: (gi, ni) for gi, g in enumerate(groups['group_order']) for ni, f in enumerate(groups[g])}

# HM: tên, mã vật phẩm, mã chiêu, huy hiệu cần để dùng ngoài trận, nơi nhận (map, ô, ai), cờ đã nhận
HMS = {
    'cut': ('HM01 Cut', 339, 15, 1, 'RustboroCity_CuttersHouse', (7, 5), 'ông chặt cây (nhà ở Rustboro)', 'FLAG_RECEIVED_HM_CUT'),
    'fly': ('HM02 Fly', 340, 19, 6, 'Route119', (26, 31), 'rival trên Route 119', 'FLAG_RECEIVED_HM_FLY'),
    'surf': ('HM03 Surf', 341, 57, 5, 'PetalburgCity_WallysHouse', (3, 4), 'bố Wally (Petalburg)', 'FLAG_RECEIVED_HM_SURF'),
    'strength': ('HM04 Strength', 342, 70, 4, 'RusturfTunnel', (23, 5), 'bạn trai Wanda trong Rusturf Tunnel (sau khi đập đá thông hầm)', 'FLAG_RECEIVED_HM_STRENGTH'),
    'flash': ('HM05 Flash', 343, 148, 2, 'GraniteCave_1F', (36, 9), 'người leo núi ở hang Granite', 'FLAG_RECEIVED_HM_FLASH'),
    'rocksmash': ('HM06 Rock Smash', 344, 249, 3, 'MauvilleCity_House1', (4, 4), 'người trong nhà ở Mauville', 'FLAG_RECEIVED_HM_ROCK_SMASH'),
    'waterfall': ('HM07 Waterfall', 345, 127, 8, 'SootopolisCity', (31, 18), 'Wallace ở Sootopolis', 'FLAG_RECEIVED_HM_WATERFALL'),
    'dive': ('HM08 Dive', 346, 291, 7, 'MossdeepCity_StevensHouse', (9, 6), 'Steven ở nhà (Mossdeep)', 'FLAG_RECEIVED_HM_DIVE'),
}
# vật phẩm then chốt: tên, nơi nhận (map, ô, ai)
ITEMS = {
    269: ('Devon Goods', 'RusturfTunnel', (14, 5), 'lấy lại từ lính Team Aqua trong Rusturf Tunnel'),
    274: ('Thư gửi Steven', 'RustboroCity_DevonCorp_3F', (15, 5), 'chủ tịch Devon (Rustboro)'),
    288: ('Devon Scope', 'Route120', (13, 15), 'Steven trên Route 120'),
    375: ('Magma Emblem', 'MtPyre_Summit', (23, 5), 'ông bà cụ trên đỉnh Mt. Pyre'),
    259: ('Mach Bike', 'MauvilleCity_BikeShop', (2, 5), 'ông Rydel, tiệm xe đạp Mauville (chọn Mach Bike)'),
}

# chương (mục tiêu lớn) -> các bước. Bước: map, ô, ai, điều kiện xong, làm gì, ghi chú, nguồn, [badge=n] [needs] [optional] [via]
def st(m, xy, who, done, do, note, src, **kw):
    return dict(m=m, xy=xy, who=who, done=done, do=do, note=note, src=src, **kw)


CH = [
 ('Bắt đầu hành trình', [
  st('Route101', (7, 14), 'túi của GS Birch', ('FLAG_RESCUED_BIRCH',), 'Cứu Giáo sư Birch: mở túi của ông, chọn Pokémon đầu tiên.', '', 'Route101/scripts.inc:218'),
  st('Route103', (10, 3), 'rival', ('FLAG_DEFEATED_RIVAL_ROUTE103',), 'Đánh rival lần đầu.', '', 'Route103 (FLAG_DEFEATED_RIVAL_ROUTE103)'),
  st('LittlerootTown_ProfessorBirchsLab', (6, 4), 'GS Birch', ('FLAG_RECEIVED_POKEDEX_FROM_BIRCH',), 'Về phòng thí nghiệm nhận Pokédex.', '', 'LittlerootTown_ProfessorBirchsLab/scripts.inc:539')]),
 ('Huy hiệu 1 — Roxanne (Rustboro)', [
  st('PetalburgCity_Gym', (4, 2), 'bố Norman', ('VAR_PETALBURG_GYM_STATE', 2), 'Gặp bố ở gym Petalburg, đi cùng Wally bắt Ralts.', '', 'PetalburgCity_Gym/scripts.inc:90'),
  st('RustboroCity_Gym', (5, 2), 'Roxanne', ('FLAG_DEFEATED_RUSTBORO_GYM',), 'Đánh Roxanne.', 'Gym hệ Đá.', 'RustboroCity_Gym/scripts.inc:18', badge=1)]),
 ('Lấy lại Devon Goods', [
  st('RusturfTunnel', (14, 5), 'lính Team Aqua', ('FLAG_RECOVERED_DEVON_GOODS',), 'Đuổi theo lính Team Aqua trong Rusturf Tunnel, lấy lại Devon Goods.', '', 'RusturfTunnel/scripts.inc:322'),
  st('RustboroCity_DevonCorp_3F', (15, 5), 'chủ tịch Stone', ('FLAG_RECEIVED_POKENAV',), 'Gặp chủ tịch Devon: nhận PokéNav + thư gửi Steven.', '', 'RustboroCity_DevonCorp_3F/scripts.inc:54')]),
 ('Huy hiệu 2 — Brawly (Dewford)', [
  st('Route104_MrBrineysHouse', (5, 3), 'ông Briney', ('FLAG_VISITED_DEWFORD_TOWN',), 'Nhờ ông Briney chở thuyền tới Dewford.', '', 'event_scripts.s:645 (VAR_BRINEY_LOCATION)'),
  st('DewfordTown_Gym', (4, 3), 'Brawly', ('FLAG_DEFEATED_DEWFORD_GYM',), 'Đánh Brawly.', 'Gym hệ Giác đấu; gym tối, có Flash thì dễ hơn.', 'DewfordTown_Gym/scripts.inc:150', badge=2)]),
 ('Đưa thư cho Steven', [
  st('GraniteCave_StevensRoom', (7, 8), 'Steven', ('FLAG_DELIVERED_STEVEN_LETTER',), 'Đưa thư cho Steven ở cuối hang Granite.', '', 'GraniteCave_StevensRoom/scripts.inc:10', needs=[('item', 274)])]),
 ('Giao Devon Goods cho Captain Stern (Slateport)', [
  st('DewfordTown', (12, 9), 'ông Briney', ('FLAG_VISITED_SLATEPORT_CITY',), 'Nhờ ông Briney chở tới Slateport.', '', 'DewfordTown/scripts.inc:165'),
  st('SlateportCity_SternsShipyard_1F', (5, 5), 'Dock (thợ đóng tàu)', ('FLAG_DOCK_REJECTED_DEVON_GOODS',), 'Vào xưởng tàu Stern, nói chuyện với Dock.', 'Để hàng lính Team Aqua tránh khỏi cửa bảo tàng.', 'SlateportCity_SternsShipyard_1F/scripts.inc:15-16 (cũng bật FLAG_HIDE_SLATEPORT_CITY_TEAM_AQUA)'),
  st('SlateportCity_OceanicMuseum_2F', (13, 6), 'Captain Stern', ('FLAG_DELIVERED_DEVON_GOODS',), 'Vào bảo tàng tầng 2, giao Devon Goods cho Captain Stern, đánh 2 lính Team Aqua.', '', 'SlateportCity_OceanicMuseum_2F/scripts.inc:72', needs=[('item', 269)])]),
 ('Huy hiệu 3 — Wattson (Mauville)', [
  st('Route110', (34, 56), 'rival', ('VAR_ROUTE110_STATE', 1), 'Rival đón đánh trên Route 110.', '', 'Route110/scripts.inc:470'),
  st('MauvilleCity', (8, 6), 'Wally', ('FLAG_DEFEATED_WALLY_MAUVILLE',), 'Wally thách đấu trước cửa gym Mauville.', '', 'MauvilleCity/scripts.inc:149'),
  st('MauvilleCity_Gym', (5, 2), 'Wattson', ('FLAG_DEFEATED_MAUVILLE_GYM',), 'Đánh Wattson.', 'Gym hệ Điện; hàng rào điện mở bằng công tắc trong gym.', 'MauvilleCity_Gym/scripts.inc:93', badge=3)]),
 ('Chặn Team Magma ở Mt. Chimney', [
  st('MauvilleCity_House1', (4, 4), 'người tặng HM', ('FLAG_RECEIVED_HM_ROCK_SMASH',), 'Nhận HM06 Rock Smash.', 'Đá chắn đường ở Route 111 (ô 18,101) phải đập mới qua được.', 'MauvilleCity_House1/scripts.inc:10'),
  st('MeteorFalls_1F_1R', (14, 18), 'Team Magma', ('VAR_METEOR_FALLS_STATE', 1), 'Tới Meteor Falls xem Team Magma cướp thiên thạch (sau đó Magma rút khỏi cáp treo Route 112).', 'Đường đi qua Route 111, Fiery Path, Fallarbor.', 'MeteorFalls_1F_1R/scripts.inc:81', needs=[('hm', 'rocksmash')]),
  st('MtChimney', (13, 6), 'Maxie', ('FLAG_DEFEATED_EVIL_TEAM_MT_CHIMNEY',), 'Đi cáp treo lên đỉnh Mt. Chimney, đánh Maxie.', 'Cáp treo ở nhà ga Route 112.', 'MtChimney/scripts.inc:64', via=('Route112_CableCarStation', (6, 6)))]),
 ('Huy hiệu 4 — Flannery (Lavaridge)', [
  st('LavaridgeTown_Gym_1F', (13, 9), 'Flannery', ('FLAG_DEFEATED_LAVARIDGE_GYM',), 'Đánh Flannery.', 'Gym hệ Lửa. Từ đỉnh Mt. Chimney đi xuống Jagged Pass là tới Lavaridge.', 'LavaridgeTown_Gym_1F/scripts.inc:61', badge=4)]),
 ('Huy hiệu 5 — Norman (Petalburg)', [
  st('PetalburgCity_Gym', (4, 2), 'Norman', ('FLAG_DEFEATED_PETALBURG_GYM',), 'Đánh bố Norman.', 'Gym hệ Thường.', 'PetalburgCity_Gym/scripts.inc:367', badge=5, needs=[('badges', 4)]),
  st('PetalburgCity_WallysHouse', (3, 4), 'bố Wally', ('FLAG_RECEIVED_HM_SURF',), 'Nhận HM03 Surf từ bố Wally.', '', 'PetalburgCity_WallysHouse/scripts.inc:23')]),
 ('Viện Thời tiết + HM Fly (Route 119)', [
  st('Route119_WeatherInstitute_2F', (4, 6), 'Shelly (Team Aqua)', ('FLAG_RECEIVED_CASTFORM',), 'Đuổi Team Aqua khỏi Viện Thời tiết, nhận Castform.', '', 'Route119_WeatherInstitute_2F/scripts.inc:119', needs=[('hm', 'surf')]),
  st('Route119', (26, 31), 'rival', ('FLAG_RECEIVED_HM_FLY',), 'Rival đánh rồi cho HM02 Fly.', '', 'Route119/scripts.inc:131', needs=[('hm', 'surf')])]),
 ('Huy hiệu 6 — Winona (Fortree)', [
  st('Route120', (13, 15), 'Steven', ('FLAG_RECEIVED_DEVON_SCOPE',), 'Steven cho Devon Scope.', 'Để thấy Kecleon tàng hình chặn gym Fortree.', 'Route120/scripts.inc:216'),
  st('FortreeCity_Gym', (15, 2), 'Winona', ('FLAG_DEFEATED_FORTREE_GYM',), 'Đánh Winona.', 'Gym hệ Bay.', 'FortreeCity_Gym/scripts.inc:33', badge=6, needs=[('item', 288)])]),
 ('Team Aqua & Team Magma: Orb, căn cứ, tàu ngầm', [
  st('MtPyre_Summit', (23, 5), 'ông bà cụ', ('FLAG_RECEIVED_RED_OR_BLUE_ORB',), 'Lên đỉnh Mt. Pyre: Team Aqua cướp Red Orb; ông bà cụ đưa Magma Emblem.', '', 'MtPyre_Summit/scripts.inc:59', needs=[('hm', 'surf')]),
  st('MagmaHideout_4F', (16, 21), 'Maxie', ('VAR_SLATEPORT_CITY_STATE', 1), 'Vào căn cứ Team Magma, đánh Maxie (Groudon thức dậy).', 'Cửa căn cứ ở Jagged Pass.', 'MagmaHideout_4F/scripts.inc:55', needs=[('item', 375)]),
  st('SlateportCity_Harbor', (8, 10), 'Archie', ('VAR_SLATEPORT_CITY_STATE', 2), 'Tới cảng Slateport: Team Aqua cướp tàu ngầm.', '', 'SlateportCity/scripts.inc:567'),
  st('AquaHideout_B2F', (23, 19), 'Matt (Team Aqua)', ('FLAG_TEAM_AQUA_ESCAPED_IN_SUBMARINE',), 'Vào căn cứ Team Aqua (Lilycove), đánh Matt.', '', 'AquaHideout_B2F/scripts.inc:44', needs=[('hm', 'surf')])]),
 ('Huy hiệu 7 — Tate & Liza (Mossdeep)', [
  st('MossdeepCity_Gym', (23, 7), 'Tate & Liza', ('FLAG_DEFEATED_MOSSDEEP_GYM',), 'Đánh Tate & Liza (đấu đôi).', 'Gym hệ Siêu linh.', 'MossdeepCity_Gym/scripts.inc:65', badge=7, needs=[('hm', 'surf')]),
  st('MossdeepCity_SpaceCenter_2F', (1, 8), 'Steven', ('FLAG_DEFEATED_MAGMA_SPACE_CENTER',), 'Cùng Steven đánh Maxie & Tabitha ở Trung tâm Vũ trụ.', '', 'MossdeepCity_SpaceCenter_2F/scripts.inc:283'),
  st('MossdeepCity_StevensHouse', (9, 6), 'Steven', ('FLAG_RECEIVED_HM_DIVE',), 'Nhận HM08 Dive từ Steven.', '', 'MossdeepCity_StevensHouse/scripts.inc:37')]),
 ('Kyogre và Groudon thức dậy', [
  st('SeafloorCavern_Room9', (17, 42), 'Archie', ('FLAG_KYOGRE_ESCAPED_SEAFLOOR_CAVERN',), 'Lặn xuống Seafloor Cavern (Route 128), đánh Archie.', '', 'SeafloorCavern_Room9/scripts.inc:114', needs=[('hm', 'dive'), ('hm', 'strength'), ('hm', 'rocksmash')]),
  st('SootopolisCity', (20, 36), 'Steven', ('VAR_SOOTOPOLIS_CITY_STATE', 2), 'Vào Sootopolis xem Groudon và Kyogre đánh nhau.', 'Lặn ở Route 126 để vào thành phố.', 'SootopolisCity/scripts.inc:242', needs=[('hm', 'dive')]),
  st('CaveOfOrigin_B1F', (9, 13), 'Wallace', ('FLAG_WALLACE_GOES_TO_SKY_PILLAR',), 'Gặp Wallace trong Cave of Origin.', '', 'CaveOfOrigin_B1F/scripts.inc:50'),
  st('SkyPillar_Top', (14, 9), 'Rayquaza', ('VAR_SOOTOPOLIS_CITY_STATE', 5), 'Leo Sky Pillar đánh thức Rayquaza.', 'Sàn nứt phải chạy Mach Bike qua.', 'SkyPillar_Top/scripts.inc:121', needs=[('hm', 'surf'), ('item', 259)])]),
 ('Huy hiệu 8 — Juan (Sootopolis)', [
  st('SootopolisCity_Gym_1F', (8, 2), 'Juan', ('FLAG_DEFEATED_SOOTOPOLIS_GYM',), 'Đánh Juan.', 'Gym hệ Nước.', 'SootopolisCity_Gym_1F/scripts.inc:96', badge=8, needs=[('hm', 'dive')]),
  st('SootopolisCity', (31, 18), 'Wallace', ('FLAG_RECEIVED_HM_WATERFALL',), 'Wallace cho HM07 Waterfall.', '', 'SootopolisCity/scripts.inc:1261')]),
 ('Liên đoàn Pokémon (Ever Grande)', [
  st('VictoryRoad_1F', (3, 23), 'Wally', ('FLAG_DEFEATED_WALLY_VICTORY_ROAD',), 'Wally chặn ở lối vào Victory Road.', '', 'VictoryRoad_1F/scripts.inc:43', needs=[('hm', 'surf'), ('hm', 'waterfall')]),
  st('EverGrandeCity_SidneysRoom', (6, 5), 'Tứ Thiên Vương', ('FLAG_DEFEATED_ELITE_4_DRAKE',), 'Đánh liền 4 người: Sidney, Phoebe, Glacia, Drake.', 'Victory Road cần Strength + Rock Smash.', 'EverGrandeCity_DrakesRoom/scripts.inc:58', needs=[('hm', 'strength'), ('hm', 'rocksmash')]),
  st('EverGrandeCity_ChampionsRoom', (6, 5), 'Wallace', ('FLAG_SYS_GAME_CLEAR',), 'Đánh Nhà vô địch Wallace, vào Đại sảnh Danh vọng.', '', 'EverGrandeCity_HallOfFame/scripts.inc:45')]),
]


def cond(c):
    return "('f', 0x%03X)" % val(c[0]) if len(c) == 1 else "('v', 0x%04X, %d)" % (val(c[0]), c[1])


L = ['"""Các bước cốt truyện Pokémon Emerald tới Đại sảnh Danh vọng (SINH bằng dev/gen_quest.py từ pokeemerald, đừng sửa tay).',
     'Mỗi bước: map đích (nhóm, số), ô NPC/điểm kích hoạt, điều kiện xong (cờ, hoặc biến >= giá trị), làm gì, ghi chú, nguồn,',
     'chương (mục tiêu lớn), huy hiệu (bước gym), needs = điều kiện trước: ("hm", tên) / ("item", mã) / ("badges", số)."""', '',
     '# tên, mã vật phẩm, mã chiêu, huy hiệu cần để dùng ngoài trận, nơi nhận (map, ô, ai), cờ đã nhận',
     'HMS = {']
for k, (name, it, mv, bd, m, xy, who, fl) in HMS.items():
    L.append('    %r: dict(name=%r, item=%d, move=%d, badge=%d, map=%r, xy=%r, who=%r, got=0x%03X),'
             % (k, name, it, mv, bd, gn[m], xy, who, val(fl)))
L += ['}', 'ITEMS = {']
for it, (name, m, xy, who) in ITEMS.items():
    L.append('    %d: dict(name=%r, map=%r, xy=%r, who=%r),' % (it, name, gn[m], xy, who))
L += ['}', '', 'STEPS = [']
n = 0
for goal, steps in CH:
    for s in steps:
        n += 1
        extra = ''
        for k in ('badge', 'needs', 'optional'):
            if k in s:
                extra += ', %s=%r' % (k, s[k])
        if 'via' in s:
            extra += ', via=(%r, %r)' % (gn[s['via'][0]], s['via'][1])
        L.append('    dict(goal=%r, map=%r, xy=%r, who=%r, done=%s,  # %d. %s' % (goal, gn[s['m']], s['xy'], s['who'], cond(s['done']), n,
                                                                          ' '.join(map(str, s['done']))))
        L.append('         do=%r, need=%r, src=%r%s),' % (s['do'], s['note'], s['src'], extra))
L += [']', '', '',
      'def progress(flag, var):',
      '    """[(bước, đã xong)] và chỉ số bước hiện tại (None = xong hết). Bước hiện tại = bước bắt buộc đầu tiên chưa xong',
      '    đứng SAU bước xong cuối cùng (làm khác thứ tự / bỏ bước tuỳ chọn vẫn chỉ đúng)."""',
      '    done = [(flag(s["done"][1]) if s["done"][0] == "f" else (var(s["done"][1]) or 0) >= s["done"][2]) for s in STEPS]',
      '    last = max((i for i, d in enumerate(done) if d), default=-1)',
      '    cur = next((i for i in range(last + 1, len(STEPS)) if not done[i] and not STEPS[i].get("optional")), None)',
      '    return list(zip(STEPS, done)), cur',
      '',
      '',
      'def badge_step(n):',
      '    """Bước gym cho huy hiệu n (1..8)."""',
      '    return next(s for s in STEPS if s.get("badge") == n)',
      '']
open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
print('ok', n, 'bước,', len(CH), 'chương')
