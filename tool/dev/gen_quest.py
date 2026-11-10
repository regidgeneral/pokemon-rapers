"""Sinh tool/mm_quest.py: các bước cốt truyện Emerald (tới Đại sảnh Danh vọng), số cờ/biến + mã map tra từ pokeemerald.
  py -3 dev\\gen_quest.py <thư mục pokeemerald> mm_quest.py
  pokeemerald: git clone -n --depth 1 --filter=blob:none https://github.com/pret/pokeemerald.git rồi sparse-checkout
  include/constants/flags.h, include/constants/vars.h, data/maps/ (đủ cho script này). Sửa bước = sửa danh sách S rồi chạy lại."""
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

# (map thư mục, (x, y), ai/cái gì, điều kiện xong, làm gì, cần gì, nguồn, tuỳ chọn, đi qua)
S = [
 ('Route101', (7, 14), 'túi của GS Birch', ('FLAG_RESCUED_BIRCH',), 'Cứu Giáo sư Birch: mở túi của ông, chọn Pokémon đầu tiên.', '', 'Route101/scripts.inc:218'),
 ('Route103', (10, 3), 'rival', ('FLAG_DEFEATED_RIVAL_ROUTE103',), 'Đánh rival lần đầu.', '', 'Route103 (FLAG_DEFEATED_RIVAL_ROUTE103)'),
 ('LittlerootTown_ProfessorBirchsLab', (6, 4), 'GS Birch', ('FLAG_RECEIVED_POKEDEX_FROM_BIRCH',), 'Về phòng thí nghiệm nhận Pokédex.', '', 'LittlerootTown_ProfessorBirchsLab/scripts.inc:539'),
 ('PetalburgCity_Gym', (4, 2), 'bố Norman', ('VAR_PETALBURG_GYM_STATE', 2), 'Gặp bố ở gym, đi cùng Wally bắt Ralts.', '', 'PetalburgCity_Gym/scripts.inc:90'),
 ('RustboroCity_Gym', (5, 2), 'Roxanne', ('FLAG_DEFEATED_RUSTBORO_GYM',), 'Huy hiệu 1: đánh Roxanne.', 'Gym hệ Đá.', 'RustboroCity_Gym/scripts.inc:18'),
 ('RusturfTunnel', (14, 5), 'lính Team Aqua', ('FLAG_RECOVERED_DEVON_GOODS',), 'Đuổi theo lính Team Aqua, lấy lại Devon Goods.', '', 'RusturfTunnel/scripts.inc:322'),
 ('RustboroCity_DevonCorp_3F', (15, 5), 'chủ tịch Stone', ('FLAG_RECEIVED_POKENAV',), 'Gặp chủ tịch Devon: nhận PokéNav + thư gửi Steven.', '', 'RustboroCity_DevonCorp_3F/scripts.inc:54'),
 ('Route104_MrBrineysHouse', (5, 3), 'ông Briney', ('FLAG_VISITED_DEWFORD_TOWN',), 'Nhờ ông Briney chở thuyền tới Dewford.', '', 'event_scripts.s:645 (VAR_BRINEY_LOCATION)'),
 ('DewfordTown_Gym', (4, 3), 'Brawly', ('FLAG_DEFEATED_DEWFORD_GYM',), 'Huy hiệu 2: đánh Brawly.', 'Gym hệ Giác đấu; gym tối, có HM05 Flash thì dễ hơn.', 'DewfordTown_Gym/scripts.inc:150'),
 ('GraniteCave_StevensRoom', (7, 8), 'Steven', ('FLAG_DELIVERED_STEVEN_LETTER',), 'Đưa thư cho Steven ở cuối hang Granite.', 'Thư của chủ tịch Devon.', 'GraniteCave_StevensRoom/scripts.inc:10'),
 ('DewfordTown', (12, 9), 'ông Briney', ('FLAG_VISITED_SLATEPORT_CITY',), 'Nhờ ông Briney chở tới Slateport.', '', 'DewfordTown/scripts.inc:165'),
 ('SlateportCity_SternsShipyard_1F', (5, 5), 'Dock (thợ đóng tàu)', ('FLAG_DOCK_REJECTED_DEVON_GOODS',), 'Vào xưởng tàu của Captain Stern, nói chuyện với Dock: biết Stern đang ở bảo tàng; hàng lính Team Aqua chắn cửa bảo tàng rút đi.', 'Devon Goods trong túi.', 'SlateportCity_SternsShipyard_1F/scripts.inc:15-16 (cũng bật FLAG_HIDE_SLATEPORT_CITY_TEAM_AQUA)'),
 ('SlateportCity_OceanicMuseum_2F', (13, 6), 'Captain Stern', ('FLAG_DELIVERED_DEVON_GOODS',), 'Giao Devon Goods cho Captain Stern; đánh 2 lính Team Aqua xông vào.', 'Devon Goods trong túi.', 'SlateportCity_OceanicMuseum_2F/scripts.inc:72'),
 ('Route110', (34, 56), 'rival', ('VAR_ROUTE110_STATE', 1), 'Rival đón đánh trên Route 110.', '', 'Route110/scripts.inc:470'),
 ('MauvilleCity', (8, 6), 'Wally', ('FLAG_DEFEATED_WALLY_MAUVILLE',), 'Wally thách đấu trước cửa gym.', '', 'MauvilleCity/scripts.inc:149'),
 ('MauvilleCity_Gym', (5, 2), 'Wattson', ('FLAG_DEFEATED_MAUVILLE_GYM',), 'Huy hiệu 3: đánh Wattson.', 'Gym hệ Điện.', 'MauvilleCity_Gym/scripts.inc:93'),
 ('MauvilleCity_House1', (4, 4), 'người tặng HM', ('FLAG_RECEIVED_HM_ROCK_SMASH',), 'Nhận HM06 Rock Smash.', '', 'MauvilleCity_House1/scripts.inc:10', True),
 ('MeteorFalls_1F_1R', (14, 18), 'Team Magma', ('VAR_METEOR_FALLS_STATE', 1), 'Xem Team Magma cướp thiên thạch ở Meteor Falls (Magma đang chặn cáp treo Route 112 sẽ rút đi).', 'Đường tới đi qua Fiery Path, Fallarbor.', 'MeteorFalls_1F_1R/scripts.inc:81'),
 ('MtChimney', (13, 6), 'Maxie', ('FLAG_DEFEATED_EVIL_TEAM_MT_CHIMNEY',), 'Lên đỉnh Mt. Chimney bằng cáp treo, đánh Maxie.', 'Cáp treo ở nhà ga Route 112.', 'MtChimney/scripts.inc:64', False, ('Route112_CableCarStation', (6, 6))),
 ('LavaridgeTown_Gym_1F', (13, 9), 'Flannery', ('FLAG_DEFEATED_LAVARIDGE_GYM',), 'Huy hiệu 4: đánh Flannery.', 'Gym hệ Lửa.', 'LavaridgeTown_Gym_1F/scripts.inc:61'),
 ('PetalburgCity_Gym', (4, 2), 'Norman', ('FLAG_DEFEATED_PETALBURG_GYM',), 'Huy hiệu 5: đánh bố Norman.', 'Gym hệ Thường; cần 4 huy hiệu.', 'PetalburgCity_Gym/scripts.inc:367'),
 ('PetalburgCity_WallysHouse', (3, 4), 'bố Wally', ('FLAG_RECEIVED_HM_SURF',), 'Nhận HM03 Surf từ bố Wally.', '', 'PetalburgCity_WallysHouse/scripts.inc:23'),
 ('Route119_WeatherInstitute_2F', (4, 6), 'Shelly (Team Aqua)', ('FLAG_RECEIVED_CASTFORM',), 'Đuổi Team Aqua khỏi Viện Thời tiết, nhận Castform.', 'Cần Surf để qua Route 118.', 'Route119_WeatherInstitute_2F/scripts.inc:119'),
 ('Route119', (26, 31), 'rival', ('FLAG_RECEIVED_HM_FLY',), 'Rival đánh rồi cho HM02 Fly.', '', 'Route119/scripts.inc:131'),
 ('Route120', (13, 15), 'Steven', ('FLAG_RECEIVED_DEVON_SCOPE',), 'Steven cho Devon Scope (để thấy Kecleon tàng hình chặn gym Fortree).', '', 'Route120/scripts.inc:216'),
 ('FortreeCity_Gym', (15, 2), 'Winona', ('FLAG_DEFEATED_FORTREE_GYM',), 'Huy hiệu 6: đánh Winona.', 'Gym hệ Bay; Kecleon chặn cửa thì dùng Devon Scope.', 'FortreeCity_Gym/scripts.inc:33'),
 ('MtPyre_Summit', (23, 5), 'ông bà cụ', ('FLAG_RECEIVED_RED_OR_BLUE_ORB',), 'Lên đỉnh Mt. Pyre: Team Aqua cướp Red Orb, ông bà cụ đưa Magma Emblem.', '', 'MtPyre_Summit/scripts.inc:59'),
 ('MagmaHideout_4F', (16, 21), 'Maxie', ('VAR_SLATEPORT_CITY_STATE', 1), 'Vào căn cứ Team Magma, đánh Maxie (Groudon thức dậy).', 'Magma Emblem; cửa căn cứ ở Jagged Pass.', 'MagmaHideout_4F/scripts.inc:55'),
 ('SlateportCity_Harbor', (8, 10), 'Archie', ('VAR_SLATEPORT_CITY_STATE', 2), 'Team Aqua cướp tàu ngầm ở cảng Slateport.', '', 'SlateportCity/scripts.inc:567'),
 ('AquaHideout_B2F', (23, 19), 'Matt (Team Aqua)', ('FLAG_TEAM_AQUA_ESCAPED_IN_SUBMARINE',), 'Vào căn cứ Team Aqua (Lilycove), đánh Matt.', 'Cần Surf để tới cửa căn cứ.', 'AquaHideout_B2F/scripts.inc:44'),
 ('MossdeepCity_Gym', (23, 7), 'Tate & Liza', ('FLAG_DEFEATED_MOSSDEEP_GYM',), 'Huy hiệu 7: đánh Tate & Liza (đấu đôi).', 'Gym hệ Siêu linh.', 'MossdeepCity_Gym/scripts.inc:65'),
 ('MossdeepCity_SpaceCenter_2F', (1, 8), 'Steven', ('FLAG_DEFEATED_MAGMA_SPACE_CENTER',), 'Cùng Steven đánh Maxie & Tabitha ở Trung tâm Vũ trụ.', '', 'MossdeepCity_SpaceCenter_2F/scripts.inc:283'),
 ('MossdeepCity_StevensHouse', (9, 6), 'Steven', ('FLAG_RECEIVED_HM_DIVE',), 'Nhận HM08 Dive từ Steven.', '', 'MossdeepCity_StevensHouse/scripts.inc:37'),
 ('SeafloorCavern_Room9', (17, 42), 'Archie', ('FLAG_KYOGRE_ESCAPED_SEAFLOOR_CAVERN',), 'Lặn xuống Seafloor Cavern (Route 128), đánh Archie; Kyogre thức dậy.', 'Dive + Strength + Rock Smash.', 'SeafloorCavern_Room9/scripts.inc:114'),
 ('SootopolisCity', (20, 36), 'Steven', ('VAR_SOOTOPOLIS_CITY_STATE', 2), 'Vào Sootopolis xem Groudon và Kyogre đánh nhau.', 'Lặn (Dive) ở Route 126 để vào thành phố.', 'SootopolisCity/scripts.inc:242'),
 ('CaveOfOrigin_B1F', (9, 13), 'Wallace', ('FLAG_WALLACE_GOES_TO_SKY_PILLAR',), 'Gặp Wallace trong Cave of Origin.', '', 'CaveOfOrigin_B1F/scripts.inc:50'),
 ('SkyPillar_Top', (14, 9), 'Rayquaza', ('VAR_SOOTOPOLIS_CITY_STATE', 5), 'Leo Sky Pillar đánh thức Rayquaza.', 'Mach Bike để qua sàn nứt.', 'SkyPillar_Top/scripts.inc:121'),
 ('SootopolisCity_Gym_1F', (8, 2), 'Juan', ('FLAG_DEFEATED_SOOTOPOLIS_GYM',), 'Huy hiệu 8: đánh Juan.', 'Gym hệ Nước.', 'SootopolisCity_Gym_1F/scripts.inc:96'),
 ('SootopolisCity', (31, 18), 'Wallace', ('FLAG_RECEIVED_HM_WATERFALL',), 'Wallace cho HM07 Waterfall.', '', 'SootopolisCity/scripts.inc:1261'),
 ('VictoryRoad_1F', (3, 23), 'Wally', ('FLAG_DEFEATED_WALLY_VICTORY_ROAD',), 'Wally chặn ở lối vào Victory Road.', 'Waterfall để tới Ever Grande.', 'VictoryRoad_1F/scripts.inc:43'),
 ('EverGrandeCity_SidneysRoom', (6, 5), 'Tứ Thiên Vương', ('FLAG_DEFEATED_ELITE_4_DRAKE',), 'Đánh liền 4 người: Sidney, Phoebe, Glacia, Drake.', '', 'EverGrandeCity_DrakesRoom/scripts.inc:58'),
 ('EverGrandeCity_ChampionsRoom', (6, 5), 'Wallace', ('FLAG_SYS_GAME_CLEAR',), 'Đánh Nhà vô địch Wallace, vào Đại sảnh Danh vọng.', '', 'EverGrandeCity_HallOfFame/scripts.inc:45'),
]

lines = ['"""Các bước cốt truyện Pokémon Emerald tới Đại sảnh Danh vọng (sinh tự động 11/11 từ pokeemerald: flags.h, vars.h,',
         'data/maps/map_groups.json, map.json, scripts.inc). Mỗi bước: map đích (nhóm, số), ô NPC/điểm kích hoạt, điều kiện xong',
         '(cờ, hoặc biến >= giá trị), làm gì, cần gì, nguồn. Không chỉ hướng đi: đường đi do tool tìm và vẽ trên bản đồ."""', '',
         'STEPS = [']
for s in S:
    folder, xy, who, cond, do, need, src = s[:7]
    opt = s[7] if len(s) > 7 else False
    via = s[8] if len(s) > 8 else None
    if len(cond) == 1:
        c = "('f', 0x%03X)" % val(cond[0])
    else:
        c = "('v', 0x%04X, %d)" % (val(cond[0]), cond[1])
    v = ', via=(%r, %r)' % (gn[via[0]], via[1]) if via else ''
    lines.append('    dict(map=%r, xy=%r, who=%r, done=%s,  # %s' % (gn[folder], xy, who, c, ' '.join(map(str, cond))))
    lines.append('         do=%r,' % do)
    lines.append('         need=%r, src=%r%s%s),' % (need, src, ', optional=True' if opt else '', v))
lines += [']', '', '',
          'def progress(flag, var):',
          '    """[(bước, đã xong)] và chỉ số bước hiện tại (None = xong hết). Bước hiện tại = bước bắt buộc đầu tiên chưa xong',
          '    đứng SAU bước xong cuối cùng (làm khác thứ tự / bỏ bước tuỳ chọn vẫn chỉ đúng)."""',
          '    done = [(flag(s["done"][1]) if s["done"][0] == "f" else (var(s["done"][1]) or 0) >= s["done"][2]) for s in STEPS]',
          '    last = max((i for i, d in enumerate(done) if d), default=-1)',
          '    cur = next((i for i in range(last + 1, len(STEPS)) if not done[i] and not STEPS[i].get("optional")), None)',
          '    return list(zip(STEPS, done)), cur',
          '']
open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print('ok', len(S), 'bước')
