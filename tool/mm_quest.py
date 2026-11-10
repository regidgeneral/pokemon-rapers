"""Các bước cốt truyện Pokémon Emerald tới Đại sảnh Danh vọng (sinh tự động 11/11 từ pokeemerald: flags.h, vars.h,
data/maps/map_groups.json, map.json, scripts.inc). Mỗi bước: map đích (nhóm, số), ô NPC/điểm kích hoạt, điều kiện xong
(cờ, hoặc biến >= giá trị), làm gì, cần gì, nguồn. Không chỉ hướng đi: đường đi do tool tìm và vẽ trên bản đồ."""

STEPS = [
    dict(map=(0, 16), xy=(7, 14), who='túi của GS Birch', done=('f', 0x052),  # FLAG_RESCUED_BIRCH
         do='Cứu Giáo sư Birch: mở túi của ông, chọn Pokémon đầu tiên.',
         need='', src='Route101/scripts.inc:218'),
    dict(map=(0, 18), xy=(10, 3), who='rival', done=('f', 0x082),  # FLAG_DEFEATED_RIVAL_ROUTE103
         do='Đánh rival lần đầu.',
         need='', src='Route103 (FLAG_DEFEATED_RIVAL_ROUTE103)'),
    dict(map=(1, 4), xy=(6, 4), who='GS Birch', done=('f', 0x8E4),  # FLAG_RECEIVED_POKEDEX_FROM_BIRCH
         do='Về phòng thí nghiệm nhận Pokédex.',
         need='', src='LittlerootTown_ProfessorBirchsLab/scripts.inc:539'),
    dict(map=(8, 1), xy=(4, 2), who='bố Norman', done=('v', 0x4085, 2),  # VAR_PETALBURG_GYM_STATE 2
         do='Gặp bố ở gym, đi cùng Wally bắt Ralts.',
         need='', src='PetalburgCity_Gym/scripts.inc:90'),
    dict(map=(11, 3), xy=(5, 2), who='Roxanne', done=('f', 0x4F0),  # FLAG_DEFEATED_RUSTBORO_GYM
         do='Huy hiệu 1: đánh Roxanne.',
         need='Gym hệ Đá.', src='RustboroCity_Gym/scripts.inc:18'),
    dict(map=(24, 4), xy=(14, 5), who='lính Team Aqua', done=('f', 0x08F),  # FLAG_RECOVERED_DEVON_GOODS
         do='Đuổi theo lính Team Aqua, lấy lại Devon Goods.',
         need='', src='RusturfTunnel/scripts.inc:322'),
    dict(map=(11, 2), xy=(15, 5), who='chủ tịch Stone', done=('f', 0x0BC),  # FLAG_RECEIVED_POKENAV
         do='Gặp chủ tịch Devon: nhận PokéNav + thư gửi Steven.',
         need='', src='RustboroCity_DevonCorp_3F/scripts.inc:54'),
    dict(map=(17, 0), xy=(5, 3), who='ông Briney', done=('f', 0x871),  # FLAG_VISITED_DEWFORD_TOWN
         do='Nhờ ông Briney chở thuyền tới Dewford.',
         need='', src='event_scripts.s:645 (VAR_BRINEY_LOCATION)'),
    dict(map=(3, 3), xy=(4, 3), who='Brawly', done=('f', 0x4F1),  # FLAG_DEFEATED_DEWFORD_GYM
         do='Huy hiệu 2: đánh Brawly.',
         need='Gym hệ Giác đấu; gym tối, có HM05 Flash thì dễ hơn.', src='DewfordTown_Gym/scripts.inc:150'),
    dict(map=(24, 10), xy=(7, 8), who='Steven', done=('f', 0x0BD),  # FLAG_DELIVERED_STEVEN_LETTER
         do='Đưa thư cho Steven ở cuối hang Granite.',
         need='Thư của chủ tịch Devon.', src='GraniteCave_StevensRoom/scripts.inc:10'),
    dict(map=(0, 11), xy=(12, 9), who='ông Briney', done=('f', 0x877),  # FLAG_VISITED_SLATEPORT_CITY
         do='Nhờ ông Briney chở tới Slateport.',
         need='', src='DewfordTown/scripts.inc:165'),
    dict(map=(9, 0), xy=(5, 5), who='Dock (thợ đóng tàu)', done=('f', 0x094),  # FLAG_DOCK_REJECTED_DEVON_GOODS
         do='Vào xưởng tàu của Captain Stern, nói chuyện với Dock: biết Stern đang ở bảo tàng; hàng lính Team Aqua chắn cửa bảo tàng rút đi.',
         need='Devon Goods trong túi.', src='SlateportCity_SternsShipyard_1F/scripts.inc:15-16 (cũng bật FLAG_HIDE_SLATEPORT_CITY_TEAM_AQUA)'),
    dict(map=(9, 8), xy=(13, 6), who='Captain Stern', done=('f', 0x095),  # FLAG_DELIVERED_DEVON_GOODS
         do='Giao Devon Goods cho Captain Stern; đánh 2 lính Team Aqua xông vào.',
         need='Devon Goods trong túi.', src='SlateportCity_OceanicMuseum_2F/scripts.inc:72'),
    dict(map=(0, 25), xy=(34, 56), who='rival', done=('v', 0x4069, 1),  # VAR_ROUTE110_STATE 1
         do='Rival đón đánh trên Route 110.',
         need='', src='Route110/scripts.inc:470'),
    dict(map=(0, 2), xy=(8, 6), who='Wally', done=('f', 0x0BE),  # FLAG_DEFEATED_WALLY_MAUVILLE
         do='Wally thách đấu trước cửa gym.',
         need='', src='MauvilleCity/scripts.inc:149'),
    dict(map=(10, 0), xy=(5, 2), who='Wattson', done=('f', 0x4F2),  # FLAG_DEFEATED_MAUVILLE_GYM
         do='Huy hiệu 3: đánh Wattson.',
         need='Gym hệ Điện.', src='MauvilleCity_Gym/scripts.inc:93'),
    dict(map=(10, 2), xy=(4, 4), who='người tặng HM', done=('f', 0x06B),  # FLAG_RECEIVED_HM_ROCK_SMASH
         do='Nhận HM06 Rock Smash.',
         need='', src='MauvilleCity_House1/scripts.inc:10', optional=True),
    dict(map=(24, 0), xy=(14, 18), who='Team Magma', done=('v', 0x40BF, 1),  # VAR_METEOR_FALLS_STATE 1
         do='Xem Team Magma cướp thiên thạch ở Meteor Falls (Magma đang chặn cáp treo Route 112 sẽ rút đi).',
         need='Đường tới đi qua Fiery Path, Fallarbor.', src='MeteorFalls_1F_1R/scripts.inc:81'),
    dict(map=(24, 12), xy=(13, 6), who='Maxie', done=('f', 0x08B),  # FLAG_DEFEATED_EVIL_TEAM_MT_CHIMNEY
         do='Lên đỉnh Mt. Chimney bằng cáp treo, đánh Maxie.',
         need='Cáp treo ở nhà ga Route 112.', src='MtChimney/scripts.inc:64', via=((19, 0), (6, 6))),
    dict(map=(4, 1), xy=(13, 9), who='Flannery', done=('f', 0x4F3),  # FLAG_DEFEATED_LAVARIDGE_GYM
         do='Huy hiệu 4: đánh Flannery.',
         need='Gym hệ Lửa.', src='LavaridgeTown_Gym_1F/scripts.inc:61'),
    dict(map=(8, 1), xy=(4, 2), who='Norman', done=('f', 0x4F4),  # FLAG_DEFEATED_PETALBURG_GYM
         do='Huy hiệu 5: đánh bố Norman.',
         need='Gym hệ Thường; cần 4 huy hiệu.', src='PetalburgCity_Gym/scripts.inc:367'),
    dict(map=(8, 0), xy=(3, 4), who='bố Wally', done=('f', 0x07A),  # FLAG_RECEIVED_HM_SURF
         do='Nhận HM03 Surf từ bố Wally.',
         need='', src='PetalburgCity_WallysHouse/scripts.inc:23'),
    dict(map=(32, 1), xy=(4, 6), who='Shelly (Team Aqua)', done=('f', 0x097),  # FLAG_RECEIVED_CASTFORM
         do='Đuổi Team Aqua khỏi Viện Thời tiết, nhận Castform.',
         need='Cần Surf để qua Route 118.', src='Route119_WeatherInstitute_2F/scripts.inc:119'),
    dict(map=(0, 34), xy=(26, 31), who='rival', done=('f', 0x06E),  # FLAG_RECEIVED_HM_FLY
         do='Rival đánh rồi cho HM02 Fly.',
         need='', src='Route119/scripts.inc:131'),
    dict(map=(0, 35), xy=(13, 15), who='Steven', done=('f', 0x11D),  # FLAG_RECEIVED_DEVON_SCOPE
         do='Steven cho Devon Scope (để thấy Kecleon tàng hình chặn gym Fortree).',
         need='', src='Route120/scripts.inc:216'),
    dict(map=(12, 1), xy=(15, 2), who='Winona', done=('f', 0x4F5),  # FLAG_DEFEATED_FORTREE_GYM
         do='Huy hiệu 6: đánh Winona.',
         need='Gym hệ Bay; Kecleon chặn cửa thì dùng Devon Scope.', src='FortreeCity_Gym/scripts.inc:33'),
    dict(map=(24, 22), xy=(23, 5), who='ông bà cụ', done=('f', 0x0D4),  # FLAG_RECEIVED_RED_OR_BLUE_ORB
         do='Lên đỉnh Mt. Pyre: Team Aqua cướp Red Orb, ông bà cụ đưa Magma Emblem.',
         need='', src='MtPyre_Summit/scripts.inc:59'),
    dict(map=(24, 91), xy=(16, 21), who='Maxie', done=('v', 0x4058, 1),  # VAR_SLATEPORT_CITY_STATE 1
         do='Vào căn cứ Team Magma, đánh Maxie (Groudon thức dậy).',
         need='Magma Emblem; cửa căn cứ ở Jagged Pass.', src='MagmaHideout_4F/scripts.inc:55'),
    dict(map=(9, 9), xy=(8, 10), who='Archie', done=('v', 0x4058, 2),  # VAR_SLATEPORT_CITY_STATE 2
         do='Team Aqua cướp tàu ngầm ở cảng Slateport.',
         need='', src='SlateportCity/scripts.inc:567'),
    dict(map=(24, 25), xy=(23, 19), who='Matt (Team Aqua)', done=('f', 0x070),  # FLAG_TEAM_AQUA_ESCAPED_IN_SUBMARINE
         do='Vào căn cứ Team Aqua (Lilycove), đánh Matt.',
         need='Cần Surf để tới cửa căn cứ.', src='AquaHideout_B2F/scripts.inc:44'),
    dict(map=(14, 0), xy=(23, 7), who='Tate & Liza', done=('f', 0x4F6),  # FLAG_DEFEATED_MOSSDEEP_GYM
         do='Huy hiệu 7: đánh Tate & Liza (đấu đôi).',
         need='Gym hệ Siêu linh.', src='MossdeepCity_Gym/scripts.inc:65'),
    dict(map=(14, 10), xy=(1, 8), who='Steven', done=('f', 0x075),  # FLAG_DEFEATED_MAGMA_SPACE_CENTER
         do='Cùng Steven đánh Maxie & Tabitha ở Trung tâm Vũ trụ.',
         need='', src='MossdeepCity_SpaceCenter_2F/scripts.inc:283'),
    dict(map=(14, 7), xy=(9, 6), who='Steven', done=('f', 0x07B),  # FLAG_RECEIVED_HM_DIVE
         do='Nhận HM08 Dive từ Steven.',
         need='', src='MossdeepCity_StevensHouse/scripts.inc:37'),
    dict(map=(24, 36), xy=(17, 42), who='Archie', done=('f', 0x081),  # FLAG_KYOGRE_ESCAPED_SEAFLOOR_CAVERN
         do='Lặn xuống Seafloor Cavern (Route 128), đánh Archie; Kyogre thức dậy.',
         need='Dive + Strength + Rock Smash.', src='SeafloorCavern_Room9/scripts.inc:114'),
    dict(map=(0, 7), xy=(20, 36), who='Steven', done=('v', 0x405E, 2),  # VAR_SOOTOPOLIS_CITY_STATE 2
         do='Vào Sootopolis xem Groudon và Kyogre đánh nhau.',
         need='Lặn (Dive) ở Route 126 để vào thành phố.', src='SootopolisCity/scripts.inc:242'),
    dict(map=(24, 42), xy=(9, 13), who='Wallace', done=('f', 0x137),  # FLAG_WALLACE_GOES_TO_SKY_PILLAR
         do='Gặp Wallace trong Cave of Origin.',
         need='', src='CaveOfOrigin_B1F/scripts.inc:50'),
    dict(map=(24, 85), xy=(14, 9), who='Rayquaza', done=('v', 0x405E, 5),  # VAR_SOOTOPOLIS_CITY_STATE 5
         do='Leo Sky Pillar đánh thức Rayquaza.',
         need='Mach Bike để qua sàn nứt.', src='SkyPillar_Top/scripts.inc:121'),
    dict(map=(15, 0), xy=(8, 2), who='Juan', done=('f', 0x4F7),  # FLAG_DEFEATED_SOOTOPOLIS_GYM
         do='Huy hiệu 8: đánh Juan.',
         need='Gym hệ Nước.', src='SootopolisCity_Gym_1F/scripts.inc:96'),
    dict(map=(0, 7), xy=(31, 18), who='Wallace', done=('f', 0x138),  # FLAG_RECEIVED_HM_WATERFALL
         do='Wallace cho HM07 Waterfall.',
         need='', src='SootopolisCity/scripts.inc:1261'),
    dict(map=(24, 43), xy=(3, 23), who='Wally', done=('f', 0x07E),  # FLAG_DEFEATED_WALLY_VICTORY_ROAD
         do='Wally chặn ở lối vào Victory Road.',
         need='Waterfall để tới Ever Grande.', src='VictoryRoad_1F/scripts.inc:43'),
    dict(map=(16, 0), xy=(6, 5), who='Tứ Thiên Vương', done=('f', 0x4FE),  # FLAG_DEFEATED_ELITE_4_DRAKE
         do='Đánh liền 4 người: Sidney, Phoebe, Glacia, Drake.',
         need='', src='EverGrandeCity_DrakesRoom/scripts.inc:58'),
    dict(map=(16, 4), xy=(6, 5), who='Wallace', done=('f', 0x864),  # FLAG_SYS_GAME_CLEAR
         do='Đánh Nhà vô địch Wallace, vào Đại sảnh Danh vọng.',
         need='', src='EverGrandeCity_HallOfFame/scripts.inc:45'),
]


def progress(flag, var):
    """[(bước, đã xong)] và chỉ số bước hiện tại (None = xong hết). Bước hiện tại = bước bắt buộc đầu tiên chưa xong
    đứng SAU bước xong cuối cùng (làm khác thứ tự / bỏ bước tuỳ chọn vẫn chỉ đúng)."""
    done = [(flag(s["done"][1]) if s["done"][0] == "f" else (var(s["done"][1]) or 0) >= s["done"][2]) for s in STEPS]
    last = max((i for i, d in enumerate(done) if d), default=-1)
    cur = next((i for i in range(last + 1, len(STEPS)) if not done[i] and not STEPS[i].get("optional")), None)
    return list(zip(STEPS, done)), cur
