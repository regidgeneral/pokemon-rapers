# PokemonRapers — tool sửa game cho Pokémon Emerald (USA, Europe) gốc — ghi chú project

> **2 tầng ghi chú** (CLAUDE.md global E14): file này = quy tắc + trạng thái hiện tại, giữ ≤ ~10KB.
> Lịch sử từng ngày, bằng chứng đo → `NHAT_KY.md` (chỉ thêm cuối, grep theo từ khoá, không đọc cả file).

**Tạo:** 2026-11-10 · **Thư mục:** máy công ty `E:\PokemonRapers` · **Repo:** https://github.com/regidgeneral/pokemon-rapers
**Tech stack:** Python 3 + Tkinter + Pillow (`tool\`), mGBA dev + Lua (`mm_bridge.lua`, giao tiếp qua file trong `tool\ipc\`), git đồng bộ 2 máy.

## Project là gì
Tool sửa/hỗ trợ chơi **Pokémon Emerald bản tiếng Anh** (mã `BPEE`, ROM gốc không vá, shiny 1/8192).
Ban đầu làm cho bản Ý (`BPEI`, "Rapers" = tên nhóm dump) → Duy chốt 10/11 **bỏ bản Ý, chỉ làm bản Anh**; tên repo giữ nguyên.
Tách từ tool FireRed (`E:\PokemonFR`, repo `regidgeneral/pokemon-fire-red`) ngày 10/11, lịch sử git mới.
**Ba bản code ĐỘC LẬP** (AowVN / FR / Emerald, Duy chốt 09/11 + 10/11): sửa lỗi bên này không tự sang bên kia.

## Nội dung folder
- ROM `Pokemon - Emerald Version (USA, Europe).gba` (SHA1 f3ae088181bf...), save cùng tên `.sav`. ROM/zip không có trong repo (gitignore).
  ROM Ý đã chuyển ra `E:\Pokemon\` (không xoá).
- `tool\`: `mm_gui.py` (giao diện), `mm_core.py` (hồ sơ EMERALD + `FrMon` = mã hoá Pokémon Gen 3), `mm_story.py`, `mm_items.py`, `mm_audio.py`, `mm_bridge.lua`, `save_sync.py`, `gen_sprites.py`, `Mo_Tool.bat`.
- `tool\dev\`: bài thử + script đọc game. `mgba\`: mGBA dev portable. `Choi.bat` / `ChoiThu_KhongDongBo.bat` / `CaiDat_LanDau.bat` như FR.

## Quy trình mỗi lần sửa
1. Việc lớn → hội đồng 4 vai (E9). 2. Định đề xuất việc "treo" → grep code + `NHAT_KY.md`.
3. Sửa → thêm/sửa bài thử trong `tool\dev\`, chạy hết bài thử liên quan.
4. `git commit` → **đẩy lên GitHub**. 5. Thêm mục ngày vào cuối `NHAT_KY.md`; sửa mục **Trạng thái**.

## Lệnh (chạy trong `tool\`, kèm `PYTHONIOENCODING=utf-8` khi in ra file)
| Việc | Lệnh |
|---|---|
| Bài thử | `py -3 dev\t_frmon.py` (mã hoá + dữ liệu ROM Emerald) · `dev\t_box_fake.py` · `dev\t_gui_fake.py` · `dev\t_race_fake.py` · `dev\t_fish_fake.py` (câu cá Emerald) · `dev\t_unlock_fake.py` (mở khoá) · `dev\t_save_fake.py` (tự lưu, chấm IV) · `dev\t_status_fake.py` (xoá trạng thái trong trận, bỏ đặt biệt danh) · `dev\t_exp_fake.py` (chia EXP đội + kho, tiến hoá) · `dev\t_quest_fake.py` (nhiệm vụ: bước, chuỗi điều kiện, đường tím, NPC chắn) |
| Đọc game đang chạy | `py -3 dev\peek_em.py` / `dev\watch_em.py` |
| Đồng bộ | `py -3 save_sync.py start` · `pull` · `push` · `status` · `code` |
| Máy mới | `py -3 save_sync.py setup https://github.com/regidgeneral/pokemon-rapers.git` hoặc `CaiDat_LanDau.bat` |

## Môi trường & cạm bẫy (như FR)
- `py -3` / `pyw -3`, đừng dùng `python` (2.7). Sửa file tiếng Việt bằng Edit/Write/Python, KHÔNG Get-Content/Set-Content PS 5.1.
- `.bat`: chữ không dấu + CRLF. Bài thử giao diện không chụp màn hình, thay `messagebox` bằng bản giả.
- Bash tool máy công ty: heredoc / `cd` vào scratchpad bị lỗi (10/11) → ghi script ra file rồi chạy bằng PowerShell `py -3 -X utf8`.

## Khác FR (dò 10/11, chi tiết trong comment hồ sơ EMERALD ở mm_core.py)
- RAM (đếm literal trong ROM + đối chiếu code FR): đội 0x020244EC, SaveBlock ptr 0x03005D8C/90/94, gMain 0x030022C0.
- Bảng ROM dò theo nội dung (cách dò ghi trong comment hồ sơ). Bản Ý có RAM giống hệt, chỉ khác bảng ROM (xem NHAT_KY).
- SaveBlock1: tiền +0x490 (khoá SB2 +0xAC), cờ +0x1270, SELECT +0x496, seen +0x988/+0x3B24. Túi: 5 ngăn, Vật phẩm chính = ngăn 4.
- Bản đồ: tileset chính 512 khối, 6 bảng màu; thuộc tính khối u16 ở tileset +0x10; ô gặp theo hành vi (`MB_LAND`/`MB_WATER` trong mm_story.py, theo pokeemerald).
- Cờ trainer 0x500 + id, vật phẩm ẩn 0x1F4 + số.

## Đã BỎ — đừng đề xuất lại
- Tính năng AowVN/CFRU (bộ đếm shiny, Randomizer, roamer CFRU). Vá ROM. Gộp code với FR/AowVN.
  (Exp. Share kho kiểu CFRU đã bỏ; 11/11 Duy yêu cầu làm lại theo Gen 3 — xem Trạng thái.)

## Trạng thái — việc treo
**✅ Bài thử (10/11, bản Anh):** t_frmon 519/519 (tên, Route 101, màu, tiến hoá), t_box_fake 10/10, t_race_fake 4/4, t_gui_fake 0 lỗi; 411 ảnh Pokémon đúng.
**☐ Chưa kiểm trong game thật:** mọi thứ (đọc đội/kho/túi/tiền/map, nhận trận, Bay). Chưa có `.sav`, chưa chạy Choi.bat lần nào.
**☐ Săn + câu cá (11/11): đã đo trong game, đã code, CHƯA chạy thử bằng tool.** Task_Fishing 0x0808C8C1, bấm A ở bước 6-7 ("Oh! A bite!", ~0,5 giây) và ≥ 9. Trận: cb2 0x08038421, chọn lệnh 0x08057589 (sửa 11/11, 0x080597B5 = chờ chữ), chọn chiêu 0x08058B41 (chưa chắc), túi 0x081AAD5D / gBagPosition 0x0203CE58. Tự lưu sau khi bắt (11/11): menu Start 0x0203760E con trỏ / +1 số mục / +2 mã mục (LƯU = 5, vị trí đổi khi có PokéNav); chấm IV theo dạng tiến hoá cuối (`Rom.grade_base`); săn "loài X shiny" thì X thường không tính là quan trọng. ☐ Tự lưu chưa chạy thật.
Đo lại: `py -3 dev\watch_fish_em.py [giây]` (chỉ đọc), Duy tự câu/đánh tay.
**✅ Hình nhân vật trên bản đồ (10/11):** ow_gfx 0x08505620 / ow_pals 0x0850BBC8, 245/245 hình vẽ được (Duy báo bản đồ chỉ có số tròn).
**Mở khoá săn shiny, gói A (11/11):** nút 🔓 ở tab 📖 Cốt truyện → `Game.unlock_all`: 8 huy hiệu, Bay 16 thị trấn, giày chạy, National Dex (cờ + biến 0x4046 + SaveBlock2), HM01-08, 3 cần, 2 xe đạp, Go-Goggles, Devon Scope. KHÔNG cờ phá đảo, không biến cốt truyện/cờ ẩn NPC/trainer/huyền thoại (Duy chốt). ☐ Chưa bấm thật. Gói B (tua cốt truyện từng chuỗi để mở huyền thoại) = làm riêng khi Duy cần.
**Xoá trạng thái xấu trong trận (11/11, Duy chốt MỌI trận khi bật Tự hồi):** `Game.cure_battle_status` gọi từ `tick_battle` lúc controller = chọn lệnh; gBattleMons[0] (+[2] trận đôi) status1 +0x4C, ghi có điều kiện. ✅ Đã chạy thật: Treecko ngủ (status1 0x2) -> 0. Không đụng status2 (lú lẫn...).
**Bắt xong không đặt biệt danh (11/11, công tắc ⚙ `skip_nick`, mặc định bật):** `Game.nickname_prompt` = Lua lệnh `N` (mỗi khung hình: lệnh 0xF3 trygivecaughtmonnick ở bước ≤ 1 -> ghi bước = 4, như bấm B; battle_script_commands.c:10220-10292); tool gửi N 15 giây/lần + khi đổi công tắc; Lua cũ -> Python bấm B mỗi giây (trượt khi bấm A dồn: lần đầu 11/11 vào màn đặt tên SHROOMISH). ☐ Bản Lua chưa chạy thật.
**Nhiệm vụ cốt truyện (11/11, Duy: "không chỉ hướng, vẽ đường tới chỗ nhiệm vụ"):** `mm_quest.py` = 42 bước tới Đại sảnh Danh vọng, SINH bằng `dev\gen_quest.py` từ pokeemerald (cờ/biến + map + ô NPC, nguồn file:dòng từng bước). Tab 📋 Việc (11/11 chiều, Duy: "nhìn vào là biết làm gì, như Rock Smash cần mấy huy hiệu, lấy ở đâu"): 🎯 MỤC TIÊU = chương (17 chương) + CHUỖI VIỆC (bước ✔/➜/⬜ + điều kiện: HM = đĩa trong túi + huy hiệu dùng ngoài trận + con trong đội biết chiêu; vật phẩm; số huy hiệu — đọc túi/cờ/chiêu đội) + TIẾP THEO; đường tím tự dẫn tới thứ thiếu đầu tiên, bấm 🧭 dòng nào dẫn dòng đó; danh sách theo map thu gọn "▸ Chi tiết map này". 📖 Cốt truyện: đủ bước ✔/➜. In thử: `py -3 dev\show_quest_fake.py <số bước đã xong>`. Bản đồ: ★ ở NPC, đường tím từng ô (`Story.walk_path`, lưới va chạm + độ cao) từ nhân vật tới cửa/mép/NPC; map đang đứng tìm đường theo VÙNG (`route_from_here`: nút = (map, ô vào), loang `Story.reach`, qua mép theo offset lối nối, qua cửa theo ô cửa đích; ô kích hoạt đòi vật phẩm chưa có = tường, `gate_block`/`Story.item_gates`), map khác dùng `route_path`; chữ không còn hướng. Công tắc ⚙ `quest_guide`. Chỉ đường săn (hunt_goal) được ưu tiên. NPC đứng trên đường (RAM gObjectEvents) -> đường vòng; không vòng được thì ✖ đỏ + báo việc làm NPC rời đi (`Story.flag_setters`: chỗ script bật cờ ẩn của NPC). Bước 16 (gym Wattson) không có đường đi bộ (hàng rào điện). ✅ Duy đã thấy đường tím trên tool thật (11/11, ảnh tới cửa bảo tàng).
**Chia EXP cả đội + kho PC, tự tiến hoá (11/11, Duy chốt, công tắc ⚙ `box_exp`):** con KHÔNG ra trận (đội + kho) nhận phần Exp. Share Gen 3 (EXP gốc x lv/7/2, Lucky Egg/trainer/đổi tay x1.5; battle_script_commands.c:3310-3392) cho mỗi đối thủ bị hạ (bắt được = 0 EXP); ghi khi đã về bản đồ (đội write_mon, kho write_box); lên level thì tiến hoá theo pokemon.c:5513-5579 (level, Atk/Def, Wurmple PID, Nincada, thân thiết ≥220; bỏ ngày/đêm, Beauty, Shedinja; Everstone chặn). Không học chiêu mới khi lên level/tiến hoá. ☐ Chưa chạy thật.
**☐ Chưa dò:** roamer Latios/Latias (game tự thả khi nói chuyện mẹ sau Đại sảnh Danh vọng, players_house.inc:438-446).
**☐ Máy nhà:** chưa nối. **☐ Chưa có `so_do/`.**
