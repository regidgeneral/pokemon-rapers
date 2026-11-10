"""Các bước cốt truyện Pokémon Emerald tới Đại sảnh Danh vọng (SINH bằng dev/gen_quest.py từ pokeemerald, đừng sửa tay).
Mỗi bước: map đích (nhóm, số), ô NPC/điểm kích hoạt, điều kiện xong (cờ, hoặc biến >= giá trị), làm gì, ghi chú, nguồn,
chương (mục tiêu lớn), huy hiệu (bước gym), needs = điều kiện trước: ("hm", tên) / ("item", mã) / ("badges", số)."""

# tên, mã vật phẩm, mã chiêu, huy hiệu cần để dùng ngoài trận, nơi nhận (map, ô, ai), cờ đã nhận
HMS = {
    'cut': dict(name='HM01 Cut', item=339, move=15, badge=1, map=(11, 11), xy=(7, 5), who='ông chặt cây (nhà ở Rustboro)', got=0x089),
    'fly': dict(name='HM02 Fly', item=340, move=19, badge=6, map=(0, 34), xy=(26, 31), who='rival trên Route 119', got=0x06E),
    'surf': dict(name='HM03 Surf', item=341, move=57, badge=5, map=(8, 0), xy=(3, 4), who='bố Wally (Petalburg)', got=0x07A),
    'strength': dict(name='HM04 Strength', item=342, move=70, badge=4, map=(24, 4), xy=(23, 5), who='bạn trai Wanda trong Rusturf Tunnel (sau khi đập đá thông hầm)', got=0x06A),
    'flash': dict(name='HM05 Flash', item=343, move=148, badge=2, map=(24, 7), xy=(36, 9), who='người leo núi ở hang Granite', got=0x06D),
    'rocksmash': dict(name='HM06 Rock Smash', item=344, move=249, badge=3, map=(10, 2), xy=(4, 4), who='người trong nhà ở Mauville', got=0x06B),
    'waterfall': dict(name='HM07 Waterfall', item=345, move=127, badge=8, map=(0, 7), xy=(31, 18), who='Wallace ở Sootopolis', got=0x138),
    'dive': dict(name='HM08 Dive', item=346, move=291, badge=7, map=(14, 7), xy=(9, 6), who='Steven ở nhà (Mossdeep)', got=0x07B),
}
ITEMS = {
    269: dict(name='Devon Goods', map=(24, 4), xy=(14, 5), who='lấy lại từ lính Team Aqua trong Rusturf Tunnel'),
    274: dict(name='Thư gửi Steven', map=(11, 2), xy=(15, 5), who='chủ tịch Devon (Rustboro)'),
    288: dict(name='Devon Scope', map=(0, 35), xy=(13, 15), who='Steven trên Route 120'),
    375: dict(name='Magma Emblem', map=(24, 22), xy=(23, 5), who='ông bà cụ trên đỉnh Mt. Pyre'),
    259: dict(name='Mach Bike', map=(10, 1), xy=(2, 5), who='ông Rydel, tiệm xe đạp Mauville (chọn Mach Bike)'),
}

STEPS = [
    dict(goal='Bắt đầu hành trình', map=(0, 16), xy=(7, 14), who='túi của GS Birch', done=('f', 0x052),  # 1. FLAG_RESCUED_BIRCH
         do='Cứu Giáo sư Birch: mở túi của ông, chọn Pokémon đầu tiên.', need='', src='Route101/scripts.inc:218'),
    dict(goal='Bắt đầu hành trình', map=(0, 18), xy=(10, 3), who='rival', done=('f', 0x082),  # 2. FLAG_DEFEATED_RIVAL_ROUTE103
         do='Đánh rival lần đầu.', need='', src='Route103 (FLAG_DEFEATED_RIVAL_ROUTE103)'),
    dict(goal='Bắt đầu hành trình', map=(1, 4), xy=(6, 4), who='GS Birch', done=('f', 0x8E4),  # 3. FLAG_RECEIVED_POKEDEX_FROM_BIRCH
         do='Về phòng thí nghiệm nhận Pokédex.', need='', src='LittlerootTown_ProfessorBirchsLab/scripts.inc:539'),
    dict(goal='Huy hiệu 1 — Roxanne (Rustboro)', map=(8, 1), xy=(4, 2), who='bố Norman', done=('v', 0x4085, 2),  # 4. VAR_PETALBURG_GYM_STATE 2
         do='Gặp bố ở gym Petalburg, đi cùng Wally bắt Ralts.', need='', src='PetalburgCity_Gym/scripts.inc:90'),
    dict(goal='Huy hiệu 1 — Roxanne (Rustboro)', map=(11, 3), xy=(5, 2), who='Roxanne', done=('f', 0x4F0),  # 5. FLAG_DEFEATED_RUSTBORO_GYM
         do='Đánh Roxanne.', need='Gym hệ Đá.', src='RustboroCity_Gym/scripts.inc:18', badge=1),
    dict(goal='Lấy lại Devon Goods', map=(24, 4), xy=(14, 5), who='lính Team Aqua', done=('f', 0x08F),  # 6. FLAG_RECOVERED_DEVON_GOODS
         do='Đuổi theo lính Team Aqua trong Rusturf Tunnel, lấy lại Devon Goods.', need='', src='RusturfTunnel/scripts.inc:322'),
    dict(goal='Lấy lại Devon Goods', map=(11, 2), xy=(15, 5), who='chủ tịch Stone', done=('f', 0x0BC),  # 7. FLAG_RECEIVED_POKENAV
         do='Gặp chủ tịch Devon: nhận PokéNav + thư gửi Steven.', need='', src='RustboroCity_DevonCorp_3F/scripts.inc:54'),
    dict(goal='Huy hiệu 2 — Brawly (Dewford)', map=(17, 0), xy=(5, 3), who='ông Briney', done=('f', 0x871),  # 8. FLAG_VISITED_DEWFORD_TOWN
         do='Nhờ ông Briney chở thuyền tới Dewford.', need='', src='event_scripts.s:645 (VAR_BRINEY_LOCATION)'),
    dict(goal='Huy hiệu 2 — Brawly (Dewford)', map=(3, 3), xy=(4, 3), who='Brawly', done=('f', 0x4F1),  # 9. FLAG_DEFEATED_DEWFORD_GYM
         do='Đánh Brawly.', need='Gym hệ Giác đấu; gym tối, có Flash thì dễ hơn.', src='DewfordTown_Gym/scripts.inc:150', badge=2),
    dict(goal='Đưa thư cho Steven', map=(24, 10), xy=(7, 8), who='Steven', done=('f', 0x0BD),  # 10. FLAG_DELIVERED_STEVEN_LETTER
         do='Đưa thư cho Steven ở cuối hang Granite.', need='', src='GraniteCave_StevensRoom/scripts.inc:10', needs=[('item', 274)]),
    dict(goal='Giao Devon Goods cho Captain Stern (Slateport)', map=(0, 11), xy=(12, 9), who='ông Briney', done=('f', 0x877),  # 11. FLAG_VISITED_SLATEPORT_CITY
         do='Nhờ ông Briney chở tới Slateport.', need='', src='DewfordTown/scripts.inc:165'),
    dict(goal='Giao Devon Goods cho Captain Stern (Slateport)', map=(9, 0), xy=(5, 5), who='Dock (thợ đóng tàu)', done=('f', 0x094),  # 12. FLAG_DOCK_REJECTED_DEVON_GOODS
         do='Vào xưởng tàu Stern, nói chuyện với Dock.', need='Để hàng lính Team Aqua tránh khỏi cửa bảo tàng.', src='SlateportCity_SternsShipyard_1F/scripts.inc:15-16 (cũng bật FLAG_HIDE_SLATEPORT_CITY_TEAM_AQUA)'),
    dict(goal='Giao Devon Goods cho Captain Stern (Slateport)', map=(9, 8), xy=(13, 6), who='Captain Stern', done=('f', 0x095),  # 13. FLAG_DELIVERED_DEVON_GOODS
         do='Vào bảo tàng tầng 2, giao Devon Goods cho Captain Stern, đánh 2 lính Team Aqua.', need='', src='SlateportCity_OceanicMuseum_2F/scripts.inc:72', needs=[('item', 269)]),
    dict(goal='Huy hiệu 3 — Wattson (Mauville)', map=(0, 25), xy=(34, 56), who='rival', done=('v', 0x4069, 1),  # 14. VAR_ROUTE110_STATE 1
         do='Rival đón đánh trên Route 110.', need='', src='Route110/scripts.inc:470'),
    dict(goal='Huy hiệu 3 — Wattson (Mauville)', map=(0, 2), xy=(8, 6), who='Wally', done=('f', 0x0BE),  # 15. FLAG_DEFEATED_WALLY_MAUVILLE
         do='Wally thách đấu trước cửa gym Mauville.', need='', src='MauvilleCity/scripts.inc:149'),
    dict(goal='Huy hiệu 3 — Wattson (Mauville)', map=(10, 0), xy=(5, 2), who='Wattson', done=('f', 0x4F2),  # 16. FLAG_DEFEATED_MAUVILLE_GYM
         do='Đánh Wattson.', need='Gym hệ Điện; hàng rào điện mở bằng công tắc trong gym.', src='MauvilleCity_Gym/scripts.inc:93', badge=3),
    dict(goal='Chặn Team Magma ở Mt. Chimney', map=(10, 2), xy=(4, 4), who='người tặng HM', done=('f', 0x06B),  # 17. FLAG_RECEIVED_HM_ROCK_SMASH
         do='Nhận HM06 Rock Smash.', need='Đá chắn đường ở Route 111 (ô 18,101) phải đập mới qua được.', src='MauvilleCity_House1/scripts.inc:10'),
    dict(goal='Chặn Team Magma ở Mt. Chimney', map=(24, 0), xy=(14, 18), who='Team Magma', done=('v', 0x40BF, 1),  # 18. VAR_METEOR_FALLS_STATE 1
         do='Tới Meteor Falls xem Team Magma cướp thiên thạch (sau đó Magma rút khỏi cáp treo Route 112).', need='Đường đi qua Route 111, Fiery Path, Fallarbor.', src='MeteorFalls_1F_1R/scripts.inc:81', needs=[('hm', 'rocksmash')]),
    dict(goal='Chặn Team Magma ở Mt. Chimney', map=(24, 12), xy=(13, 6), who='Maxie', done=('f', 0x08B),  # 19. FLAG_DEFEATED_EVIL_TEAM_MT_CHIMNEY
         do='Đi cáp treo lên đỉnh Mt. Chimney, đánh Maxie.', need='Cáp treo ở nhà ga Route 112.', src='MtChimney/scripts.inc:64', via=((19, 0), (6, 6))),
    dict(goal='Huy hiệu 4 — Flannery (Lavaridge)', map=(4, 1), xy=(13, 9), who='Flannery', done=('f', 0x4F3),  # 20. FLAG_DEFEATED_LAVARIDGE_GYM
         do='Đánh Flannery.', need='Gym hệ Lửa. Từ đỉnh Mt. Chimney đi xuống Jagged Pass là tới Lavaridge.', src='LavaridgeTown_Gym_1F/scripts.inc:61', badge=4),
    dict(goal='Huy hiệu 5 — Norman (Petalburg)', map=(8, 1), xy=(4, 2), who='Norman', done=('f', 0x4F4),  # 21. FLAG_DEFEATED_PETALBURG_GYM
         do='Đánh bố Norman.', need='Gym hệ Thường.', src='PetalburgCity_Gym/scripts.inc:367', badge=5, needs=[('badges', 4)]),
    dict(goal='Huy hiệu 5 — Norman (Petalburg)', map=(8, 0), xy=(3, 4), who='bố Wally', done=('f', 0x07A),  # 22. FLAG_RECEIVED_HM_SURF
         do='Nhận HM03 Surf từ bố Wally.', need='', src='PetalburgCity_WallysHouse/scripts.inc:23'),
    dict(goal='Viện Thời tiết + HM Fly (Route 119)', map=(32, 1), xy=(4, 6), who='Shelly (Team Aqua)', done=('f', 0x097),  # 23. FLAG_RECEIVED_CASTFORM
         do='Đuổi Team Aqua khỏi Viện Thời tiết, nhận Castform.', need='', src='Route119_WeatherInstitute_2F/scripts.inc:119', needs=[('hm', 'surf')]),
    dict(goal='Viện Thời tiết + HM Fly (Route 119)', map=(0, 34), xy=(26, 31), who='rival', done=('f', 0x06E),  # 24. FLAG_RECEIVED_HM_FLY
         do='Rival đánh rồi cho HM02 Fly.', need='', src='Route119/scripts.inc:131', needs=[('hm', 'surf')]),
    dict(goal='Huy hiệu 6 — Winona (Fortree)', map=(0, 35), xy=(13, 15), who='Steven', done=('f', 0x11D),  # 25. FLAG_RECEIVED_DEVON_SCOPE
         do='Steven cho Devon Scope.', need='Để thấy Kecleon tàng hình chặn gym Fortree.', src='Route120/scripts.inc:216'),
    dict(goal='Huy hiệu 6 — Winona (Fortree)', map=(12, 1), xy=(15, 2), who='Winona', done=('f', 0x4F5),  # 26. FLAG_DEFEATED_FORTREE_GYM
         do='Đánh Winona.', need='Gym hệ Bay.', src='FortreeCity_Gym/scripts.inc:33', badge=6, needs=[('item', 288)]),
    dict(goal='Team Aqua & Team Magma: Orb, căn cứ, tàu ngầm', map=(24, 22), xy=(23, 5), who='ông bà cụ', done=('f', 0x0D4),  # 27. FLAG_RECEIVED_RED_OR_BLUE_ORB
         do='Lên đỉnh Mt. Pyre: Team Aqua cướp Red Orb; ông bà cụ đưa Magma Emblem.', need='', src='MtPyre_Summit/scripts.inc:59', needs=[('hm', 'surf')]),
    dict(goal='Team Aqua & Team Magma: Orb, căn cứ, tàu ngầm', map=(24, 91), xy=(16, 21), who='Maxie', done=('v', 0x4058, 1),  # 28. VAR_SLATEPORT_CITY_STATE 1
         do='Vào căn cứ Team Magma, đánh Maxie (Groudon thức dậy).', need='Cửa căn cứ ở Jagged Pass.', src='MagmaHideout_4F/scripts.inc:55', needs=[('item', 375)]),
    dict(goal='Team Aqua & Team Magma: Orb, căn cứ, tàu ngầm', map=(9, 9), xy=(8, 10), who='Archie', done=('v', 0x4058, 2),  # 29. VAR_SLATEPORT_CITY_STATE 2
         do='Tới cảng Slateport: Team Aqua cướp tàu ngầm.', need='', src='SlateportCity/scripts.inc:567'),
    dict(goal='Team Aqua & Team Magma: Orb, căn cứ, tàu ngầm', map=(24, 25), xy=(23, 19), who='Matt (Team Aqua)', done=('f', 0x070),  # 30. FLAG_TEAM_AQUA_ESCAPED_IN_SUBMARINE
         do='Vào căn cứ Team Aqua (Lilycove), đánh Matt.', need='', src='AquaHideout_B2F/scripts.inc:44', needs=[('hm', 'surf')]),
    dict(goal='Huy hiệu 7 — Tate & Liza (Mossdeep)', map=(14, 0), xy=(23, 7), who='Tate & Liza', done=('f', 0x4F6),  # 31. FLAG_DEFEATED_MOSSDEEP_GYM
         do='Đánh Tate & Liza (đấu đôi).', need='Gym hệ Siêu linh.', src='MossdeepCity_Gym/scripts.inc:65', badge=7, needs=[('hm', 'surf')]),
    dict(goal='Huy hiệu 7 — Tate & Liza (Mossdeep)', map=(14, 10), xy=(1, 8), who='Steven', done=('f', 0x075),  # 32. FLAG_DEFEATED_MAGMA_SPACE_CENTER
         do='Cùng Steven đánh Maxie & Tabitha ở Trung tâm Vũ trụ.', need='', src='MossdeepCity_SpaceCenter_2F/scripts.inc:283'),
    dict(goal='Huy hiệu 7 — Tate & Liza (Mossdeep)', map=(14, 7), xy=(9, 6), who='Steven', done=('f', 0x07B),  # 33. FLAG_RECEIVED_HM_DIVE
         do='Nhận HM08 Dive từ Steven.', need='', src='MossdeepCity_StevensHouse/scripts.inc:37'),
    dict(goal='Kyogre và Groudon thức dậy', map=(24, 36), xy=(17, 42), who='Archie', done=('f', 0x081),  # 34. FLAG_KYOGRE_ESCAPED_SEAFLOOR_CAVERN
         do='Lặn xuống Seafloor Cavern (Route 128), đánh Archie.', need='', src='SeafloorCavern_Room9/scripts.inc:114', needs=[('hm', 'dive'), ('hm', 'strength'), ('hm', 'rocksmash')]),
    dict(goal='Kyogre và Groudon thức dậy', map=(0, 7), xy=(20, 36), who='Steven', done=('v', 0x405E, 2),  # 35. VAR_SOOTOPOLIS_CITY_STATE 2
         do='Vào Sootopolis xem Groudon và Kyogre đánh nhau.', need='Lặn ở Route 126 để vào thành phố.', src='SootopolisCity/scripts.inc:242', needs=[('hm', 'dive')]),
    dict(goal='Kyogre và Groudon thức dậy', map=(24, 42), xy=(9, 13), who='Wallace', done=('f', 0x137),  # 36. FLAG_WALLACE_GOES_TO_SKY_PILLAR
         do='Gặp Wallace trong Cave of Origin.', need='', src='CaveOfOrigin_B1F/scripts.inc:50'),
    dict(goal='Kyogre và Groudon thức dậy', map=(24, 85), xy=(14, 9), who='Rayquaza', done=('v', 0x405E, 5),  # 37. VAR_SOOTOPOLIS_CITY_STATE 5
         do='Leo Sky Pillar đánh thức Rayquaza.', need='Sàn nứt phải chạy Mach Bike qua.', src='SkyPillar_Top/scripts.inc:121', needs=[('hm', 'surf'), ('item', 259)]),
    dict(goal='Huy hiệu 8 — Juan (Sootopolis)', map=(15, 0), xy=(8, 2), who='Juan', done=('f', 0x4F7),  # 38. FLAG_DEFEATED_SOOTOPOLIS_GYM
         do='Đánh Juan.', need='Gym hệ Nước.', src='SootopolisCity_Gym_1F/scripts.inc:96', badge=8, needs=[('hm', 'dive')]),
    dict(goal='Huy hiệu 8 — Juan (Sootopolis)', map=(0, 7), xy=(31, 18), who='Wallace', done=('f', 0x138),  # 39. FLAG_RECEIVED_HM_WATERFALL
         do='Wallace cho HM07 Waterfall.', need='', src='SootopolisCity/scripts.inc:1261'),
    dict(goal='Liên đoàn Pokémon (Ever Grande)', map=(24, 43), xy=(3, 23), who='Wally', done=('f', 0x07E),  # 40. FLAG_DEFEATED_WALLY_VICTORY_ROAD
         do='Wally chặn ở lối vào Victory Road.', need='', src='VictoryRoad_1F/scripts.inc:43', needs=[('hm', 'surf'), ('hm', 'waterfall')]),
    dict(goal='Liên đoàn Pokémon (Ever Grande)', map=(16, 0), xy=(6, 5), who='Tứ Thiên Vương', done=('f', 0x4FE),  # 41. FLAG_DEFEATED_ELITE_4_DRAKE
         do='Đánh liền 4 người: Sidney, Phoebe, Glacia, Drake.', need='Victory Road cần Strength + Rock Smash.', src='EverGrandeCity_DrakesRoom/scripts.inc:58', needs=[('hm', 'strength'), ('hm', 'rocksmash')]),
    dict(goal='Liên đoàn Pokémon (Ever Grande)', map=(16, 4), xy=(6, 5), who='Wallace', done=('f', 0x864),  # 42. FLAG_SYS_GAME_CLEAR
         do='Đánh Nhà vô địch Wallace, vào Đại sảnh Danh vọng.', need='', src='EverGrandeCity_HallOfFame/scripts.inc:45'),
]


def progress(flag, var):
    """[(bước, đã xong)] và chỉ số bước hiện tại (None = xong hết). Bước hiện tại = bước bắt buộc đầu tiên chưa xong
    đứng SAU bước xong cuối cùng (làm khác thứ tự / bỏ bước tuỳ chọn vẫn chỉ đúng)."""
    done = [(flag(s["done"][1]) if s["done"][0] == "f" else (var(s["done"][1]) or 0) >= s["done"][2]) for s in STEPS]
    last = max((i for i, d in enumerate(done) if d), default=-1)
    cur = next((i for i in range(last + 1, len(STEPS)) if not done[i] and not STEPS[i].get("optional")), None)
    return list(zip(STEPS, done)), cur


def badge_step(n):
    """Bước gym cho huy hiệu n (1..8)."""
    return next(s for s in STEPS if s.get("badge") == n)
