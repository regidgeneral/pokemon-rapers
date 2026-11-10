-- Cầu nối mGBA <-> Pokémon Tool AowVN (Python). Nạp 1 lần trong Tools > Scripting > File > Load script.
-- Giao thức qua file trong thư mục IPC (không dùng socket):
--   cmd.txt : dòng 1 = id; các dòng sau: "R <addr_hex> <len>" hoặc "W <addr_hex> <hex bytes>"
--             "K <mask_hex> <số khung>" = xếp hàng giữ phím (mask 0 = chờ), "S 0 0" = hỏi còn bao nhiêu khung phím
--             "A <gTasks_hex> <hàm_task_hex> <bước,bước>" = tự bấm A ngay trong khung hình task đó tới bước đã nêu
--             (câu cá: "Oh! A bite!" chỉ chờ ~30 khung, fast forward thì Python không kịp); "A 0 0 0" = tắt. Trả "1".
--             "N <con trỏ lệnh_hex> <biến bước_hex> <mã lệnh_hex>" = mỗi khung hình: lệnh battle script đang chạy là mã đó
--             (0xF3 trygivecaughtmonnick) và bước <= 1 thì ghi bước = 4 (như bấm B: không đặt biệt danh); "N 0 0 0" = tắt.
--   resp.txt: dòng 1 = id; dòng 2 = OK hoặc ERR <lý do>; rồi mỗi lệnh R / S một dòng
-- Phím GBA: A=1 B=2 Select=4 Start=8 Phải=0x10 Trái=0x20 Lên=0x40 Xuống=0x80 R=0x100 L=0x200 (cộng với phím thật).
-- Cho đọc/ghi EWRAM (0x02000000-0x0203FFFF) và IWRAM (0x03000000-0x03007FFF); ROM (0x08000000-0x09FFFFFF) chỉ đọc.
-- Thư mục tool = thư mục chứa chính file này (mang sang máy/ổ khác không phải sửa); không lấy được thì dùng mặc định.
local function scriptDir()
	local ok, src = pcall(function() return debug.getinfo(1, "S").source end)
	if ok and src and src:sub(1, 1) == "@" then
		local d = src:sub(2):match("^(.*[\\/])")
		if d then return d end
	end
	return "E:\\PokemonRapers\\tool\\"
end
local DIR = scriptDir()
local IPC = DIR .. "ipc\\"
local POLL_EVERY = 3        -- số khung hình giữa 2 lần kiểm tra file lệnh
local lastId = nil
local frameCount = 0
local keyQueue, keyCur = {}, nil     -- hàng phím: {mask, số khung}
local autoA = nil                    -- {tasks, fn, {bước = true}, đã bấm cho lượt này?, số khung còn giữ A}
local skipNick = nil                 -- {instr = địa chỉ gBattlescriptCurrInstr, comm = gBattleCommunication, op = mã lệnh}

local function inRange(addr, len, isWrite)
	if len < 0 or len > 4096 then return false end
	local last = addr + len - 1
	if addr >= 0x02000000 and last <= 0x0203FFFF then return true end
	if addr >= 0x03000000 and last <= 0x03007FFF then return true end
	-- ROM chỉ cho đọc (để công cụ nhận ra game qua header ROM)
	if not isWrite and addr >= 0x08000000 and last <= 0x09FFFFFF then return true end
	return false
end

local function readHex(addr, len)
	local t = {}
	for i = 0, len - 1 do t[#t + 1] = string.format("%02x", emu:read8(addr + i)) end
	return table.concat(t)
end

local function writeHex(addr, hex)
	local n = 0
	for i = 1, #hex - 1, 2 do
		emu:write8(addr + n, tonumber(hex:sub(i, i + 1), 16))
		n = n + 1
	end
	return n
end

local function handle(text)
	local lines = {}
	for l in text:gmatch("[^\r\n]+") do lines[#lines + 1] = l end
	if #lines == 0 then return nil end
	local id = lines[1]
	if id == lastId then return nil end
	lastId = id
	local out = { id, "OK" }
	-- "C địa_chỉ cũ mới": chỉ ghi khi MỌI vùng C còn đúng byte cũ (kiểm hết trước, rồi mới ghi, trong cùng khung hình).
	-- Game FR giải mã Pokémon tại chỗ rồi mã hoá lại; ghi chen vào giữa thì game XOR lên byte mới = hỏng (Metapod 09/11).
	local cas = {}
	for i = 2, #lines do
		local a, o, n = lines[i]:match("^C%s+(%x+)%s+(%x+)%s+(%x+)$")
		if a then
			local addr = tonumber(a, 16)
			if #o ~= #n or #o % 2 ~= 0 or not inRange(addr, #o // 2, true) then return id .. "\nERR range " .. lines[i] end
			if readHex(addr, #o // 2) ~= o:lower() then return id .. "\nOK\n0" end
			cas[i] = { addr, n }
		end
	end
	for i = 2, #lines do
		local op, a, b = lines[i]:match("^(%a)%s+(%x+)%s+(%S+)")
		if cas[i] then op = "C" end
		local addr = a and tonumber(a, 16)
		if op == "R" then
			local len = tonumber(b)
			if not (addr and len and inRange(addr, len)) then out[2] = "ERR range " .. lines[i]; break end
			out[#out + 1] = readHex(addr, len)
		elseif op == "W" then
			if not (addr and b and #b % 2 == 0 and inRange(addr, #b // 2, true)) then out[2] = "ERR range " .. lines[i]; break end
			writeHex(addr, b)
		elseif op == "C" then
			writeHex(cas[i][1], cas[i][2])
		elseif op == "K" then
			local n = tonumber(b)
			if not (addr and n and n > 0 and n <= 600 and addr < 0x400) then out[2] = "ERR key " .. lines[i]; break end
			keyQueue[#keyQueue + 1] = { addr, n }
		elseif op == "A" then
			local fn, steps = lines[i]:match("^A%s+%x+%s+(%x+)%s+(%S+)")
			if not addr or addr == 0 then
				if autoA and autoA.hold > 0 then emu:clearKeys(1) end
				autoA = nil
			else
				if not (inRange(addr, 16 * 40) and fn and steps) then out[2] = "ERR auto " .. lines[i]; break end
				local set = {}
				for s in steps:gmatch("%d+") do set[tonumber(s)] = true end
				autoA = { tasks = addr, fn = tonumber(fn, 16), steps = set, done = false, hold = 0 }
			end
			out[#out + 1] = "1"
		elseif op == "N" then
			local comm, code = lines[i]:match("^N%s+%x+%s+(%x+)%s+(%x+)")
			if not addr or addr == 0 then
				skipNick = nil
			else
				local c = comm and tonumber(comm, 16)
				if not (inRange(addr, 4, true) and c and inRange(c, 1, true) and code) then out[2] = "ERR nick " .. lines[i]; break end
				skipNick = { instr = addr, comm = c, op = tonumber(code, 16) }
			end
			out[#out + 1] = "1"
		elseif op == "S" then
			local left = keyCur and keyCur[2] or 0
			for _, k in ipairs(keyQueue) do left = left + k[2] end
			out[#out + 1] = tostring(left)
		else
			out[2] = "ERR cmd " .. lines[i]; break
		end
	end
	if next(cas) and out[2] == "OK" then out[#out + 1] = "1" end
	return table.concat(out, "\n")
end

local function keyTick()             -- chạy mỗi khung hình: giữ phím đầu hàng đủ số khung rồi nhả
	if keyCur == nil then
		if #keyQueue == 0 then return end
		keyCur = table.remove(keyQueue, 1)
		if keyCur[1] ~= 0 then emu:addKeys(keyCur[1]) end
	end
	keyCur[2] = keyCur[2] - 1
	if keyCur[2] <= 0 then
		if keyCur[1] ~= 0 then emu:clearKeys(keyCur[1]) end
		keyCur = nil
	end
end

local function autoTick()           -- mỗi khung hình: task câu cá tới bước chờ A -> bấm A 2 khung, một lần mỗi lượt
	if not autoA then return end
	if autoA.hold > 0 then
		autoA.hold = autoA.hold - 1
		if autoA.hold == 0 then emu:clearKeys(1) end
		return
	end
	local inStep = false
	for i = 0, 15 do
		local t = autoA.tasks + 40 * i
		if emu:read8(t + 4) ~= 0 and emu:read32(t) == autoA.fn and autoA.steps[emu:read16(t + 8)] then
			inStep = true
			break
		end
	end
	if not inStep then
		autoA.done = false           -- rời bước chờ: lượt sau (vòng chấm mới / lần câu mới) được bấm lại
	elseif not autoA.done then
		emu:addKeys(1)
		autoA.hold, autoA.done = 2, true
	end
end

local function nickTick()           -- mỗi khung hình: câu hỏi đặt biệt danh sau khi bắt -> bỏ qua (bước = 4)
	if not skipNick then return end
	local p = emu:read32(skipNick.instr)
	if p >= 0x08000000 and p < 0x0A000000 and emu:read8(p) == skipNick.op and emu:read8(skipNick.comm) <= 1 then
		emu:write8(skipNick.comm, 4)
	end
end

local function poll()
	keyTick()
	autoTick()
	nickTick()
	frameCount = frameCount + 1
	if frameCount % POLL_EVERY ~= 0 then return end
	local f = io.open(IPC .. "cmd.txt", "rb")
	if not f then return end
	local text = f:read("*a")
	f:close()
	local resp = handle(text)
	if resp then
		local g = io.open(IPC .. "resp.txt", "wb")
		if g then
			g:write(resp .. "\nEND")
			g:close()
		end
	end
end

-- Nạp lại script (File > Load script / dofile) thì gỡ vòng cũ, tránh 2 vòng cùng trả lời và cùng bấm phím
if _G.mm_bridge_cb then pcall(function() callbacks:remove(_G.mm_bridge_cb) end) end
_G.mm_bridge_cb = callbacks:add("frame", poll)
console:log("mm_bridge: san sang, thu muc tool: " .. DIR)
-- Tự mở tool mỗi lần nạp script (đóng tool rồi nạp lại là mở lại); tool đang chạy thì bản mới tự thoát.
-- pyw = không hiện cửa sổ đen; "start" để mGBA không bị treo chờ.
-- "-3" = bản Python 3 mới nhất trên máy (công ty 3.11, nhà 3.12), khỏi sửa theo từng máy.
local home = (DIR:gsub("[\\/]$", ""))
local ok = pcall(os.execute, 'start "" /D "' .. home .. '" pyw -3 mm_gui.py')
if ok then
	console:log("mm_bridge: da mo tool.")
else
	console:log("mm_bridge: khong tu mo duoc tool, hay chay Mo_Tool.bat.")
end
