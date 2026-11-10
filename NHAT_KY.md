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
