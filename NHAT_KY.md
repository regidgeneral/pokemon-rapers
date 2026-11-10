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
