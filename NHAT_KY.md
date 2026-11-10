# Nhật ký PokemonRapers (Emerald Ý)

> Chỉ thêm cuối file. Tìm bằng grep theo từ khoá, không đọc cả file.

## 2026-11-10 — tạo tool từ bản FR
- ROM `2207 - Pokemon - Versione Smeraldo (I)(Pokemon Rapers).gba`: header `POKEMON EMER` / `BPEI`, SHA1 35bf749579af88c784f6fbdd67421d3164a1bded = Emerald Ý gốc.
- Folder `E:\PokemonRapers`: chép code FR (git archive, lịch sử git mới), ROM chuyển từ `E:\PokemonFR` sang.
- **RAM**: đếm literal u32 trong ROM: gPlayerParty 0x020244EC (1091), gEnemyParty 0x02024744 (532), SaveBlock1/2/storage ptr
  0x03005D8C/90/94, gMain 0x030022C0, gTasks 0x03005E00, gBattleMons 0x02024084, gObjectEvents 0x02037350 → trùng Emerald Mỹ.
  Đối chiếu code FR (16-24 byte trước literal, che BL): sWarpDestination 0x020322E4 (7/7), khoá điều khiển 0x03000F2C,
  gMapHeader 0x02037318 (26), gFieldCallback 0x03005DAC (7), controller 0x03005D60 (9).
- **Hàm** (khớp thân hàm FR): CB2_Overworld 0x08085E71, CB2_ReturnToField 0x080860DD, FieldCallback_UseFly 0x080B6A11.
  KHÔNG khớp: BattleMainCB2, controller chọn lệnh/chiêu, túi, Task_Fishing (Emerald viết khác) → săn tắt.
- **ROM**: tên loài 0x08317F8C, chiêu 0x08319140, ability 0x0831B0DB, dữ liệu chiêu 0x0831C298, chỉ số 0x0831FDCC,
  EXP 0x0831F12C, TM 0x08612BDC, natdex 0x0831D682, tiến hoá 0x08324D1C, vật phẩm 0x0858000C (max 376 MAPPA STINTA),
  hoang dã 0x0854FA8C (124 map, đầu = Route 101), map groups 0x084832BC, tên khu vực 0x0859DEE8, điểm bay 0x0859BF00 (22, 8 byte),
  trainer 0x0830F9F4, ảnh mặt trước 0x08300DDC, màu 0x0830303C / shiny 0x08303DFC (cách nhau 440 × 8).
- Không tìm được bảng cờ hành vi khối (sTileBitAttributes) trong ROM → ô gặp dùng danh sách hành vi pokeemerald, chưa kiểm.
- Bài thử: t_frmon 519/519, t_box_fake 10/10, t_race_fake 4/4, t_gui_fake 0 lỗi, t_fish_fake bỏ qua; gen_sprites 411/411, xem ảnh đúng.

## 2026-11-10 (chiều) — bỏ bản Ý, chuyển sang Emerald tiếng Anh
- Duy hỏi "bản này không phải tiếng Anh hả" → bản Ý thật (BPEI, tên chiêu/map tiếng Ý). Duy chép `Pokemon - Emerald Version (USA, Europe).gba`:
  BPEE, SHA1 f3ae088181bf583e55daf962a92bb46f4f1d07b7 = dump gốc. Duy chốt: bỏ bản Ý, làm bản Anh.
- RAM y hệt bản Ý (đếm literal lại: 0x020244EC 1091, 0x03005D8C 829, khoá 0x03000F2C 3...).
- ROM Anh: loài 0x083185C8, chiêu 0x0831977C, ability 0x0831B6DB, dữ liệu chiêu 0x0831C898, chỉ số 0x083203CC, EXP 0x0831F72C,
  TM 0x08616040, natdex 0x0831DC82, tiến hoá 0x0832531C, vật phẩm 0x085839A0, hoang dã 0x08552D48, map groups 0x08486578,
  khu vực 0x085A147C, điểm bay 0x0859F53C, trainer 0x08310030, lớp trainer 0x0830FCD4 (bản Anh đọc được, 13 byte),
  ảnh 0x08301418, màu 0x08303678 / shiny 0x08304438. Hàm: CB2_Overworld 0x08085E5D, CB2_ReturnToField 0x080860C9, UseFly 0x080B69FD.
- Lệnh xoá ROM Ý bị chặn (auto mode) → chuyển ROM Ý sang `E:\Pokemon\`. Thêm `*.zip` vào .gitignore (zip ROM Anh nằm trong folder).
- Bài thử: t_frmon 519/519, box 10/10, race 4/4, gui 0 lỗi, fish bỏ qua; 411 ảnh, xem mẫu đúng.

## 2026-11-10 — vẽ nhân vật trên bản đồ
- Duy gửi ảnh: bản đồ Littleroot chỉ có số tròn thay NPC → hồ sơ thiếu ow_gfx/ow_pals.
- Dò: bảng con trỏ GraphicsInfo 0x08505620 (mục 0 Brendan 16x32, tag màu 0x1100, 1 tham chiếu), bảng màu {ptr, tag} 0x0850BBC8
  (tag 0x1103, 0x1104... 0x1100, 0x1101). Gfx 94/140/141 cỡ 48x48 / 96x40 / 88x32 (xe tải, tàu, bóng) → nới điều kiện cỡ trong
  ow_sprite thành bội 8, ≤ 128. 245/245 hình vẽ được, xem mẫu đúng. t_frmon thêm 1 kiểm (520/520).

## 2026-11-11 — đo câu cá + trận đấu trong game thật
- Duy đứng ở chỗ câu, câu tay 2 lần (dính cả 2), trong trận mở túi, ném bóng, chạy. Script `dev\watch_fish_em.py` (chỉ đọc gTasks,
  gMain.callback2, gBattlerControllerFuncs, khoá, phím) — chết ở giây 101 vì PermissionError tranh file ipc với tool (đã sửa: bắt OSError).
- Task_Fishing 0x0808C8C1 (lock = 1), bước 2 -> 4 -> 7 -> 10, A ở bước 10 -> vào trận. ROM: hàm gọi bảng 16 bước 0x0849755C (như pokeemerald).
- Trận: callback2 0x08038421; controller[0] = 0x080597B5 ở menu chọn lệnh (A -> chiêu), 0x08058B41 lúc chọn chiêu (chỉ thấy 1 lần, chưa chắc);
  túi trong trận callback2 0x081AAD5D (trùng ứng viên mẫu byte 10/11). gBagPosition 0x0203CE58 đọc thật: cb 0x08059D51, location 1, ngăn 1.
- Code: hồ sơ thêm cb2_battle/ctl_*/cb2_bag/bag_state/fishing; set_bag_cursor/bag_cursor theo bố cục Emerald (mở ngăn Poké Ball ở đầu,
  bấm xuống tới đúng bóng); câu bấm A ở bước 6-7 (6 khung chờ) và ≥ 9; tắt tự lưu (START_MENU_CURSOR = None) -> nhắc lưu tay.
- Bài thử: t_fish_fake 19/19 (thêm bước 3, 6, 7, 8), t_frmon 520, box 10, race 4, gui 0 lỗi. CHƯA chạy Săn thật.

## 2026-11-11 — chạy Săn câu cá thật lần đầu
- Duy: câu ~5 lần dính 1, vào trận với MAGIKARP Lv10 thì tool đứng ở menu FIGHT/BAG/POKéMON/RUN.
- Đọc lúc đứng ở menu: cb2 0x08038421, inBattle 2, controller[0] = 0x08057589 (11/11 lần). 0x08057589 đọc gMain (literal 0x030022C0),
  được gọi từ 0x0805C040. 0x080597B5 (lấy nhầm làm ctl_action) gọi từ 0x0805BFDC, đứng lúc chữ intro trận chờ A -> hàm chờ chữ.
  Sửa ctl_action = 0x08057589. Tỉ lệ dính 1/5: chưa rõ là "Not even a nibble" (game, 50% mỗi vòng) hay "got away" (A trễ) -> hỏi Duy.

## 2026-11-11 — mở khoá săn shiny, gói A
- Duy dán yêu cầu từ phiên FR (commit FR 6425db9). Đọc RAM: Petalburg, 0 huy hiệu, vừa có Pokédex, 165 cờ ẩn NPC đang bật.
- Tra pokeemerald (sparse clone vào scratchpad): SYSTEM_FLAGS 0x860 (flags.h:1348), huy hiệu 0x867-0x86E (1359-1366),
  VISITED 0x86F-0x87E (1370-1385), B_DASH 0x8C0 (1462), NATIONAL_DEX 0x896 (1414), GAME_CLEAR 0x864 (1354, 22 file script kiểm);
  VAR_NATIONAL_DEX 0x4046 (vars.h:90) = 0x302, nationalMagic 0xDA, mode National (event_data.c:63-72; global.h:210, 527);
  cờ SB1 +0x1270, biến +0x139C (global.h:1020-1021). Kecleon chỉ kiểm Devon Scope (kecleon.inc:51), sa mạc kiểm Go-Goggles
  (Route111/scripts.inc:190). Latios/Latias: hall_of_fame.inc:44-45 đặt biến nhà = 3, mẹ bật TV thả roamer (players_house.inc:438-446).
- Hội đồng: gói A (đi lại tự do, không đụng cốt truyện, không cờ phá đảo, Duy tự dạy HM). Duy: "làm luôn".
- Code: UNLOCK_* + Game.unlock_all (write_cas một khung hình, chỉ ở overworld), nút 🔓 sao lưu .sav trước.
  Bài thử t_unlock_fake 16/16. Lần đầu 2 SAI do túi giả 0x02027000 đè vùng cờ giả (sb1 giả + 0x1270) -> chuyển túi giả sang 0x02032000.

## 2026-11-11 — "tool chưa tự lưu được": tự lưu Emerald + chấm IV
- Duy hỏi thông báo "chưa tự lưu được". Log encounter_history: 762 lần gặp 09:17-11:09 (530 Magikarp, 223 Goldeen), không shiny.
  11:08 tool bắt MAGIKARP Lv5 IV 28/14/28/28/25/31 (đang ở ô 4 đội) vì "IV có ích" 140/155 = 90% -> quan trọng -> muốn lưu, Emerald
  chưa có con trỏ menu Start -> chỉ nhắc. Hai chỗ sai: chấm theo chỉ số gốc Magikarp (SpA 15 > Atk 10 -> coi SpA là chính, Gyarados
  dùng Atk; con này Atk 14) và săn "Magikarp shiny" mà Magikarp thường vẫn tính quan trọng vì đúng loài.
- Dò menu Start: quét EWRAM tìm dãy mã mục 0,1,2,4,5,6,7 -> 0x02037610, trước là số mục 7 (0x0203760F), con trỏ 2 (0x0203760E,
  lần trước mở Túi). ROM tham chiếu 0x0203760E/0F/10 lần lượt 2/5/3 lần.
- Sửa: hồ sơ start_menu; hunt_save_step tìm vị trí LƯU trong danh sách mục, bấm lên/xuống (không dựa vòng quanh); menu lạ -> dừng + báo.
  Rom.grade_base (dạng tiến hoá cuối, nhiều nhánh lấy tổng cao nhất), mọi lời gọi iv_grade dùng nó. hunt_important: đúng loài chỉ tính
  khi không đòi shiny. Bài thử t_save_fake 13/13 (con Magikarp 11:08 giờ chấm 129/155 Atk -> không bắt nữa); bài cũ qua hết.

## 2026-11-11 — xoá trạng thái xấu trong trận
- Duy gửi ảnh: Treecko Lv13 ngủ (SLP) khi đánh SHROOMISH ở Petalburg Woods (Effect Spore), tool chỉ hồi sau trận.
  Hỏi phạm vi -> Duy chốt "mọi trận" (khi bật Tự hồi).
- Đọc thật trước khi ghi: ctl 0x08057589 (chọn lệnh), TREECKO HP 42/45 khớp ảnh, status1 (+0x4C) = 0x2, status2 = 0.
- Code: Game.cure_battle_status (chỉ khi ctl = chọn lệnh, write_cas status1 -> 0, trận đôi thêm ô 2), tick_battle gọi khi bật Tự hồi,
  báo "💊 Trong trận: X hết ngủ". Chạy thật 1 lần: [('TREECKO', 'ngủ')], status1 sau = 0. Bài thử t_status_fake 7/7, bài cũ qua hết.

## 2026-11-11 — bắt xong không đặt biệt danh
- Duy: "làm thêm chức năng tắt đặt tên pokemon sau khi bắt". Săn đã tự bấm B; giờ cho mọi lần bắt, công tắc ⚙ (mặc định bật).
- Dò: bảng lệnh battle script 0x0831BD10 (249 lệnh 0x00-0xF8, 5 tham chiếu). Hàm lệnh 0xF3 0x08056BEC dùng gBattleCommunication
  0x02024332 + gMain + BattleMainCB2 0x08038421 = trygivecaughtmonnick. Vùng battle script chỉ có 1 chỗ 0xF3: 0x082DBDAF.
  gBattlescriptCurrInstr 0x02024214 (526 tham chiếu). Bước chờ YES/NO = gBattleCommunication[0] == 1 theo pokeemerald, CHƯA đo thật.
- Code: hồ sơ `nickname`, Game.nickname_prompt, tick_battle bấm B (game tự dọn khung). Bài thử t_status_fake 14/14, bài cũ qua hết.

## 2026-11-11 — đặt biệt danh vẫn hiện -> chuyển sang Lua
- Duy gửi ảnh màn "SHROOMISH's nickname?" có chữ "A" đã gõ. Đọc lúc đó: đã về overworld (lỡ khoảnh khắc). Tool chạy bản mới (14:05),
  skip_nick bật. Kết luận: bấm A dồn qua "Gotcha!" -> A rơi vào câu hỏi (con trỏ mặc định YES) trước khi Python (kiểm ~1 giây/lần) bấm B.
- pokeemerald battle_script_commands.c:10220-10292: bước 0 vẽ YES/NO -> 1; bước 1 A+YES -> 2 (màn đặt tên), B hoặc A+NO -> 4
  (không dọn gì thêm); 4 = nhảy qua. -> Lua lệnh N: mỗi khung hình, lệnh 0xF3 và bước <= 1 -> ghi 4 (khung YES/NO không kịp hiện).
- Python: Game.set_skip_nick, App.sync_skip_nick (15 giây/lần + khi đổi công tắc), Lua cũ -> giữ cách bấm B.
  Lua đang chạy trả "ERR cmd N" (chưa nạp lại). Không có trình Lua trên máy -> chưa soát được cú pháp ngoài mGBA.

## 2026-11-11 — làm lại phần nhiệm vụ: bước cốt truyện + đường tím
- Duy kẹt ở Slateport, tab Việc/Cốt truyện không giúp: main_story dùng cờ huy hiệu FR (0x820), chỉ quét script, không có thứ tự.
  Duy: bỏ kiểu "đi về phía đông", nói nhiệm vụ cần gì / ở đâu / làm gì, vẽ đường từ nhân vật tới chỗ nhiệm vụ.
- RAM thật: 2 huy hiệu, FLAG_DELIVERED_STEVEN_LETTER, còn DEVON GOODS -> bước tiếp = Captain Stern (OceanicMuseum_2F scripts.inc:72).
- Tra pokeemerald: script truy ngược setflag/setvar -> NPC/coord event trong map.json -> (map, ô); map_groups.json -> (nhóm, số),
  khớp tên map ROM. Biến: VAR_PETALBURG_GYM_STATE 2, VAR_ROUTE110_STATE 1, VAR_METEOR_FALLS_STATE 1, VAR_SLATEPORT_CITY_STATE 1/2
  (Magma Hideout / cảng), VAR_SOOTOPOLIS_CITY_STATE 2/5. SYSTEM_FLAGS = 0x860 (flags.h:1348).
- Code: mm_quest.py (41 bước, sinh từ dev/gen_quest.py), Game.vars, Story.walk_path (BFS lưới va chạm, đổi độ cao qua ô 0/15),
  App.guide_goal/guide_route/guide_tiles/quest_path_draw/quest_target_draw/quest_progress/quest_next_text/quest_story mới;
  route_how bỏ chữ hướng. Xoá main_story + world_index (không còn ai gọi). Thử thật đường: Slateport (21,15) -> cửa bảo tàng (30,26)
  -> cầu thang 1F (6,1) -> Stern 2F; xem ảnh vẽ thử đúng.
- Bài thử t_quest_fake 18/18 (dữ liệu, bước hiện tại, giao diện giả ở Slateport). t_fish_fake hỏng vì settings.json thật đang săn
  ABRA (hộp thoại giả trả "Không") -> bài thử tự bỏ hunt_target. Mọi bài thử qua.

## 2026-11-11 — NPC chắn cửa bảo tàng: thiếu bước Dock + tự phát hiện NPC chắn đường
- Duy gửi ảnh: đường tím tới cửa bảo tàng nhưng hàng lính Aqua chắn. RAM: lính ở (30,27) (31,27) ngay trước cửa (30,26) (31,26),
  Duy ở (31,28). Cờ ẩn chung 0x372 FLAG_HIDE_SLATEPORT_CITY_TEAM_AQUA, chỉ bật ở SlateportCity_SternsShipyard_1F/scripts.inc:15-16
  (nói chuyện với Dock ô 5,5, FLAG_DOCK_REJECTED_DEVON_GOODS 0x94). Lính 1 chỉ nói "Quit pushing" rồi đứng lại.
- Sửa: thêm bước Dock vào gen_quest (42 bước), RAM thật ra bước 12 = Dock. Chung cho mọi chỗ: Game.live_objects (gObjectEvents,
  lọc map), Story.flag_setters (quét mọi script 1 lần 0,4 giây: tự tìm ra cờ 0x372 <- NPC (5,5) map (9,0)), walk_path(blocked=...),
  App.quest_route_now / quest_block_text (⚠ CÓ NPC ĐỨNG CHẮN ĐƯỜNG + [xem chỗ đó]) / ✖ đỏ. Bấm xem bước khác cũng có ★ (q_view_step).
  Mục LỐI ĐI: "Hướng/Đi về phía Bắc" -> "Ra khỏi map / Dive". t_quest_fake 22/22 (thêm ca đúng ảnh), bài cũ qua hết.

## 2026-11-11 — nhiệm vụ dạng chuỗi điều kiện (mục tiêu -> việc cần -> có/thiếu)
- Duy: "nhìn vào là biết sẽ làm gì, như dùng Rock Smash cần bao nhiêu huy hiệu, lấy ở đâu; giờ nhìn còn rối". Trình bố cục mẫu, Duy: làm luôn.
- gen_quest viết lại: 17 chương (mục tiêu lớn), bước gym có badge=n, needs (hm/item/badges). HMS: đĩa, chiêu, huy hiệu dùng ngoài trận
  (Cut 1, Flash 2, Rock Smash 3, Strength 4, Surf 5, Fly 6, Dive 7, Waterfall 8), nơi nhận (Cut: nhà Rustboro 7,5; Flash: Granite 1F
  36,9; Strength: Rusturf Tunnel 23,5 sau khi đập đá; ...). ITEMS: Devon Goods 269, Thư 274, Devon Scope 288, Magma Emblem 375, Mach Bike 259.
- Route 111: tìm đường thật từ mép Mauville (12,139) tới đoạn mép nối Route 112 (offset 20, cao 60) bắt buộc qua đá (18,101); coi đá là
  vật cản thì không có đường -> Rock Smash BẮT BUỘC (trước ghi tuỳ chọn = sai), Meteor Falls needs rocksmash.
- GUI: quest_needs (túi, cờ huy hiệu 0x866+n, chiêu đội), quest_next_text = 🎯 MỤC TIÊU + CHUỖI VIỆC + TIẾP THEO, q_need_tgt (đường tím
  tới thứ thiếu đầu tiên), q_pick (🧭), chi tiết map thu gọn (không chấm số trên bản đồ khi thu). quest_where: "(trong nhà)" chỉ khi trùng
  tên thị trấn/route nhóm 0 (hang nhiều tầng không ghi). dev/show_quest_fake.py in thử tab Việc. t_quest_fake 33/33; mọi bài thử qua.

## 2026-11-11 — chia EXP cho cả đội + kho PC, tự tiến hoá
- Duy hỏi có share EXP vào kho không -> không (code AowVN/CFRU còn nhưng tắt: cần box_ptr + cờ Exp. Share của hack). Duy: làm, chia cho
  toàn đội và kho, có tự tiến hoá.
- pokeemerald: Cmd_getexp (battle_script_commands.c:3310-3392): calculatedExp = expYield*level/7, phần Exp. Share = /2 (>=1); Lucky Egg,
  trainer, đổi tay mỗi cái *150/100 (Emerald không có x1.7 khác ngôn ngữ). GetEvolutionTargetSpecies (pokemon.c:5513-5579): duyệt hết
  mục, khớp sau cùng thắng, HOLD_EFFECT_PREVENT_EVOLVE chặn. EXP gốc ở BaseStats +9 (Magikarp 20 đúng). Lucky Egg 197, Everstone 195.
- Code: mm_core share_exp_gain / evolve_target / share_exp_apply, Rom.exp_yield / item_id; bỏ exp_share_gain, could_have_evolved,
  EVO_LEVEL_METHODS, box_evolve, box_exp_share (CFRU, kho không mã hoá), Game.exp_share_on, App.log_battle. tick_battle: đầu trận chụp
  (đội, đối thủ, trận trainer = battle_type & 8); trận mới chen giữa thì bỏ phần trận cũ (không ghi đội giữa trận); về bản đồ mới
  finish_exp. Công tắc ⚙ "Chia EXP cho cả đội + kho PC..." (settings box_exp, mặc định bật).
- Bài thử t_exp_fake 22/22 (công thức tính tay, tiến hoá, luồng trận giả); mọi bài thử qua.
