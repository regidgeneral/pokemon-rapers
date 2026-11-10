"""Pokémon Tool (AowVN) - giao diện. Chạy cạnh mGBA (đã nạp mm_bridge.lua):  py -3 mm_gui.py
Thử không cần game:  py -3 mm_gui.py --fake"""
import base64, io, json, os, struct, sys, time, traceback, types
import tkinter as tk
from collections import Counter
from tkinter import ttk, messagebox
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mm_core import *
import mm_items
import save_sync

PAD = dict(padx=4, pady=2)


def catch_level(rate):
    """Chỉ số bắt gốc của loài (0-255, cao = dễ) -> mức độ, vd 'Rất dễ (235)'."""
    for lo, t in ((200, 'Rất dễ'), (120, 'Dễ'), (60, 'Trung bình'), (30, 'Khó'), (10, 'Rất khó')):
        if rate >= lo:
            return '%s (%d)' % (t, rate)
    return 'Cực khó (%d)' % rate


def hp_color(hp, maxhp):
    """Màu thanh máu như trong game: xanh > 50%, vàng > 20%, đỏ còn lại."""
    r = hp / maxhp if maxhp else 0
    return '#2fb84f' if r > 0.5 else '#e8b400' if r > 0.2 else '#e03a2f'


def hp_text(hp, maxhp, cells=8):
    """Thanh máu bằng chữ cho cột HP: '██████░░ 43/57'."""
    n = 0 if not maxhp or hp <= 0 else max(1, round(cells * hp / maxhp))
    return '%s%s %d/%d' % ('█' * n, '░' * (cells - n), hp, maxhp)


STATUS_NAMES = ((0x7, 'Ngủ'), (0x8, 'Độc'), (0x10, 'Bỏng'), (0x20, 'Đóng băng'), (0x40, 'Tê liệt'), (0x80, 'Độc nặng'))


def status_text(st):
    return ', '.join(t for bit, t in STATUS_NAMES if st & bit)


IV_GRADES = ['Thường', 'Tạm', 'Nên bắt', 'Tuyệt vời']


def iv_grade(iv, base):
    """Đánh giá IV theo 5 chỉ số có ích: bỏ chỉ số tấn công không dùng (Atk vs SpA theo chỉ số gốc của loài).
    Trả (mức 0..3, tổng có ích, chỉ số tấn công chính 'Atk'/'SpA'). Thứ tự: HP Atk Def Spe SpA SpD."""
    phys = base[1] >= base[4]
    main, off = (1, 4) if phys else (4, 1)
    useful = sum(v for k, v in enumerate(iv) if k != off)
    pct = useful / 155
    g = 3 if pct >= 0.9 else 2 if pct >= 0.75 else 1 if pct >= 0.55 else 0
    if iv[main] < 20 and g > 0:                       # tấn công chính yếu -> hạ một mức
        g -= 1
    return g, useful, 'Atk' if phys else 'SpA'


def parse_id(text, values):
    """'271 - Assist' -> 271; hoặc gõ số / tên."""
    t = text.strip()
    head = t.split(' - ')[0].strip()
    if head.lstrip('-').isdigit():
        return int(head)
    low = t.lower()
    for v in values:
        if v.lower().split(' - ', 1)[-1] == low:
            return int(v.split(' - ')[0])
    raise ValueError('không hiểu "%s"' % text)


class Tip:
    """Chữ giải thích hiện khi rê chuột lên widget (thay cho các đoạn giải thích dài luôn chiếm chỗ)."""
    def __init__(self, widget, text):
        self.w, self.text, self.win, self.job = widget, text, None, None
        widget.bind('<Enter>', self._sched, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')

    def _sched(self, e=None):
        self._hide()
        self.job = self.w.after(450, self._show)

    def _show(self):
        self.job = None
        x, y = self.w.winfo_pointerx() + 14, self.w.winfo_pointery() + 18
        self.win = tk.Toplevel(self.w)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        tk.Label(self.win, text=self.text, justify='left', wraplength=420, background='#ffffe0', relief='solid',
                 borderwidth=1, padx=6, pady=4, font=('Segoe UI', 9)).pack()
        self.win.geometry('+%d+%d' % (x, y))

    def _hide(self, e=None):
        if self.job:
            self.w.after_cancel(self.job)
            self.job = None
        if self.win:
            self.win.destroy()
            self.win = None


def info_icon(parent, text):
    """Dấu ⓘ nhỏ, rê chuột vào để đọc giải thích."""
    lb = ttk.Label(parent, text='ⓘ', foreground='#1565c0', cursor='question_arrow', font=('Segoe UI', 11, 'bold'))
    Tip(lb, text)
    return lb


class SearchCombo(ttk.Combobox):
    """Ô gõ tên: vừa gõ là tự xổ danh sách gợi ý (không cướp focus). Mũi tên lên/xuống chọn, Enter hoặc Tab
    nhận gợi ý đang sáng, bấm chuột vào gợi ý cũng được. Chọn xong phát <<ComboboxSelected>>."""
    ROWS = 8
    SKIP = ('Up', 'Down', 'Return', 'Tab', 'ISO_Left_Tab', 'Escape', 'Left', 'Right', 'Home', 'End',
            'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R')

    def __init__(self, master, values, width=26, label=None, on_browse=None, icon=None, **kw):
        super().__init__(master, values=values, width=width, **kw)
        self.all = list(values)
        self._label = label or (lambda v: v)          # chữ hiện trong danh sách gợi ý (giá trị chọn vẫn là v)
        self._icon = icon                             # icon(v) -> PhotoImage | None: danh sách gợi ý có hình
        self._fill = None
        if icon:                                      # mũi tên: mở danh sách có hình thay cho danh sách gốc
            self.bind('<Button-1>', self._arrow, add='+')
        self._pop = self._lb = None
        self._matches = []
        self.bind('<KeyRelease>', self._on_key, add='+')
        self.bind('<KeyPress-Down>', lambda e: self._move(1))
        self.bind('<KeyPress-Up>', lambda e: self._move(-1))
        self.bind('<Return>', self._accept)
        self.bind('<Tab>', self._tab)
        self.bind('<Escape>', lambda e: self._hide())
        self.bind('<FocusOut>', lambda e: self.after(150, self._hide_away), add='+')
        self.bind('<Unmap>', lambda e: self._hide(), add='+')
        self.bind('<<ComboboxSelected>>', lambda e: self._hide(), add='+')
        if on_browse:
            self._hook_popdown(on_browse)

    def _hook_popdown(self, cb):
        """Danh sách gốc (nút mũi tên): dòng đang sáng đổi (phím lên/xuống, rê chuột) -> cb(giá trị); đóng -> cb(None)."""
        pd = self.tk.call('ttk::combobox::PopdownWindow', self)
        lb = '%s.f.l' % pd

        def cur():
            sel = self.tk.splitlist(self.tk.call(lb, 'curselection'))
            vals = self.tk.splitlist(self.cget('values'))
            if sel and int(sel[0]) < len(vals):
                cb(str(vals[int(sel[0])]))

        c1, c2 = self.register(lambda *a: self.after_idle(cur)), self.register(lambda *a: cb(None))
        for ev in ('<<ListboxSelect>>', '<KeyRelease>', '<Motion>'):
            self.tk.call('bind', lb, ev, '+' + c1)
        self.tk.call('bind', pd, '<Unmap>', '+' + c2)

    # --- gợi ý
    def _find(self, text):
        t = text.strip().lower()
        if not t:
            return []
        starts, contains = [], []
        for v in self.all:
            low = v.lower()
            if low.split(' - ', 1)[-1].startswith(t) or low.startswith(t):
                starts.append(v)
            elif t in low:
                contains.append(v)
        return (starts + contains)[:200]

    def _on_key(self, ev):
        if ev.keysym in self.SKIP:
            return
        self._show(self.get())

    def _arrow(self, ev):
        if 'downarrow' not in str(self.identify(ev.x, ev.y)):
            return None
        if self._visible():
            self._hide()
        else:
            self.focus_set()
            self._show_list(list(self.all), self.get())
        return 'break'

    def _show(self, text):
        m = self._find(text)
        if not m:
            self._hide()
            return
        if self._icon:
            return self._show_list(m)
        self._matches = m
        if self._pop is None:
            self._pop = tk.Toplevel(self)
            self._pop.withdraw()
            self._pop.overrideredirect(True)
            try:
                self._pop.attributes('-topmost', True)
            except tk.TclError:
                pass
            self._lb = tk.Listbox(self._pop, activestyle='none', exportselection=False, takefocus=0,
                                  highlightthickness=1, relief='solid', borderwidth=0)
            sb = ttk.Scrollbar(self._pop, orient='vertical', command=self._lb.yview)
            self._lb.configure(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y')
            self._lb.pack(side='left', fill='both', expand=True)
            self._lb.bind('<Button-1>', self._click)
        self._lb.delete(0, 'end')
        for v in m:
            self._lb.insert('end', self._label(v))
        self._lb.selection_clear(0, 'end')
        self._lb.selection_set(0)
        self._lb.config(height=min(self.ROWS, len(m)), width=max(28, int(self.winfo_width() / 7), max(len(self._label(v)) for v in m)))
        self._pop.geometry('+%d+%d' % (self.winfo_rootx(), self.winfo_rooty() + self.winfo_height()))
        self._pop.deiconify()
        self._pop.lift()

    def _show_list(self, m, cur=None):
        """Danh sách gợi ý có hình (Treeview). Hình nạp dần từng đợt cho khỏi đứng giao diện khi mở cả danh sách."""
        self._matches = m
        if self._pop is None:
            self._pop = tk.Toplevel(self)
            self._pop.withdraw()
            self._pop.overrideredirect(True)
            try:
                self._pop.attributes('-topmost', True)
            except tk.TclError:
                pass
            ttk.Style(self).configure('Pic.Treeview', rowheight=44, font=('Segoe UI', 10))
            self._lb = ttk.Treeview(self._pop, show='tree', selectmode='browse', style='Pic.Treeview', takefocus=0)
            self._lb.column('#0', width=300)
            sb = ttk.Scrollbar(self._pop, orient='vertical', command=self._lb.yview)
            self._lb.configure(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y')
            self._lb.pack(side='left', fill='both', expand=True)
            self._lb.bind('<ButtonRelease-1>', self._click)
        if self._fill:
            self.after_cancel(self._fill)
        self._lb.delete(*self._lb.get_children())
        for i, v in enumerate(m):
            self._lb.insert('', 'end', iid=str(i), text='  ' + self._label(v))
        i = m.index(cur) if cur in m else 0
        self._sel_set(i)
        self._lb.configure(height=min(self.ROWS, len(m)))
        self._pop.geometry('%dx%d+%d+%d' % (max(320, self.winfo_width()), min(self.ROWS, len(m)) * 44 + 4,
                                            self.winfo_rootx(), self.winfo_rooty() + self.winfo_height()))
        self._pop.deiconify()
        self._pop.lift()

        def fill(order, k=0):                         # dòng đang thấy trước, rồi tới hết danh sách
            for j in order[k:k + 40]:
                if self._lb.exists(str(j)):
                    im = self._icon(m[j])
                    if im:
                        self._lb.item(str(j), image=im)
            self._fill = self.after(15, fill, order, k + 40) if k + 40 < len(order) else None
        near = sorted(range(len(m)), key=lambda j: abs(j - i))
        fill(near)

    def _sel_set(self, i):
        if self._icon:
            self._lb.selection_set(str(i))
            self._lb.see(str(i))
        else:
            self._lb.selection_clear(0, 'end')
            self._lb.selection_set(i)
            self._lb.see(i)

    def _hide(self):
        if self._pop is not None:
            self._pop.withdraw()

    def _hide_away(self):
        try:
            f = self.focus_get()
        except (KeyError, tk.TclError):
            f = None
        if self._pop is not None and f is self._lb:   # đang bấm / lăn trong danh sách có hình: giữ lại
            self.focus_set()
            return
        self._hide()

    def _visible(self):
        return self._pop is not None and self._pop.winfo_viewable()

    def _move(self, d):
        if not self._visible():
            return None                                   # popup đóng: để mũi tên gốc của Combobox lo
        i = max(0, min(len(self._matches) - 1, self._highlighted() + d))
        self._sel_set(i)
        return 'break'

    def _choose(self, i):
        self.set(self._matches[i])
        self.icursor('end')
        self._hide()
        self.event_generate('<<ComboboxSelected>>')

    def _highlighted(self):
        cur = self._lb.selection() if self._icon else self._lb.curselection()
        if self._icon:
            return int(cur[0]) if cur else 0
        return cur[0] if cur else 0

    def _accept(self, ev):
        if self._visible():
            self._choose(self._highlighted())
        else:
            self.event_generate('<<ComboboxSelected>>')   # Enter khi đã gõ đủ: coi như đã chọn
        return 'break'

    def _tab(self, ev):
        if self._visible():
            self._choose(self._highlighted())             # Tab nhận gợi ý rồi chuyển ô như bình thường

    def _click(self, ev):
        if self._icon:
            row = self._lb.identify_row(ev.y)
            if row:
                self._choose(int(row))
            return 'break'
        self._choose(self._lb.nearest(ev.y))
        return 'break'

    def set_id(self, i):
        for v in self.all:
            if int(v.split(' - ')[0]) == i:
                self.set(v)
                return
        self.set(str(i))


class App(tk.Tk):
    def __init__(self, fake=False):
        super().__init__()
        self.geometry('1120x740')
        self.minsize(1080, 700)
        self.bridge = FakeBridge() if fake else Bridge()
        self.fake = fake
        prof = EMERALD
        self.prof = prof
        self.title('Pokémon Tool — %s' % prof.title)
        self.rom = Rom(prof)
        if fake:
            self._load_fake()
        self.game = Game(self.bridge, self.rom)
        self.species_vals = ['%d - %s' % x for x in self.rom.species_list()]
        self.item_vals = ['0 - (không có)'] + ['%d - %s' % x for x in self.rom.item_list()]
        mvs = self.rom.move_list()
        z = next((i for i, n in mvs if n.startswith('Z-Move')), None)   # bỏ Z-Move và Max Move (nằm sau Z-Move)
        mvs = sorted((x for x in mvs if z is None or x[0] < z), key=lambda x: (-self.rom.move_power(x[0]), x[0]))
        self.move_vals = ['0 - (trống)'] + ['%d - %s' % x for x in mvs]   # sức mạnh lớn lên đầu
        self.mons = []
        self.sel = None
        top = ttk.Frame(self)
        top.pack(fill='x', **PAD)
        self.status = ttk.Label(top, text='Chưa kết nối', foreground='gray')
        self.status.pack(side='left')
        ttk.Button(top, text='↻ Làm mới', command=self.refresh_all).pack(side='right')
        b = ttk.Button(top, text='☁ Đồng bộ', command=self.guard(self.do_sync))
        b.pack(side='right', padx=4)
        Tip(b, 'Lấy bản tool mới nhất về (có thì hỏi mở lại tool) + đẩy save đang chơi lên GitHub.\n'
               'Lấy SAVE về thì phải đóng mGBA trước: mở game bằng Choi.bat (tự lấy code + save mới nhất rồi mới mở mGBA).\n'
               'Mỗi lần game lưu, tool tự đẩy save lên (không cần bấm).')
        nb = self.nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, **PAD)
        nb.bind('<<NotebookTabChanged>>', lambda e: self.on_tab())
        self.t_quest, self.t_mon, self.t_box, self.t_bag = (ttk.Frame(nb) for _ in range(4))
        for t, name in ((self.t_quest, '🗺 Bản đồ'), (self.t_mon, '👥 Đội'), (self.t_box, '📦 Kho PC'), (self.t_bag, '🎒 Túi đồ')):
            nb.add(t, text=name)
        self.foe_mons, self.hist, self.seen = [], [], set()
        self.hist_load()
        self._photos = {}
        self.settings_file = os.path.join(HERE, 'settings.json')    # cài đặt nhớ qua các lần mở tool
        try:
            with open(self.settings_file, encoding='utf-8') as fp:
                self.settings = json.load(fp)
        except (OSError, ValueError):
            self.settings = {}
        self.auto_heal = tk.BooleanVar(value=bool(self.settings.get('auto_heal', True)))
        self.box_exp = tk.BooleanVar(value=bool(self.settings.get('box_exp', True)))
        self.shiny_boost = tk.BooleanVar(value=bool(self.settings.get('shiny_boost', True)))
        self.alert_on = tk.BooleanVar(value=bool(self.settings.get('alert', True)))   # báo shiny / nên bắt
        # tool tự thả huyền thoại lang thang (Duy chốt 06/11: mọi huyền thoại kể cả đã bắt, 20 phút/con, tối đa 2, Lv theo đội)
        self.roam_auto = tk.BooleanVar(value=bool(self.settings.get('roam_auto', True)))
        self.roam_timer = float(self.settings.get('roam_timer', 0))          # giây đã chơi kể từ lần thả trước
        self.roam_spawned = list(self.settings.get('roam_spawned', []))     # [[ô, PID]] các con tool đã thả
        self.roam_last = None
        self.shiny_c = None                               # bộ đếm tăng tỉ lệ shiny trong game (AowVN)
        self.was_battle, self.exp_snap, self.exp_msg = False, None, []
        self.tick_err = None
        self.roam_keep = None                              # đang bay tới chỗ huyền thoại để giữ nó lại
        self.q_wild_on = tk.BooleanVar(value=bool(self.settings.get('wild_zone', True)))   # tô vùng có Pokémon
        self.hide_caught = tk.BooleanVar(value=bool(self.settings.get('hide_caught', False)))
        self.fly_origin = self.settings.get('fly_origin')   # [nhóm, số, x, y] chỗ đứng trước lần bay đầu chuyến
        self.fly_landed = self.settings.get('fly_landed')   # [nhóm, số] map tool thả xuống lần bay gần nhất
        # nút Săn ▾: loại sẽ tự bắt (Duy chốt 06/11: tick nhiều ô, IV có ích, mức % tự gõ)
        self.hunt_opt = {k: tk.BooleanVar(value=bool(self.settings.get('hunt_' + k, True)))
                         for k in ('shiny', 'iv', 'dex', 'legend')}
        self.hunt_iv_pct = int(self.settings.get('hunt_iv_pct', 70))
        self.hunt_target = self.settings.get('hunt_target')   # số loài đang săn theo loài, None = không
        # săn theo loài: chỉ bắt con shiny của loài đó (Duy 07/11: "tưởng đang canh bắt shiny Pikachu")
        self.hunt_target_shiny = tk.BooleanVar(value=bool(self.settings.get('hunt_target_shiny', False)))
        self.hunt_mute = tk.BooleanVar(value=bool(self.settings.get('hunt_mute', True)))   # tắt tiếng mGBA khi săn
        self.muted_by_tool = bool(self.settings.get('muted_by_tool', False))   # tool đang giữ mGBA tắt tiếng
        if self.muted_by_tool:                                # lần trước tool tắt mà chưa kịp bật lại (đóng đột ngột)
            self.after(500, lambda: self.hunt_sound(True))
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        g0 = self.settings.get('hunt_goal')                   # [nhóm, số] map đang chỉ đường tới, None = không
        self.hunt_goal = tuple(g0) if g0 else None
        self._build_settings_menu(top)
        self._build_mon()
        self._load_shiny_count()
        self.htrees = []                                   # bảng Lịch sử đã gặp (tab Bản đồ)
        self._build_box()
        self._build_bag()
        self._build_quest()
        self.after(200, self.refresh_all)
        self.after(1500, self.tick_field)
        if not fake:
            self.after(5000, self.tick_save_sync)

    def _build_settings_menu(self, top):
        """Nút ⚙ trên thanh trên cùng: mọi cài đặt của tool ở một chỗ, đều lưu vào settings.json."""
        mb = ttk.Menubutton(top, text='⚙ Cài đặt')
        mb.pack(side='right', padx=(0, 6))
        m = tk.Menu(mb, tearoff=0)
        mb['menu'] = m
        save = self.save_area_state
        m.add_checkbutton(label='Tự hồi phục cả đội sau mỗi trận', variable=self.auto_heal, command=save)
        m.add_separator()
        m.add_checkbutton(label='Báo khi gặp shiny / nên bắt (kêu + khung nổi, không lấy phím của mGBA)',
                          variable=self.alert_on, command=save)
        m.add_command(label='     Thử báo', command=lambda: self.alert('★ SHINY: thử', 'Đây là thông báo thử',
                                                                        types.SimpleNamespace(species=25), shiny=True))
        m.add_separator()
        m.add_checkbutton(label='Tô vùng có Pokémon trên bản đồ', variable=self.q_wild_on,
                          command=lambda: (save(), self.guard(self.quest_render)()))

    # ------------------------------------------------------------ tiện ích
    def photo(self, sp, shiny=False, scale=1.0):
        """Ảnh Pokémon cho tkinter (đã phóng bằng NEAREST); None nếu chưa có ảnh."""
        key = (sp, bool(shiny), scale)
        if key not in self._photos:
            im = self.rom.sprite(sp, shiny) if 1 <= sp <= self.rom.max_species else None
            if im is None:
                self._photos[key] = None
            else:
                from PIL import Image
                w = int(64 * scale)
                buf = io.BytesIO()
                im.resize((w, w), Image.NEAREST).save(buf, 'PNG')
                self._photos[key] = tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
        return self._photos[key]

    def on_tab(self):
        """Chuyển sang tab nào thì đọc lại dữ liệu của tab đó từ game (tab Bản đồ còn tự làm mới theo nhịp 1 giây)."""
        cur = self.nb.nametowidget(self.nb.select())
        fn = {self.t_bag: self.open_bag, self.t_mon: self.refresh_party, self.t_box: self.refresh_box,
              self.t_quest: lambda: self.quest_tick(force=True)}.get(cur)
        if fn:
            self.guard(fn)()

    def alert(self, title, sub, m, shiny, sticky=False):
        """Báo gặp shiny / nên bắt khi đang nhìn mGBA: kêu + khung nổi trên mọi cửa sổ ở giữa phía trên màn hình.
        Khung không lấy focus (WS_EX_NOACTIVATE) nên phím vẫn vào mGBA; bấm vào khung để đóng.
        Nên bắt tự tắt sau 10 giây, shiny / sticky (huyền thoại mới) giữ tới khi bấm."""
        if not self.alert_on.get():
            return
        import threading
        try:
            import winsound
            tones = ((880, 140), (1175, 140), (1568, 260)) * 2 if shiny else ((660, 120), (988, 220))
            threading.Thread(target=lambda: [winsound.Beep(f, d) for f, d in tones], daemon=True).start()
        except Exception:
            pass
        old = getattr(self, '_alert_win', None)
        if old is not None and old.winfo_exists():
            old.destroy()
        fg = None
        try:
            import ctypes
            u32 = ctypes.windll.user32
            fg = u32.GetForegroundWindow()
        except Exception:
            u32 = None
        bg, fc = ('#d49a00', 'white') if shiny else ('#1b7f2a', 'white')
        w = self._alert_win = tk.Toplevel(self)
        w.withdraw()
        w.overrideredirect(True)
        w.attributes('-topmost', True)
        box = tk.Frame(w, background=bg, padx=18, pady=10, highlightthickness=3, highlightbackground='white')
        box.pack()
        ph = self.photo(m.species, shiny, 1.0) if m else None
        if ph:
            tk.Label(box, image=ph, background=bg).pack(side='left', padx=(0, 12))
        tx = tk.Frame(box, background=bg)
        tx.pack(side='left')
        tk.Label(tx, text=title, font=('Segoe UI', 20, 'bold'), foreground=fc, background=bg).pack(anchor='w')
        tk.Label(tx, text=sub + '   (bấm để đóng)', font=('Segoe UI', 11), foreground=fc, background=bg).pack(anchor='w')
        for wd in [w, box, tx] + list(box.winfo_children()) + list(tx.winfo_children()):
            wd.bind('<Button-1>', lambda e: w.destroy())
        w.update_idletasks()
        w.geometry('+%d+%d' % ((w.winfo_screenwidth() - w.winfo_reqwidth()) // 2, 40))
        if u32:
            try:                                            # không lấy focus, không hiện trên thanh taskbar
                h = u32.GetParent(w.winfo_id()) or w.winfo_id()
                u32.SetWindowLongW(h, -20, u32.GetWindowLongW(h, -20) | 0x08000000 | 0x80)
            except Exception:
                pass
        w.deiconify()
        w.lift()
        if u32 and fg:
            try:
                if u32.GetForegroundWindow() != fg:         # lỡ bị lấy focus thì trả lại cho mGBA
                    u32.SetForegroundWindow(fg)
            except Exception:
                pass
        if not (shiny or sticky):
            w.after(10000, lambda: w.winfo_exists() and w.destroy())

    def say(self, text, ok=True):
        self.status.config(text=text, foreground='#0a7d2c' if ok else '#b00020')

    def guard(self, fn):
        def run(*a):
            try:
                fn(*a)
            except BridgeError as e:
                self.say('Lỗi: %s' % e, False)
            except ValueError as e:
                self.say('Giá trị sai: %s' % e, False)
        return run

    def _load_fake(self):
        """Dữ liệu giả để thử giao diện mà không cần mGBA (theo hồ sơ game đang chọn)."""
        p, b = self.prof, self.bridge
        sb1, sb2 = 0x02026DEC, 0x02025E04
        b.write(p.sb1_ptr, struct.pack('<I', sb1))
        b.write(p.sb2_ptr, struct.pack('<I', sb2))
        b.write(sb2 + p.key_off, struct.pack('<I', 0x1234ABCD))
        b.write(sb1 + p.money_off, struct.pack('<I', 5000 ^ 0x1234ABCD))
        for i in range(p.n_pockets):
            # túi giả ở 0x02032000: ngoài SaveBlock1 giả (Emerald: cờ ở sb1 + 0x1270 = 0x0202805C) và kho giả
            b.write(p.pockets_addr + 8 * i, struct.pack(p.pocket_fmt, 0x02032000 + 0x400 * i, 30).ljust(8, b'\0'))
        wm = self.rom.wild_maps()
        g, n = next(((a, c) for a, c, nm in wm if nm == 'ROUTE 1'), wm[0][:2])
        b.write(sb1 + p.loc_off, bytes([g, n]))
        # FireRed: đội + kho giả mã hoá như thật (khi chưa có save)
        st = 0x02029314
        b.write(p.storage_ptr, struct.pack('<I', st))
        r, otid = self.rom, 0x0BAD1234

        def fake_mon(sp, lv, pid):
            dec = bytearray(MON_SIZE)
            struct.pack_into('<II', dec, 0, pid, otid)
            dec[8:18] = r.species_name_bytes(sp)
            dec[0x14:0x1B] = bytes([0xC8, 0xBF, 0xBE, 0xFF, 0xFF, 0xFF, 0xFF])
            struct.pack_into('<HHI', dec, 0x20, sp, 0, r.exp_for(r.growth(sp), lv))
            struct.pack_into('<4H', dec, 0x2C, 33, 45, 0, 0)
            struct.pack_into('<I', dec, 0x48, pid * 2654435761 & 0x3FFFFFFF)
            dec[0x55] = 0xFF
            m = FrMon(fr_encrypt(dec))
            m.recalc(r)
            m.full_restore(r)
            return m.to_bytes()
        b.write(sb2 + 0xA, struct.pack('<I', otid))
        b.write(p.cb2_addr, struct.pack('<I', p.cb2_overworld))     # giả như đang đi trên bản đồ
        team = [fake_mon(sp, lv, 0x1000 * sp + 7) for sp, lv in ((6, 36), (25, 22), (131, 30))]
        b.write(p.party_base, b''.join(team).ljust(MON_SIZE * PARTY_SLOTS, b'\0'))
        b.write(p.party_count, bytes([len(team)]))
        b.write(p.enemy_base, fake_mon(16, 4, 0x777))
        b.write(st + 4, b''.join(fake_mon(sp, 5 + sp % 20, 0x3000 + sp)[:BOX_MON_SIZE] for sp in (1, 4, 7, 16, 19, 25, 25)))
        # (FR: không đọc đội từ file save như bản AowVN, để bài thử dev\ luôn chạy trên cùng dữ liệu giả)

    # ------------------------------------------------------------ tab Pokémon
    def _build_mon(self):
        f = self.t_mon
        left = ttk.Frame(f)
        left.pack(side='left', fill='y', **PAD)
        self.tree = ttk.Treeview(left, columns=('slot', 'name', 'lv', 'hp', 'shiny'), show='headings', height=8)
        for c, w, t in (('slot', 30, '#'), ('name', 110, 'Loài'), ('lv', 36, 'Lv'), ('hp', 180, 'HP'), ('shiny', 44, 'Shiny')):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor='center')
        self.tree.tag_configure('hurt', foreground='#b00020')            # còn thiếu máu / có trạng thái
        self.tree.pack(fill='y', expand=True)
        self.tree.bind('<<TreeviewSelect>>', lambda e: self.on_select())
        self.drag_reorder(self.tree, self.party_move, lambda: sum(not m.empty for m in self.mons))
        Tip(self.tree, 'Kéo thả một dòng để đổi vị trí trong đội (khi đang đi trên bản đồ).')
        ttk.Button(left, text='♥ Hồi phục cả đội (như Trung tâm)', command=self.guard(lambda: self.heal_slots(range(PARTY_SLOTS)))
                   ).pack(fill='x', pady=(4, 0))
        right = ttk.Frame(f)
        right.pack(side='left', fill='both', expand=True, **PAD)
        itop = ttk.Frame(right)
        itop.pack(fill='x')
        self.pk_img = ttk.Label(itop)
        self.pk_img.pack(side='left', padx=(0, 10))
        self.info = ttk.Label(itop, text='Chọn một Pokémon bên trái', justify='left')
        self.info.pack(side='left', anchor='w')
        hpf = ttk.Frame(right)                                           # thanh máu (tự cập nhật mỗi giây)
        hpf.pack(fill='x', pady=(2, 0))
        ttk.Label(hpf, text='HP', font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(4, 6))
        self.hp_bar = tk.Canvas(hpf, width=240, height=14, highlightthickness=1, highlightbackground='#888', bg='#ddd')
        self.hp_bar.pack(side='left')
        self.hp_lbl = ttk.Label(hpf, text='', width=26)
        self.hp_lbl.pack(side='left', padx=6)
        hb = ttk.Button(hpf, text='♥ Hồi phục con này', command=self.guard(lambda: self.heal_slots([self.sel])))
        hb.pack(side='left')
        Tip(hb, 'Hồi đầy HP, PP và bỏ trạng thái. Dùng ngoài trận.')
        g = ttk.LabelFrame(right, text='Cơ bản')
        g.pack(fill='x', pady=3)
        self.species = SearchCombo(g, self.species_vals, icon=self.species_icon)
        self.species.bind('<<ComboboxSelected>>', lambda e: self.preview_species(), add='+')
        self.level = tk.IntVar(value=1)
        self.friend = tk.IntVar(value=0)
        self.item = SearchCombo(g, self.item_vals)
        self.shiny = tk.BooleanVar(value=False)
        for r, (t, w) in enumerate((('Loài', self.species), ('Vật cầm', self.item))):
            ttk.Label(g, text=t).grid(row=r, column=0, sticky='e', **PAD)
            w.grid(row=r, column=1, sticky='w', **PAD)
        ttk.Label(g, text='Level').grid(row=0, column=2, sticky='e', **PAD)
        ttk.Spinbox(g, from_=1, to=100, width=5, textvariable=self.level).grid(row=0, column=3, **PAD)
        ttk.Label(g, text='Thân thiết').grid(row=1, column=2, sticky='e', **PAD)
        ttk.Spinbox(g, from_=0, to=255, width=5, textvariable=self.friend).grid(row=1, column=3, **PAD)
        ttk.Checkbutton(g, text='Shiny', variable=self.shiny).grid(row=0, column=4, **PAD)
        ttk.Label(g, text='Tính cách').grid(row=2, column=0, sticky='e', **PAD)
        self.nature = ttk.Combobox(g, state='readonly', width=26, values=[nature_label(n) for n in range(25)])
        self.nature.grid(row=2, column=1, sticky='w', **PAD)
        s = ttk.LabelFrame(right, text='IV (0-31) và EV (0-255)')
        s.pack(fill='x', pady=3)
        self.iv = [tk.IntVar() for _ in range(6)]
        self.ev = [tk.IntVar() for _ in range(6)]
        for c, n in enumerate(BaseMon.STAT_NAMES):
            ttk.Label(s, text=n).grid(row=0, column=c + 1)
            ttk.Spinbox(s, from_=0, to=31, width=5, textvariable=self.iv[c]).grid(row=1, column=c + 1, **PAD)
            ttk.Spinbox(s, from_=0, to=255, width=5, textvariable=self.ev[c], command=self.upd_ev).grid(row=2, column=c + 1, **PAD)
        ttk.Label(s, text='IV').grid(row=1, column=0)
        ttk.Label(s, text='EV').grid(row=2, column=0)
        self.evtotal = ttk.Label(s, text='Tổng EV: 0 / 510')
        self.evtotal.grid(row=3, column=0, columnspan=4, sticky='w', **PAD)
        bf = ttk.Frame(s)
        bf.grid(row=3, column=4, columnspan=3, sticky='e')
        ttk.Button(bf, text='IV = 31', width=8, command=lambda: self.fill(self.iv, 31)).pack(side='left')
        if self.nature:
            ttk.Button(bf, text='EV theo tính cách', width=16, command=self.guard(self.fill_nature_ev)).pack(side='left')
        ttk.Button(bf, text='EV 85 đều', width=10, command=lambda: self.fill(self.ev, 85)).pack(side='left')
        ttk.Button(bf, text='EV = 0', width=7, command=lambda: self.fill(self.ev, 0)).pack(side='left')
        m = ttk.LabelFrame(right, text='Chiêu thức')
        m.pack(fill='x', pady=3)
        self.moves = [SearchCombo(m, self.move_vals, width=24, label=self.move_label,
                                  on_browse=lambda v, k=k: self.browse_move(k, v)) for k in range(4)]
        self.pp = [tk.IntVar() for _ in range(4)]
        self.mvinfo = [ttk.Label(m, text='', width=30) for _ in range(4)]
        for i in range(4):
            ttk.Label(m, text='%d' % (i + 1)).grid(row=i, column=0, **PAD)
            self.moves[i].grid(row=i, column=1, **PAD)
            ttk.Label(m, text='PP').grid(row=i, column=2)
            ttk.Spinbox(m, from_=0, to=64, width=5, textvariable=self.pp[i]).grid(row=i, column=3, **PAD)
            self.mvinfo[i].grid(row=i, column=4, sticky='w', **PAD)
            for ev in ('<<ComboboxSelected>>', '<KeyRelease>', '<FocusOut>'):
                self.moves[i].bind(ev, lambda e, k=i: self.upd_move(k), add='+')
            self.moves[i].bind('<<ComboboxSelected>>', lambda e, k=i: self.move_pp_max(k), add='+')
        ab = ttk.Button(right, text='ÁP DỤNG vào game', command=self.guard(self.apply))
        ab.pack(fill='x', pady=6)
        Tip(ab, 'Dùng khi đang đi trên bản đồ (không trong trận, không mở menu). Sau đó LƯU GAME để ghi vào .sav.')

    def move_label(self, v):
        """Dòng gợi ý chiêu: '89 - Earthquake   [SM 100 | CX 100]'."""
        i = int(v.split(' - ')[0])
        if i <= 0:
            return v
        pw, ac = self.rom.move_power(i), self.rom.move_accuracy(i)
        return '%s   [SM %s | CX %s]' % (v, pw or '—', ac or '—')

    def move_pp_max(self, k):
        """Vừa chọn chiêu trong ô -> PP = PP tối đa của chiêu đó."""
        try:
            i = parse_id(self.moves[k].get(), self.move_vals)
        except ValueError:
            return
        self.pp[k].set(self.rom.move_pp(i) if i > 0 else 0)

    def browse_move(self, k, v):
        """Đang rê/lướt trong danh sách chiêu: hiện thông số chiêu đang sáng; đóng danh sách thì về chiêu trong ô."""
        if v is None:
            self.upd_move(k)
        else:
            self.show_move(k, int(v.split(' - ')[0]))

    def upd_move(self, k):
        try:
            i = parse_id(self.moves[k].get(), self.move_vals)
        except ValueError:
            return
        self.show_move(k, i)

    def show_move(self, k, i):
        if i <= 0:
            self.mvinfo[k].config(text='')
            return
        pw, ac = self.rom.move_power(i), self.rom.move_accuracy(i)
        self.mvinfo[k].config(text='Sức mạnh: %s    Chính xác: %s' % (pw or '—', ac or '—'))

    def fill(self, vars_, value):
        for v in vars_:
            v.set(value)
        self.upd_ev()

    def fill_nature_ev(self):
        n = self.nature.current()
        if n < 0:
            raise ValueError('chưa chọn Pokémon')
        sp = parse_id(self.species.get(), self.species_vals)
        for v, x in zip(self.ev, nature_ev_spread(n, self.rom.base_stats(sp))):
            v.set(x)
        self.upd_ev()
        self.say('Đã điền EV theo %s, bấm ÁP DỤNG để ghi vào game.' % NATURES[n])

    def upd_ev(self):
        try:
            tot = sum(v.get() for v in self.ev)
        except tk.TclError:
            return
        self.evtotal.config(text='Tổng EV: %d / 510' % tot, foreground='#b00020' if tot > 510 else 'black')

    def drag_reorder(self, tree, on_move, count):
        """Kéo một dòng của tree thả lên dòng khác -> on_move(vị trí cũ, vị trí mới); chỉ trong count() dòng đầu."""
        st = {}
        tree.tag_configure('drop', background='#fff1b8')                 # dòng sắp thả vào
        tree.tag_configure('moved', background='#c9f2cf')                # dòng vừa chuyển (chớp 1,5 giây)
        line = tk.Frame(tree, height=3, background='#1a73e8')            # vạch xanh: chỗ dòng sẽ nằm
        tip = tk.Toplevel(self)                                          # nhãn bay theo chuột
        tip.overrideredirect(True)
        tip.attributes('-topmost', True)
        tip_lbl = tk.Label(tip, background='#1a73e8', foreground='white', padx=8, pady=3, font=('Segoe UI', 9, 'bold'))
        tip_lbl.pack()
        tip.withdraw()

        def tags(row, add=None, drop=None):
            t = [x for x in tree.item(row, 'tags') if x != drop]
            tree.item(row, tags=t + ([add] if add and add not in t else []))

        def clear():
            line.place_forget()
            tip.withdraw()
            if st.get('tgt') and tree.exists(st['tgt']):
                tags(st['tgt'], drop='drop')
            st.pop('tgt', None)

        def target(e):
            """(dòng, vị trí mới) dưới chuột, kẹp trong các dòng có dữ liệu."""
            rows = tree.get_children()[:count()]
            row = tree.identify_row(e.y)
            if not rows:
                return None, None
            if row not in rows:                                          # trên tiêu đề -> đầu; dưới dòng cuối / ô trống -> cuối
                row = rows[0] if e.y < 0 or tree.identify_region(e.x, e.y) == 'heading' else rows[-1]
            return row, tree.index(row)

        def hover(e):                                                    # con trỏ bàn tay = dòng kéo được
            if 'src' not in st:
                row = tree.identify_row(e.y)
                tree.configure(cursor='hand2' if row and tree.index(row) < count() else '')

        def press(e):
            clear()
            st.clear()
            row = tree.identify_row(e.y)
            if row and tree.index(row) < count():
                st['src'], st['name'] = tree.index(row), tree.item(row, 'values')[1]

        def motion(e):
            if 'src' not in st:
                return
            row, dst = target(e)
            if row is None:
                return
            if row != st.get('tgt'):
                clear()
                if dst != st['src']:
                    st['tgt'] = row
                    tags(row, add='drop')
            if dst == st['src']:
                tree.configure(cursor='hand2')
                return
            tree.configure(cursor='fleur')
            x, y, w, h = tree.bbox(row) or (0, 0, 0, 0)
            line.place(x=0, y=y + h - 2 if dst > st['src'] else y - 1, relwidth=1)   # kéo xuống: vạch dưới; kéo lên: vạch trên
            line.lift()
            tip_lbl.config(text='↕ %s  →  vị trí %d' % (st['name'], dst + 1))
            tip.geometry('+%d+%d' % (e.x_root + 16, e.y_root + 8))
            tip.deiconify()

        def release(e):
            tree.configure(cursor='')
            src, name = st.pop('src', None), st.pop('name', '')
            row, dst = target(e) if src is not None else (None, None)
            clear()
            if row is None or dst == src:
                return
            self.guard(on_move)(src, dst)
            rows = tree.get_children()
            if dst < len(rows) and tree.item(rows[dst], 'values')[1] == name:   # chuyển thành công: chớp xanh + nhãn ✔
                tags(rows[dst], add='moved')
                tree.selection_remove(rows[dst])                         # bỏ chọn tạm để thấy màu xanh
                tip_lbl.config(text='✔ %s  →  vị trí %d' % (name, dst + 1), background='#1e8e3e')
                tip.geometry('+%d+%d' % (e.x_root + 16, e.y_root + 8))
                tip.deiconify()

                def done(r=rows[dst]):
                    tip.withdraw()
                    tip_lbl.config(background='#1a73e8')
                    if tree.exists(r):
                        tags(r, drop='moved')
                        if not tree.selection():
                            tree.selection_set(r)
                self.after(1500, done)

        tree.bind('<Motion>', hover, add='+')
        tree.bind('<Leave>', lambda e: 'src' in st or tree.configure(cursor=''), add='+')
        tree.bind('<ButtonPress-1>', press, add='+')
        tree.bind('<B1-Motion>', motion, add='+')
        tree.bind('<ButtonRelease-1>', release, add='+')

    def party_move(self, src, dst):
        name = self.rom.species_name(self.mons[src].species)
        self.game.move_party(src, dst)
        self.sel = dst                                       # form đi theo con vừa chuyển
        self.refresh_party()
        self.on_select()
        self.say('Đã chuyển %s từ vị trí %d tới %d. Nhớ lưu game.' % (name, src + 1, dst + 1))

    def bag_move(self, src, dst):
        idx = self.pocket.current()
        item = self.pocket_items[src][0]
        self.game.move_item(idx, src, dst)
        self.refresh_bag()
        row = self.btree.get_children()[dst]
        self.btree.selection_set(row)
        self.btree.see(row)
        self.say('Đã chuyển %s từ vị trí %d tới %d. Nhớ lưu game.' % (self.rom.item_name(item), src + 1, dst + 1))

    def refresh_party(self):
        self.mons = self.game.party()
        self.tree.delete(*self.tree.get_children())
        for i, m in enumerate(self.mons):
            self.tree.insert('', 'end', iid=str(i), **self.party_row(i, m))
        if self.sel is not None and self.tree.exists(str(self.sel)):
            self.tree.selection_set(str(self.sel))
        self.say('Đã đọc đội từ game.')

    def party_row(self, i, m):
        if m.empty:
            return dict(values=(i + 1, '(trống)', '', '', ''), tags=())
        hurt = m.hp < m.maxhp or m.status
        hp = hp_text(m.hp, m.maxhp) + ('  ' + status_text(m.status) if m.status else '')
        return dict(values=(i + 1, self.rom.species_name(m.species), m.level, hp, '★' if m.is_shiny_in_game() else ''),
                    tags=('hurt',) if hurt else ())

    def draw_hp(self, m):
        c = self.hp_bar
        c.delete('all')
        if m is None or m.empty:
            self.hp_lbl.config(text='')
            return
        w = int(c.cget('width'))
        if m.maxhp and m.hp > 0:
            c.create_rectangle(0, 0, max(2, round(w * m.hp / m.maxhp)), 16, fill=hp_color(m.hp, m.maxhp), width=0)
        st = status_text(m.status)
        self.hp_lbl.config(text='%d / %d%s' % (m.hp, m.maxhp, '   ' + st if st else ''),
                           foreground='#b00020' if st or m.hp < m.maxhp else 'black')

    def tick_party(self):
        """Mỗi giây (khi đang mở tab Đội): cập nhật HP/trạng thái tại chỗ, không đụng các ô đang chỉnh."""
        mons = self.game.party()
        if [m.pid for m in mons] != [m.pid for m in self.mons]:     # đội đổi (bắt thêm, đổi chỗ...) -> tải lại hẳn
            self.refresh_party()
            return
        for i, (old, m) in enumerate(zip(self.mons, mons)):
            if (old.hp, old.maxhp, old.status, old.level) != (m.hp, m.maxhp, m.status, m.level):
                self.tree.item(str(i), **self.party_row(i, m))
                if i == self.sel:
                    self.draw_hp(m)
        self.mons = mons

    def heal_slots(self, slots):
        """Hồi phục như Trung tâm (HP, PP, trạng thái), đọc dữ liệu mới nhất từ game; không ghi các ô đang chỉnh ở form."""
        party = self.game.party()
        done = []
        for i in slots:
            if i is None or not 0 <= i < len(party):
                continue
            m = party[i]
            if m.empty or not m.checksum_ok or not m.full_restore(self.rom):   # checksum sai = đọc trúng lúc game đang giải mã
                continue
            try:
                self.game.write_mon(i, m)
            except ValueError:                               # game đang bận với con này: bỏ qua, lần sau hồi
                continue
            done.append(self.rom.species_name(m.species))
            if i == self.sel:                                # ô PP ở form theo luôn
                for k in range(4):
                    self.pp[k].set(m.pp[k])
        self.tick_party()
        self.say('♥ Đã hồi phục (HP, PP, trạng thái): %s. Nhớ lưu game trong menu.' % ', '.join(done)
                 if done else 'Đã khoẻ hết rồi (đầy HP, PP, không trạng thái).')

    def on_select(self):
        s = self.tree.selection()
        if not s:
            return
        self.sel = int(s[0])
        m = self.mons[self.sel]
        if m.empty:
            self.info.config(text='Ô trống')
            self.pk_img.config(image='')
            self.draw_hp(None)
            return
        self.loaded_pid = m.pid
        self.pk_img.config(image=self.photo(m.species, m.is_shiny_in_game(), 1.0) or '')
        self.species.set_id(m.species)
        self.item.set_id(m.item)
        self.level.set(m.level)
        self.friend.set(m.friendship)
        self.shiny.set(m.is_shiny_in_game())
        if self.nature:
            self.nature.current(m.nature_key())
        self.draw_hp(m)
        for i in range(6):
            self.iv[i].set(m.iv[i])
            self.ev[i].set(m.ev[i])
        for i in range(4):
            self.moves[i].set_id(m.moves[i])
            self.pp[i].set(m.pp[i])
            self.upd_move(i)
        self.upd_ev()
        ab, hidden = self.rom.ability_of(m)
        lock = ''
        self.info.config(text='Tính cách: %s     Ability: %s%s     EXP %d\n'
                              'PID %08X   TID %d  SID %d%s\n'
                              'Chỉ số: HP %d/%d  Atk %d  Def %d  Spe %d  SpA %d  SpD %d' % (
            self.rom.nature_text(m), ab, ' (ẩn)' if hidden else '', m.exp,
            m.pid, m.otid & 0xFFFF, m.otid >> 16, lock,
            m.hp, m.maxhp, m.atk, m.defn, m.spe, m.spa, m.spd))

    def preview_species(self):
        """Chọn loài trong ô là đổi ảnh ngay (chỉ xem trước, chưa ghi vào game)."""
        try:
            sp = parse_id(self.species.get(), self.species_vals)
        except ValueError:
            return
        self.pk_img.config(image=self.photo(sp, self.shiny.get(), 1.0) or '')

    def apply(self):
        if self.sel is None or self.mons[self.sel].empty:
            raise ValueError('chưa chọn Pokémon')
        slot = self.sel
        cur = self.game.party()[slot]
        if cur.empty or cur.pid != self.loaded_pid:
            self.refresh_party()
            raise BridgeError('đội đã thay đổi trong game, hãy chọn lại rồi áp dụng')
        m = cur
        sp = parse_id(self.species.get(), self.species_vals)
        if not 1 <= sp <= self.rom.max_species:
            raise ValueError('loài phải từ 1 đến %d' % self.rom.max_species)
        new_item = parse_id(self.item.get(), self.item_vals)
        lvl = max(1, min(100, int(self.level.get())))
        iv = [max(0, min(31, int(v.get()))) for v in self.iv]
        ev = [max(0, min(255, int(v.get()))) for v in self.ev]
        mv = [parse_id(c.get(), self.move_vals) for c in self.moves]
        changed_stats = (sp != m.species) or iv != m.iv or ev != m.ev
        if self.nature and self.nature.current() != m.nature_key():
            m.set_nature(self.nature.current())
            changed_stats = True
        old_moves = list(m.moves)
        if m.nickname != self.rom.species_name(sp):            # tên luôn theo loài (sửa cả ô đã đổi loài trước đó)
            m.raw[8:18] = self.rom.species_name_bytes(sp)
        m.species, m.item, m.iv, m.ev = sp, new_item, iv, ev
        m.friendship = max(0, min(255, int(self.friend.get())))
        m.moves = mv
        for i in range(4):
            pp = max(0, min(64, int(self.pp[i].get())))
            if mv[i] != old_moves[i] and pp == m.pp[i]:       # đổi chiêu mà không sửa PP -> PP tối đa
                pp = self.rom.move_pp(mv[i]) if mv[i] else 0
            m.pp[i] = pp if mv[i] else 0
        if lvl != m.level:
            m.set_level(self.rom, lvl)
        elif changed_stats:
            m.recalc(self.rom)
        want = self.shiny.get()
        if want != m.is_shiny_in_game():
            m.set_shiny(want)
        self.game.write_mon(slot, m)
        self.refresh_party()
        self.on_select()
        self.say('Đã ghi ô %d (%s). Nhớ lưu game trong menu.' % (slot + 1, self.rom.species_name(m.species)))

    # ------------------------------------------------------------ Pokémon hoang dã, đối thủ, lịch sử
    METHODS = (('land', 'Cỏ cao', LAND_W, (0, 12)),
               ('water', 'Lướt nước (Surf)', WATER_W, (0, 5)),
               ('rock', 'Đập đá (Rock Smash)', ROCK_W, (0, 5)),
               ('fish', 'Cần câu cũ', FISH_W['old'], (0, 2)),
               ('fish', 'Cần câu tốt', FISH_W['good'], (2, 5)),
               ('fish', 'Cần câu siêu', FISH_W['super'], (5, 10)))

    def _load_shiny_count(self):
        """Bộ đếm lần gặp kể từ shiny gần nhất (shiny_count.json theo hồ sơ game)."""
        self.shiny_file = os.path.join(HERE, 'shiny_count.json')
        try:
            with open(self.shiny_file, encoding='utf-8') as fp:
                d = json.load(fp).get(self.prof.key, {})
            self.shiny_n, self.shiny_last = int(d.get('n', 0)), d.get('last')
        except (OSError, ValueError, AttributeError):
            self.shiny_n, self.shiny_last = 0, None

    def save_area_state(self):
        """Lưu mọi cài đặt (nút ⚙ + bộ lọc + đồng hồ huyền thoại) vào settings.json."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as fp:
                json.dump({'hide_caught': self.hide_caught.get(), 'wild_zone': self.q_wild_on.get(),
                           'auto_heal': self.auto_heal.get(), 'box_exp': self.box_exp.get(),
                           'shiny_boost': self.shiny_boost.get(), 'alert': self.alert_on.get(),
                           'roam_auto': self.roam_auto.get(), 'roam_timer': round(self.roam_timer),
                           'roam_spawned': self.roam_spawned, 'fly_origin': self.fly_origin, 'fly_landed': self.fly_landed,
                           'map_zoom': getattr(self, 'q_zoom', None), 'hunt_iv_pct': self.hunt_iv_pct, 'hunt_target': self.hunt_target,
                           'hunt_target_shiny': self.hunt_target_shiny.get(), 'hunt_mute': self.hunt_mute.get(),
                           'muted_by_tool': self.muted_by_tool, 'hunt_goal': self.hunt_goal,
                           **{'hunt_' + k: v.get() for k, v in self.hunt_opt.items()}}, fp, ensure_ascii=False)
        except OSError:
            pass

    def wild_groups(self, wild, caught, tid):
        """[(kiểu, nhãn, chỉ số gặp, [(loài, lv thấp, lv cao, %, đã bắt?)])] từ wild_for_map; Randomizer đã đổi loài,
        chưa bắt xếp trước. Dùng cho tab con 🐾 Pokémon."""
        r, out = self.rom, []
        got = lambda sp: caught is not None and r.natdex(sp) in caught
        for key, label, weights, (a, b) in self.METHODS:
            if key not in wild:
                continue
            rate, slots = wild[key]
            agg = {}
            for (lo, hi, sp), w in zip(slots[a:b], weights):
                if not 1 <= sp <= r.max_species:
                    continue
                if tid is not None:
                    sp = r.randomize_species(sp, tid)
                e = agg.setdefault(sp, [lo, hi, 0])
                e[0], e[1], e[2] = min(e[0], lo), max(e[1], hi), e[2] + w
            if agg:
                rows = sorted(agg.items(), key=lambda kv: (got(kv[0]), -kv[1][2]))   # chưa bắt lên đầu
                out.append((key, label, rate, [(sp, lo, hi, pct, got(sp)) for sp, (lo, hi, pct) in rows]))
        return out

    @staticmethod
    def _scroll_frame(parent):
        """Khung cuộn dọc (canvas + thanh cuộn, lăn chuột khi rê vào): cửa sổ thấp vẫn xem đủ nội dung."""
        cv = tk.Canvas(parent, highlightthickness=0, background=ttk.Style().lookup('TFrame', 'background') or None)
        sb = ttk.Scrollbar(parent, orient='vertical', command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        cv.pack(side='left', fill='both', expand=True)
        inner = ttk.Frame(cv, padding=6)
        win = cv.create_window(0, 0, window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: cv.configure(scrollregion=cv.bbox('all')))
        cv.bind('<Configure>', lambda e: cv.itemconfigure(win, width=e.width))
        wheel = lambda e: cv.yview_scroll(-e.delta // 120 * 3, 'units')
        cv.bind('<Enter>', lambda e: cv.bind_all('<MouseWheel>', wheel))
        cv.bind('<Leave>', lambda e: cv.unbind_all('<MouseWheel>'))
        return inner

    @staticmethod
    def _make_htree(gh, height):
        """Bảng "Lịch sử đã gặp" (chưa pack); thanh cuộn pack bên phải gh."""
        hcols = (('time', 72, 'Giờ'), ('name', 86, 'Loài'), ('lv', 28, 'Lv'), ('shiny', 38, 'Shiny'), ('iv', 44, 'IV'),
                 ('catch', 48, '% bắt'), ('cnt', 90, 'Lần gặp'))
        t = ttk.Treeview(gh, columns=[c[0] for c in hcols], show='headings', height=height)
        for c, w, h in hcols:
            t.heading(c, text=h)
            t.column(c, width=w, anchor='center')
        hsb = ttk.Scrollbar(gh, orient='vertical', command=t.yview)
        t.configure(yscrollcommand=hsb.set)
        hsb.pack(side='right', fill='y')
        t.tag_configure('iv_good', background='#dff3df')
        t.tag_configure('iv_best', background='#a8e0a8')
        return t

    def _build_detail(self, right):
        """Khung chi tiết Pokémon (ảnh, Thông tin, Chỉ số, Chiêu thức); dùng ở tab Bản đồ (Chi tiết) và tab Kho PC."""
        p = types.SimpleNamespace()
        head = ttk.Frame(right)
        head.pack(fill='x')
        p.img = ttk.Label(head)
        p.img.pack(side='left', padx=(0, 14))
        hb = ttk.Frame(head)
        hb.pack(side='left', fill='x')
        row1 = ttk.Frame(hb)
        row1.pack(anchor='w')
        p.name = ttk.Label(row1, text='', font=('Segoe UI', 18, 'bold'))
        p.name.pack(side='left')
        p.star = ttk.Label(row1, text='', font=('Segoe UI', 14, 'bold'), foreground='#d49a00')
        p.star.pack(side='left', padx=12)
        p.sub = ttk.Label(hb, text='', font=('Segoe UI', 11))
        p.sub.pack(anchor='w')
        p.warn = ttk.Label(hb, text='', foreground='#b00020')
        p.warn.pack(anchor='w')

        gi = ttk.LabelFrame(right, text='Thông tin')
        gi.pack(fill='x', pady=4)
        p.fi = {}
        fields = (('Tính cách', 'nature'), ('Ability', 'ability'), ('Vật cầm', 'item'), ('Thân thiết', 'friend'),
                  ('EXP', 'exp'), ('Tỉ lệ bắt', 'catch'), ('TID / SID', 'tid'))
        for n, (t, k) in enumerate(fields):
            r, c = divmod(n, 2)
            ttk.Label(gi, text=t + ':', foreground='gray').grid(row=r, column=2 * c, sticky='e', padx=(10, 6), pady=1)
            p.fi[k] = ttk.Label(gi, text='', font=('Segoe UI', 10, 'bold'))
            p.fi[k].grid(row=r, column=2 * c + 1, sticky='w', padx=(0, 14), pady=1)
        for r, (t, k) in enumerate((('PID', 'pid'), ('Ability của loài', 'abil_all')), start=4):   # dòng dài: chiếm cả hàng
            ttk.Label(gi, text=t + ':', foreground='gray').grid(row=r, column=0, sticky='e', padx=(10, 6), pady=1)
            p.fi[k] = ttk.Label(gi, text='', font=('Segoe UI', 10, 'bold'), wraplength=380, justify='left')
            p.fi[k].grid(row=r, column=1, columnspan=3, sticky='w', pady=1)

        gs = ttk.LabelFrame(right, text='Chỉ số')
        gs.pack(fill='x', pady=4)
        for c, h in enumerate(('', 'HP', 'Atk', 'Def', 'Spe', 'SpA', 'SpD', 'Tổng')):   # cột tự co theo chữ dài nhất
            ttk.Label(gs, text=h, font=('Segoe UI', 10, 'bold'), anchor='center').grid(row=0, column=c, padx=3)
        p.fs = {}
        for r, (k, t) in enumerate((('now', 'Hiện tại'), ('base', 'Cơ bản (loài)'), ('iv', 'IV'), ('ev', 'EV')), start=1):
            ttk.Label(gs, text=t, anchor='e').grid(row=r, column=0, padx=(6, 3), pady=1, sticky='e')
            p.fs[k] = []
            for c in range(1, 8):
                lb = tk.Label(gs, text='', anchor='center', font=('Consolas', 11))
                lb.grid(row=r, column=c, padx=3, pady=1, sticky='ew')
                p.fs[k].append(lb)
        for c in range(1, 8):
            gs.columnconfigure(c, minsize=44)                      # giữ cột đều khi chưa có số
        p.note = ttk.Label(gs, text='', foreground='gray', wraplength=430, justify='left')
        p.note.grid(row=6, column=0, columnspan=8, sticky='w', padx=6, pady=(2, 4))
        p.grade = tk.Label(gs, text='', font=('Segoe UI', 11, 'bold'), padx=8, pady=2)   # đánh giá IV nổi bật
        p.grade.grid(row=5, column=0, columnspan=8, sticky='w', padx=6, pady=(4, 0))

        gm = ttk.LabelFrame(right, text='Chiêu thức')
        gm.pack(fill='x', pady=4)
        mcols = (('n', 26, '#'), ('name', 140, 'Chiêu'), ('pw', 80, 'Sức mạnh'), ('ac', 80, 'Chính xác'), ('pp', 70, 'PP'))
        p.move = ttk.Treeview(gm, columns=[c[0] for c in mcols], show='headings', height=4)
        for c, w, t in mcols:
            p.move.heading(c, text=t)
            p.move.column(c, width=w, anchor='center')
        p.move.pack(fill='x', padx=4, pady=4)
        return p

    def foe_clear(self, msg, p=None):
        p = p or self.q_fd
        p.img.config(image='')
        p.name.config(text=msg)
        p.star.config(text='')
        p.sub.config(text='Vào trận đấu để xem Pokémon đối thủ, hoặc bấm một loài ở danh sách khu vực để xem trước.')
        p.warn.config(text='')
        for lb in p.fi.values():
            lb.config(text='')
        for row in p.fs.values():
            for lb in row:
                lb.config(text='', fg='black')
        p.note.config(text='')
        p.grade.config(text='', bg=p.grade.master.winfo_toplevel().cget('bg'))
        p.move.delete(*p.move.get_children())

    @staticmethod
    def iv_color(v):
        return '#0a7d2c' if v >= 28 else ('#b00020' if v <= 5 else 'black')

    def _types(self, sp):
        tn = lambda t: TYPE_NAMES[t] if t < len(TYPE_NAMES) else str(t)
        t1, t2 = self.rom.species_types(sp)
        return tn(t1) + ('' if t1 == t2 else ' / ' + tn(t2))

    def _abilities_all(self, sp):
        return self.rom.abilities_text(sp)

    def species_preview(self, sp, p=None):
        p = p or self.q_fd
        r = self.rom
        b = r.base_stats(sp)
        self.foe_clear(r.species_name(sp), p)
        p.img.config(image=self.photo(sp, False, 1.5) or '')
        p.sub.config(text='Hệ: %s     (loài #%d)     — xem trước loài, chưa phải cá thể đang gặp' % (self._types(sp), sp))
        p.fi['abil_all'].config(text=self._abilities_all(sp))
        p.fi['catch'].config(text=catch_level(r.catch_rate(sp)))
        p.fi['friend'].config(text=str(r.base_friendship(sp)) + '  (cơ bản)')
        for c, lb in enumerate(p.fs['base']):
            lb.config(text=str(b[c]) if c < 6 else str(sum(b)))
        p.grade.config(text='', bg=p.grade.master.winfo_toplevel().cget('bg'))
        p.note.config(text='Chỉ số cơ bản của loài. IV, EV, tính cách, chiêu chỉ có khi bạn gặp một cá thể cụ thể.')

    def foe_render(self, m, p=None):
        p = p or self.q_fd
        r = self.rom
        b = r.base_stats(m.species)
        shiny = m.is_shiny_in_game()
        p.img.config(image=self.photo(m.species, shiny, 1.5) or '')
        p.name.config(text=r.species_name(m.species))
        p.star.config(text='★ SHINY' if shiny else '')
        p.sub.config(text='Lv %d     %s     Hệ: %s     (loài #%d)' % (
            m.level, r.gender(m.species, m.pid), self._types(m.species), m.species))
        p.warn.config(text='' if m.checksum_ok else '⚠ Dữ liệu chưa hợp lệ: Pokémon đang được tạo hoặc là dữ liệu cũ/lỗi.')
        ab, hidden = r.ability_of(m)
        vals = {
            'nature': r.nature_text(m),
            'ability': ab + ('  (ability ẩn)' if hidden else ''),
            'abil_all': self._abilities_all(m.species),
            'item': r.item_name(m.item) if m.item else '(không)',
            'friend': str(m.friendship), 'exp': str(m.exp), 'catch': catch_level(r.catch_rate(m.species)),
            'tid': '%d / %d' % (m.otid & 0xFFFF, m.otid >> 16),
            'pid': '%08X   (shiny-xor %d)' % (m.pid, shiny_xor(m.pid, m.otid)),
        }
        for k, v in vals.items():
            p.fi[k].config(text=v)
        now = [m.maxhp, m.atk, m.defn, m.spe, m.spa, m.spd]
        rows = {'now': ['%d/%d' % (m.hp, m.maxhp)] + [str(x) for x in now[1:]] + [str(sum(now))],
                'base': [str(x) for x in b] + [str(sum(b))],
                'iv': [str(x) for x in m.iv] + [str(sum(m.iv))],
                'ev': [str(x) for x in m.ev] + [str(sum(m.ev))]}
        for k, texts in rows.items():
            for c, lb in enumerate(p.fs[k]):
                col = 'black'
                if k == 'iv' and c < 6:
                    col = self.iv_color(m.iv[c])
                elif k == 'ev' and c < 6 and m.ev[c] > 0:
                    col = '#1565c0'
                lb.config(text=texts[c], fg=col)
        ivs = sum(m.iv)
        g, useful, main = iv_grade(m.iv, b)
        plain = p.grade.master.winfo_toplevel().cget('bg')            # Tạm/Thường: không nền, chữ xám
        fg, bg = (('#ffffff', '#1b7f2a'), ('#14501d', '#c8efc8'), ('gray', plain), ('gray', plain))[3 - g]
        p.grade.config(text='%s IV: %s — có ích %d/155 (%d%%)' % (
            '✔' if g >= 2 else '•', IV_GRADES[g].upper(), useful, round(useful * 100 / 155)), fg=fg, bg=bg)
        p.note.config(text='IV tổng %d/186 (%d%%)     EV tổng %d/510     loài đánh bằng %s nên bỏ qua %s\n'
                                 'xanh lá = IV cao (≥28), đỏ = IV thấp (≤5), xanh dương = có EV' % (
                                     ivs, round(ivs * 100 / 186), sum(m.ev), main, 'SpA' if main == 'Atk' else 'Atk'))
        p.move.delete(*p.move.get_children())
        for i in range(4):
            mv = m.moves[i]
            if not mv:
                p.move.insert('', 'end', values=(i + 1, '-', '', '', ''))
                continue
            maxpp = r.move_pp(mv) * (5 + ((m.ppbonus >> (2 * i)) & 3)) // 5
            p.move.insert('', 'end', values=(i + 1, r.move_name(mv), r.move_power(mv) or '—',
                                                 r.move_accuracy(mv) or '—', '%d/%d' % (m.pp[i], maxpp)))

    def shiny_text(self, n):
        return '%d/%d (%.2f%%)' % (n, SHINY_ODDS, 100.0 * n / SHINY_ODDS)

    def upd_shiny_lbl(self):
        text = 'Đếm shiny: đã gặp %s kể từ shiny gần nhất' % self.shiny_text(self.shiny_n)
        if self.shiny_c is not None:                      # tỉ lệ thật của lượt gặp tới, theo bộ đếm trong game
            p = 1 - (1 - 1 / SHINY_ODDS) * (1 - min(1.0, self.shiny_c * SHINY_STEP / SHINY_ODDS))
            text += '\nBộ đếm trong game: %d · lượt gặp tới: 1/%d' % (self.shiny_c, round(1 / p))
        if getattr(self, 'q_shiny_lbl', None):               # tab con Lịch sử (dựng sau khi nạp bộ đếm)
            self.q_shiny_lbl.config(text=text)

    def on_shiny_boost(self):
        self.save_area_state()
        self.guard(self.tick_shiny)()

    def tick_shiny(self):
        """AowVN: đọc bộ đếm tăng tỉ lệ shiny; khi bỏ tick thì giữ nó ở 0, game chỉ còn tỉ lệ gốc."""
        if not getattr(self.prof, 'shiny_boost_off', None):
            return
        c = self.game.shiny_counter()
        if c and not self.shiny_boost.get() and c <= SHINY_ODDS:
            st = self.game.battle_state()
            if st and (st[0] or st[1]):                   # trong trận/overworld: SaveBlock1 không bị dời chỗ
                self.game.reset_shiny_counter()
                c = 0
        self.shiny_c = c
        self.upd_shiny_lbl()

    def count_encounter(self, m, key):
        """+1 cho mỗi Pokémon hoang dã mới (mang ID của người chơi); gặp shiny -> trả 'N/8192 (%)' rồi đếm lại."""
        try:
            wild = m.otid == self.game.player_otid()
        except Exception:
            wild = False
        if not wild:
            return '— (trainer)'
        if list(key) == self.shiny_last:                  # cùng con đã đếm trước khi tắt tool
            return str(self.shiny_n)
        self.shiny_n += 1
        n, self.shiny_last = self.shiny_n, list(key)
        if m.is_shiny_in_game():
            self.shiny_n = 0
        try:
            with open(self.shiny_file, encoding='utf-8') as fp:
                data = json.load(fp)
        except (OSError, ValueError):
            data = {}
        data[self.prof.key] = {'n': self.shiny_n, 'last': self.shiny_last}
        with open(self.shiny_file, 'w', encoding='utf-8') as fp:
            json.dump(data, fp)
        self.upd_shiny_lbl()
        return self.shiny_text(n) if m.is_shiny_in_game() else str(n)

    HIST_FILE = os.path.join(HERE, 'encounter_history.jsonl')
    HIST_KEEP = 3000                 # số lần gặp nạp lại khi mở tool
    HIST_TIMES = [('all', 'Tất cả'), ('today', 'Hôm nay'), ('hour', '1 giờ qua')]

    def hist_add(self, t, m, cnt):
        """Thêm một lần gặp vào đầu self.hist (mới nhất trước). t = 'YYYY-mm-dd HH:MM:SS'."""
        self.hist_seq = getattr(self, 'hist_seq', 0) + 1
        g = iv_grade(m.iv, self.rom.base_stats(m.species))[0] if 1 <= m.species <= self.rom.max_species else 0
        e = dict(id=self.hist_seq, t=t, m=m, cnt=cnt, g=g)
        self.hist.insert(0, e)
        self.__dict__.setdefault('hist_by_id', {})[e['id']] = e
        return e

    def hist_load(self):
        """Nạp HIST_KEEP lần gặp gần nhất từ file; các con này coi như đã gặp (mở lại tool sau trận không báo lại)."""
        self.hist_by_id = {}
        try:
            with open(self.HIST_FILE, encoding='utf-8') as fp:
                lines = fp.readlines()[-self.HIST_KEEP:]
        except OSError:
            return
        for ln in lines:
            try:
                d = json.loads(ln)
                m = self.prof.mon_cls(base64.b64decode(d['raw']))
            except Exception:
                continue
            self.hist_add(d['t'], m, d.get('cnt', ''))
            self.seen.add((m.pid, m.otid, m.species))

    def hist_save(self, e):
        if self.fake:                                     # bài thử / bộ nhớ giả: không ghi vào lịch sử thật
            return
        try:
            with open(self.HIST_FILE, 'a', encoding='utf-8') as fp:
                fp.write(json.dumps({'t': e['t'], 'raw': base64.b64encode(e['m'].to_bytes()).decode(),
                                     'cnt': e['cnt']}, ensure_ascii=False) + '\n')
        except OSError:
            pass

    def hist_pass(self, e):
        """Dòng lịch sử có qua bộ lọc đang chọn không."""
        if not hasattr(self, 'h_time'):
            return True
        mode = self.HIST_TIMES[max(0, self.h_time.current())][0]
        if mode == 'today' and not e['t'].startswith(time.strftime('%Y-%m-%d')):
            return False
        if mode == 'hour' and e['t'] < time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - 3600)):
            return False
        if self.h_shiny.get() and not e['m'].is_shiny_in_game():
            return False
        if self.h_iv.get() and e['g'] < 2:
            return False
        return True

    def hist_row(self, e):
        m, g = e['m'], e['g']
        day, hms = e['t'].split(' ')
        shown = hms if day == time.strftime('%Y-%m-%d') else '%s/%s %s' % (day[8:10], day[5:7], hms[:5])
        return dict(values=(shown, self.rom.species_name(m.species), m.level, '★' if m.is_shiny_in_game() else '',
                            ('✔ %d' if g >= 2 else '%d') % sum(m.iv),
                            '%.1f%%' % (100 * catch_chance(self.rom.catch_rate(m.species), m.hp, m.maxhp,
                                                           m.status)),          # Poké Ball, lúc gặp
                            e['cnt']),
                    tags=('iv_best',) if g == 3 else ('iv_good',) if g == 2 else ())

    def hist_render(self):
        """Vẽ lại các bảng lịch sử theo bộ lọc."""
        rows = [e for e in self.hist if self.hist_pass(e)]
        for ht in self.htrees:
            ht.delete(*ht.get_children())
            for e in rows:
                ht.insert('', 'end', iid=str(e['id']), **self.hist_row(e))
        self.hist_count()

    def hist_count(self):
        if hasattr(self, 'h_cnt'):
            n = len(self.htrees[0].get_children()) if self.htrees else 0
            self.h_cnt.config(text='%d / %d lần gặp' % (n, len(self.hist)))

    def refresh_foe(self):
        """Mỗi giây: đọc đội đối thủ; con mới gặp -> đếm lần gặp (shiny), ghi Lịch sử, báo nếu shiny / nên bắt.
        Tab Bản đồ tự hiện đối thủ đang đánh (quest_foe_detail)."""
        mons = self.game.enemy_party()
        self.foe_mons = mons
        for m in mons:
            if m.empty or not m.checksum_ok or not 1 <= m.species <= self.rom.max_species:
                continue
            key = (m.pid, m.otid, m.species)
            if key not in self.seen and 1 <= m.level <= 100:
                self.seen.add(key)
                cnt = self.count_encounter(m, key)
                g, useful, _ = iv_grade(m.iv, self.rom.base_stats(m.species))
                e = self.hist_add(time.strftime('%Y-%m-%d %H:%M:%S'), m, cnt)
                self.hist_save(e)
                if self.hist_pass(e):
                    for ht in self.htrees:                    # tab con Lịch sử
                        ht.insert('', 0, iid=str(e['id']), **self.hist_row(e))
                    self.hist_count()
                wild =not cnt.startswith('—')                # count_encounter trả '— (trainer)' cho Pokémon trainer
                if m.is_shiny_in_game():
                    self.say('★ Gặp %s SHINY! (lần gặp %s)' % (self.rom.species_name(m.species), cnt))
                    if wild:
                        self.alert('★ SHINY: %s Lv %d' % (self.rom.species_name(m.species), m.level),
                                   'Lần gặp %s  ·  IV %s' % (cnt, IV_GRADES[g].lower()), m, shiny=True)
                elif g >= 2:
                    self.say('✔ Gặp %s IV %s (có ích %d/155) — nên bắt' % (self.rom.species_name(m.species),
                                                                          IV_GRADES[g].lower(), useful))
                    # đang săn: chỉ kêu khi tool sẽ bắt con này (Duy 07/11: rời máy, không muốn bíp con mình không săn)
                    if wild and (not self.hunt or self.hunt_want(m)):
                        self.alert('✔ NÊN BẮT: %s Lv %d' % (self.rom.species_name(m.species), m.level),
                                   'IV %s — có ích %d/155' % (IV_GRADES[g].lower(), useful), m, shiny=False)

    def tick_battle(self):
        """Trận vừa xong và đã về overworld (qua màn tiến hoá/học chiêu) -> tự hồi phục cả đội."""
        st = self.game.battle_state()
        if st is None:
            return
        in_battle, overworld = st
        if in_battle:
            new = not self.was_battle
            if self.exp_snap:                                    # gặp trận mới ngay, tool không kịp thấy lúc hết trận cũ:
                pids = {m.pid for m in self.game.enemy_party() if not m.empty}   # đối thủ đổi = trận cũ đã xong
                if pids != {m.pid for m in self.exp_snap[1]}:
                    self.finish_exp()
                    new = True
            if new and getattr(self.prof, 'box_ptr', None) and self.box_exp.get() \
                    and self.game.exp_share_on():                # đầu trận: chụp EXP đội + đối thủ
                foes = [m for m in self.game.enemy_party() if not m.empty and m.checksum_ok]
                self.exp_snap = ([m for m in self.game.party() if not m.empty], foes) if foes else None
            self.was_battle = True
            return
        if self.exp_snap:                                        # cờ trong trận tắt = EXP đã chia xong, không chờ overworld
            self.finish_exp()
        if overworld and not getattr(self, '_form_dex_done', False):
            self._form_dex_done = True                          # lần đầu tool thấy game: ghi Pokédex dạng Galar...
            self.fix_form_dex()
        if self.was_battle and overworld:
            self.was_battle = False
            self.fix_form_dex()                                  # vừa bắt xong có thể là chim Galar
            msg, self.exp_msg = self.exp_msg, []
            if self.auto_heal.get():
                self.heal_slots(range(PARTY_SLOTS))
                msg.append(self.status.cget('text'))
            if msg:
                self.say('Sau trận — ' + ' · '.join(msg))

    def fix_form_dex(self):
        """Bảng số Pokédex của hack ghi 0 cho chim Galar, Gigantamax... nên game không bật cờ khi bắt chúng.
        Tool bật cờ đã thấy + đã bắt theo số của loài cùng tên (như game chính thức) cho con đang có trong đội/kho
        (Duy chốt 06/11). Chạy khi mở tool và mỗi lần trận xong."""
        t = getattr(self.prof, 'natdex_table', None)
        if not t or not getattr(self.prof, 'dex_caught', None):
            return
        r = self.rom
        game0 = lambda sp: not struct.unpack_from('<H', r.d, r._o(t) + 2 * (sp - 1))[0]
        cand = lambda sp: 1 <= sp <= r.max_species and game0(sp) and r.natdex(sp)
        mons = [m for m in self.game.party() if not m.empty and m.checksum_ok and not m.egg and cand(m.species)]
        if getattr(self.prof, 'box_ptr', None):
            _, box = self.game.read_box()
            sz = self.prof.box_size
            for i in range(len(box) // sz):
                cell = bytes(box[i * sz:(i + 1) * sz])
                if cand(struct.unpack_from('<H', cell, self.prof.box_species)[0]):
                    m = box_to_party(r, cell)
                    if not m.egg:
                        mons.append(m)
        caught = self.game.caught_dex() or set()
        need = sorted({m.species for m in mons if r.natdex(m.species) not in caught})
        if need:
            self.game.mark_dex(need)
            self.say('Đã ghi Pokédex cho %s (game không tự ghi các dạng này). Nhớ lưu game.' % ', '.join(
                '%s #%d' % (r.species_name(sp), r.natdex(sp)) for sp in need))

    def finish_exp(self):
        """Trận trong exp_snap đã xong: cộng EXP cho kho PC theo đối thủ bị hạ/bắt, ghi nhật ký."""
        before, foes = self.exp_snap
        self.exp_snap = None
        after = [m for m in self.game.party() if not m.empty]
        end = {m.pid: m for m in self.game.enemy_party() if not m.empty}
        beaten, old, box, evolved = [], b'', b'', []
        now_exp = {m.pid: m.exp for m in after}
        if any(now_exp.get(m.pid, m.exp) > m.exp for m in before):          # con có từ đầu trận nhận EXP (không tính con vừa bắt)
            base, box = self.game.read_box()
            old = bytes(box)
            # bị bắt (CFRU cho EXP khi bắt) = PID vừa có trong đội hoặc kho
            caught = {m.pid for m in after} | {struct.unpack_from('<I', old, o)[0] for o in range(0, len(old), self.prof.box_size)}
            # bị hạ (HP 0), bị bắt, hoặc đã sang trận mới nên đối thủ cũ không còn trong bộ nhớ (trận đôi: tính từng con)
            beaten = [m for m in foes if m.pid not in end or end[m.pid].hp == 0 or m.pid in caught]
            n = box_exp_share(self.rom, [(m.species, m.level) for m in beaten], box, self.game.player_otid())
            evolved = box_evolve(self.rom, box)                              # đủ cấp là đổi loài, không qua màn tiến hoá của game
            if n or evolved:
                self.game.write_box(base, old, box)
            if evolved:
                self.game.mark_dex({to for _, _, to in evolved})
                names = ['%s → %s' % (self.rom.species_name(a), self.rom.species_name(b)) for _, a, b in evolved]
                self.exp_msg.append('kho PC đổi loài: ' + ', '.join(names[:4]) + (' và %d con khác' % (len(names) - 4) if len(names) > 4 else ''))
            if n:
                self.exp_msg.append('kho PC: +EXP cho %d con' % n)
        self.log_battle(foes, end, beaten, before, after, old, box, evolved)

    def log_battle(self, foes, end, beaten, before, after, old, box, evolved=()):
        """Ghi 1 dòng JSON mỗi trận vào battle_log.jsonl để đối chiếu EXP sau này.
        party: [tên, lv trước, lv sau, EXP nhận, đủ x1.2 tiến hoá lúc vào trận]; box: [ô, tên, lv, EXP được cộng, x1.2]."""
        r, p = self.rom, self.prof
        now = {m.pid: m for m in after}
        rec = {'time': time.strftime('%Y-%m-%d %H:%M:%S'),
               'foes': [[r.species_name(m.species), m.level, end[m.pid].hp if m.pid in end else None] for m in foes],
               'beaten': [[r.species_name(m.species), m.level] for m in beaten],
               'party': [[r.species_name(m.species), m.level, now[m.pid].level if m.pid in now else None,
                          now[m.pid].exp - m.exp if m.pid in now else None, could_have_evolved(r, m.species, m.level)]
                         for m in before],
               'box': [], 'evolved': [[c, r.species_name(a), r.species_name(b)] for c, a, b in evolved]}
        for o in range(0, len(old), p.box_size):
            e0, e1 = (struct.unpack_from('<I', d, o + p.box_exp)[0] for d in (old, box))
            if e1 != e0:
                sp = struct.unpack_from('<H', old, o + p.box_species)[0]
                lv = r.level_for(r.growth(sp), e0)
                rec['box'].append([o // p.box_size, r.species_name(sp), lv, e1 - e0, could_have_evolved(r, sp, lv)])
        try:
            with open(os.path.join(HERE, 'battle_log.jsonl'), 'a', encoding='utf-8') as fp:
                fp.write(json.dumps(rec, ensure_ascii=False) + '\n')
        except OSError:
            pass

    def do_sync(self):
        """Nút ☁ Đồng bộ: cập nhật code + đẩy save (luồng nền); có code mới thì hỏi mở lại tool."""
        code, sav = save_sync.CodeSync(), self.__dict__.setdefault('_sync', save_sync.Sync())
        if not code.ready() and not sav.ready():
            return messagebox.showinfo('Đồng bộ', 'Chưa nối với GitHub. Mở cửa sổ lệnh ở thư mục tool rồi chạy:\n'
                                       'py -3 save_sync.py setup <link repo GitHub>', parent=self)
        if getattr(self, '_sync_busy', False):
            return self.say('☁ Đang đồng bộ, đợi chút…')
        self.say('☁ Đang đồng bộ…')

        def run():
            n, out = 0, []
            for name, job in (('code', code.update if code.ready() else None),
                              ('save', sav.push if sav.ready() else None)):
                if job:
                    try:
                        r = job()
                        n, r = (r if name == 'code' else (n, r))
                        out.append(r)
                    except Exception as e:
                        out.append('LỖI %s: %s' % (name, e))
            return n, out
        self.run_bg(run, lambda r: self._sync_done(*r))

    def run_bg(self, job, done):
        """Chạy job() ở luồng nền (git chậm, không làm đứng giao diện); xong thì done(kết quả) ở luồng giao diện.
        Luồng nền chỉ cất kết quả, luồng giao diện tự hỏi mỗi 0,2 giây (Tk không an toàn khi gọi từ luồng khác)."""
        import threading
        self._sync_busy, box = True, []
        threading.Thread(target=lambda: box.append(job()), daemon=True).start()

        def poll():
            if not box:
                return self.after(200, poll)
            self._sync_busy = False
            done(box[0])
        self.after(200, poll)

    def _sync_done(self, n, out):
        msg = ' · '.join(out)
        self.say('☁ ' + msg, not any(x.startswith(('LỖI', 'KHÔNG')) for x in out))
        if n and messagebox.askyesno('Có bản tool mới', '%s\n\nMở lại tool để dùng bản mới?' % msg, parent=self):
            self.restart_tool()

    def restart_tool(self):
        """Mở bản tool mới (đợi bản này thoát hẳn mới chạy, xem --restart ở already_running) rồi đóng bản này."""
        import subprocess
        subprocess.Popen([sys.executable, os.path.abspath(__file__), '--restart'], cwd=HERE,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.destroy()

    def tick_save_sync(self):
        """Mỗi 5 giây: file .sav đổi (game vừa lưu) và đã đứng yên 3 giây -> đẩy lên repo save (luồng nền).
        Chưa cài đồng bộ (chưa có save_sync\\.git) thì không làm gì."""
        try:
            sy = self.__dict__.setdefault('_sync', save_sync.Sync())
            if sy.ready() and not getattr(self, '_sync_busy', False):
                mt = os.path.getmtime(sy.sav)
                last = self.__dict__.setdefault('_sync_mtime', mt)   # lần đầu: coi bản hiện tại là đã xét
                if mt != last and time.time() - mt > 3:
                    self._sync_mtime = mt

                    def run():
                        try:
                            return sy.push()
                        except Exception as e:
                            return 'LỖI: %s' % e
                    self.run_bg(run, lambda msg: self.say('☁ Đồng bộ save: ' + msg,
                                                          not msg.startswith(('LỖI', 'KHÔNG'))))
        except Exception:
            self.log_tick_error()
        self.after(5000, self.tick_save_sync)

    def tick_field(self):
        old = getattr(self.bridge, 'timeout', None)       # luôn tự làm mới mỗi giây
        try:
            if old is not None:
                self.bridge.timeout = 1.0
            try:
                self.game.snapshot_tick()                    # 2 lệnh đọc gộp; các hàm dưới đọc từ bản chụp
            except BridgeError:
                pass
            fns = [self.tick_shiny, self.tick_battle, self.refresh_foe]
            if self.roam_keep:
                fns.append(self.tick_roam_keep)              # vừa bay tới chỗ huyền thoại: giữ nó lại (mọi tab)
            if getattr(self.prof, 'roam_sets', None):
                fns.append(self.tick_roam_spawn)             # tự thả huyền thoại theo giờ chơi
            if self.nb.select() == str(self.t_mon) and self.mons:
                fns.append(self.tick_party)                  # tab Đội: HP tự cập nhật
            if self.t_box and self.nb.select() == str(self.t_box) and self.bx_shown:
                fns.append(self.tick_box)                    # tab Kho: EXP tự cập nhật
            if self.t_quest and self.nb.select() == str(self.t_quest):
                fns.append(self.quest_tick)                  # tab Bản đồ: theo map đang đứng + cờ
            for fn in fns:
                try:
                    fn()
                except BridgeError:
                    break
                except Exception:                            # lỗi lạ: ghi lại, hàm khác vẫn chạy (pythonw không có stderr)
                    self.log_tick_error()
        finally:
            self.bridge.end_snapshot()                       # bấm nút ngoài nhịp này luôn đọc số mới
            if old is not None:
                self.bridge.timeout = old
            self.after(1000, self.tick_field)                # luôn hẹn lần sau, vòng này chết là mất tự hồi phục + EXP kho

    def tick_player_fast(self):
        """Tab Bản đồ đang mở + đang xem map đang đứng: đọc vị trí nhân vật mỗi 0,3 giây (1 lệnh bridge),
        chỉ vẽ lại khi nhân vật đi / quay. Map lấy theo SaveBlock1 của nhịp 1 giây; SaveBlock1 vừa dời chỗ thì
        đọc ra map sai -> bỏ qua, nhịp 1 giây sẽ sửa."""
        delay = 300
        try:
            p = self.prof
            if (self.t_quest and self.nb.select() == str(self.t_quest) and self.q_img and getattr(self, 'q_sb1', None)
                    and self.q_shown == self.q_cur):
                b = self.bridge
                old = getattr(b, 'timeout', None)
                try:
                    if old is not None:
                        b.timeout = 0.5
                    pairs = [(self.q_sb1 + p.loc_off, 2), (p.player_obj, 0x19)]
                    b.snapshot(pairs)
                    loc, obj = b.read_many(pairs)
                    key = ((loc[0], loc[1]), obj[0x10:0x14], obj[5], obj[0x18] & 0xF)
                    if key[0] == self.q_shown and key != self.q_fast_key:
                        self.q_fast_key = key
                        self.quest_player()                   # đọc player_xy / player_look từ bản chụp
                finally:
                    b.end_snapshot()
                    if old is not None:
                        b.timeout = old
        except BridgeError:
            delay = 1000                                      # mGBA chưa mở / đang dừng: thưa ra
        except Exception:
            self.log_tick_error()
            delay = 1000
        self.after(delay, self.tick_player_fast)

    def log_tick_error(self):
        err = traceback.format_exc()
        if err == self.tick_err:                             # lặp mỗi giây thì chỉ ghi một lần
            return
        self.tick_err = err
        self.say('Lỗi nền, đã ghi tick_error.log: %s' % err.strip().splitlines()[-1], False)
        try:
            with open(os.path.join(HERE, 'tick_error.log'), 'a', encoding='utf-8') as fp:
                fp.write('%s\n%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), err))
        except OSError:
            pass

    def report_callback_exception(self, exc, val, tb):
        """Lỗi trong lúc bấm nút/chuột: pythonw không có stderr nên trước đây mất lặng -> ghi log + báo trên thanh trạng thái."""
        err = ''.join(traceback.format_exception(exc, val, tb))
        self.say('Lỗi khi bấm, đã ghi tick_error.log: %s' % err.strip().splitlines()[-1], False)
        try:
            with open(os.path.join(HERE, 'tick_error.log'), 'a', encoding='utf-8') as fp:
                fp.write('%s (bấm)\n%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), err))
        except OSError:
            pass

    # ------------------------------------------------------------ tab Kho PC
    def _build_box(self):
        self.bx_shown = None                                 # (ô đầu của box đang hiện, số loài từng ô)
        f = self.t_box
        col = ttk.Frame(f)
        col.pack(side='left', fill='y', **PAD)
        left = ttk.LabelFrame(col, text='Đội')
        left.pack(fill='x')
        cols = (('slot', 28, '#'), ('name', 120, 'Loài'), ('lv', 36, 'Lv'), ('hp', 190, 'HP'), ('shiny', 44, 'Shiny'),
                ('send', 56, ''))
        self.bx_party = ttk.Treeview(left, columns=[c[0] for c in cols], show='headings', height=6, selectmode='none')
        for c, w, t in cols:
            self.bx_party.heading(c, text=t)
            self.bx_party.column(c, width=w, anchor='w' if c in ('name', 'hp') else 'center')
        self.bx_party.pack(**PAD)
        srt = ttk.Frame(left)
        srt.pack(fill='x', **PAD)
        ttk.Label(srt, text='Sắp xếp cả kho theo').pack(side='left')
        self.bx_sort = ttk.Combobox(srt, state='readonly', width=16, values=[t for _, t in SORT_MODES])
        self.bx_sort.current(0)
        self.bx_sort.pack(side='left', padx=4)
        ttk.Button(srt, text='Sắp xếp', command=self.guard(self.do_sort_box)).pack(side='left', fill='x', expand=True)
        Tip(srt, 'Xếp cả 25 box rồi dồn về từ Box 1. Hoà nhau (cùng shiny / cùng IV / cùng level) thì theo số Pokédex.\n'
                 'Pokédex: cùng loài thì shiny trước, rồi IV cao. Level: cùng level thì EXP cao trước.')
        det = ttk.LabelFrame(col, text='Chi tiết, chỉ xem (bấm một con trong đội hoặc kho)')
        det.pack(fill='both', expand=True, pady=(4, 0))
        self.bx_fd = self._build_detail(self._scroll_frame(det))
        self.foe_clear('Chọn một con', self.bx_fd)
        self.bx_fd.sub.config(text='Chỉ xem. Muốn sửa thì lấy về đội rồi sửa ở tab Đội.')
        right = ttk.LabelFrame(f, text='Kho')
        right.pack(side='left', fill='both', expand=True, **PAD)
        bt = ttk.Frame(right)
        bt.pack(fill='x')
        self.bx_box = ttk.Combobox(bt, state='readonly', width=12,
                                   values=['Box %d' % (i + 1) for i in range(self.prof.box_slots // BOX_CAPACITY)])
        self.bx_box.current(0)
        self.bx_box.pack(side='left', **PAD)
        info_icon(bt, 'Gửi: vào ô trống đầu tiên, tính từ Box 1. Lấy: về cuối đội, đầy HP và PP.\n'
                      'Chỉ làm được khi đang đi trên bản đồ. Nhớ lưu game để giữ thay đổi.\n'
                      'Dòng tô cam: loài này có từ 2 con trở lên trong kho, thả được ngay tại dòng.\n'
                      'Bấm vào một con (ngoài chữ Gửi/Lấy/Thả) để xem chi tiết bên trái.').pack(side='left', padx=6)
        self.bx_box.bind('<<ComboboxSelected>>', lambda e: self.guard(self.refresh_box)())
        cols = (('slot', 26, 'Ô'), ('name', 96, 'Loài'), ('lv', 34, 'Lv'), ('exp', 58, 'EXP'), ('shiny', 42, 'Shiny'),
                ('iv', 38, 'IV'), ('item', 90, 'Vật cầm'), ('get', 50, ''), ('rel', 50, ''))   # + cột hình 38: vừa 1080
        wrap = ttk.Frame(right)
        wrap.pack(fill='both', expand=True)
        ttk.Style(self).configure('Box.Treeview', rowheight=36)
        self.bx_cells = ttk.Treeview(wrap, columns=[c[0] for c in cols], show='tree headings', selectmode='none',
                                     style='Box.Treeview')
        self.bx_cells.column('#0', width=38, minwidth=38, stretch=False)   # cột hình
        for c, w, t in cols:
            self.bx_cells.heading(c, text=t)
            self.bx_cells.column(c, width=w, anchor='w' if c in ('name', 'item') else 'center')
        self.bx_cells.tag_configure('dup', background='#ffd9a8')
        for t in (self.bx_party, self.bx_cells):
            t.tag_configure('viewing', background='#cfe3ff')
        sb = ttk.Scrollbar(wrap, orient='vertical', command=self.bx_cells.yview)
        self.bx_cells.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.bx_cells.pack(side='left', fill='both', expand=True)
        for t in (self.bx_party, self.bx_cells):
            t.bind('<Motion>', lambda e: e.widget.configure(cursor='hand2' if self._bx_action(e) else ''))
            t.bind('<ButtonRelease-1>', self._bx_click)

    def _bx_action(self, e):
        """Nút (chữ trong cột hành động) dưới con trỏ chuột: (tên cột, số dòng); không có thì None."""
        t = e.widget
        row, col = t.identify_row(e.y), t.identify_column(e.x)
        if row and col and col != '#0' and t.identify_region(e.x, e.y) == 'cell':
            name = t['columns'][int(col[1:]) - 1]
            if name in ('send', 'get', 'rel') and t.set(row, name):
                return name, int(row)
        return None

    def _bx_click(self, e):
        hit = self._bx_action(e)
        if hit:
            fn = {'send': self.do_deposit, 'get': self.do_withdraw, 'rel': self.do_release}[hit[0]]
            self.guard(fn)(hit[1])
            return
        row = e.widget.identify_row(e.y)                 # bấm chỗ khác trên dòng: xem chi tiết con đó (chỉ xem)
        if row:
            self.guard(self.bx_detail)(e.widget, int(row))

    def bx_detail(self, tree, i):
        if tree is self.bx_party:
            m = self.game.party()[i]
        else:
            raw = self.game.read_one_box(self.bx_box.current())[i]
            sp = cell_species(raw)
            if not 1 <= sp <= self.rom.max_species:
                return
            m = box_to_party(self.rom, raw)
        if m.empty:
            return
        self.foe_render(m, self.bx_fd)
        for t in (self.bx_party, self.bx_cells):          # tô dòng đang xem (selectmode none nên tự làm)
            for r in t.get_children():
                tags = [x for x in t.item(r, 'tags') if x != 'viewing']
                t.item(r, tags=tags + (['viewing'] if t is tree and r == str(i) else []))

    def refresh_box(self):
        self.bx_party.delete(*self.bx_party.get_children())
        for i, m in enumerate(self.game.party()):
            if not m.empty:
                self.bx_party.insert('', 'end', iid=str(i), values=self.party_row(i, m)['values'] + ('[ Gửi ]',))
        self.bx_cells.delete(*self.bx_cells.get_children())
        _, data = self.game.read_box()
        cells = [bytes(data[i:i + BOX_MON_SIZE]) for i in range(0, len(data), BOX_MON_SIZE)]
        species = [cell_species(c) for c in cells]
        count = Counter(species)                    # so cả kho vì con trùng có thể nằm ở box khác
        start = self.bx_box.current() * BOX_CAPACITY
        self.bx_shown = (start, species[start:start + BOX_CAPACITY])
        for i, c in enumerate(cells[start:start + BOX_CAPACITY]):
            sp = species[start + i]
            if not 1 <= sp <= self.rom.max_species:
                self.bx_cells.insert('', 'end', iid=str(i), values=(i + 1, '(trống)', '', '', '', '', ''))
                continue
            m = box_to_party(self.rom, c)
            self.bx_cells.insert('', 'end', iid=str(i), image=self.species_icon(sp, 32, m.is_shiny_in_game()) or '', values=(
                i + 1, self.rom.species_name(sp), m.level, m.exp, '★' if m.is_shiny_in_game() else '', sum(m.iv),
                self.rom.item_name(m.item) if m.item else '', '[ Lấy ]', '[ Thả ]' if count[sp] > 1 else ''),
                tags=('dup',) if count[sp] > 1 else ())

    def tick_box(self):
        """Mỗi giây (khi đang mở tab Kho): cập nhật Lv/EXP của box đang xem tại chỗ; kho đổi thì tải lại hẳn."""
        start = self.bx_box.current() * BOX_CAPACITY
        cells = self.game.read_one_box(start // BOX_CAPACITY)
        if (start, [cell_species(c) for c in cells]) != self.bx_shown:
            self.refresh_box()
            return
        for i, c in enumerate(cells):
            if 1 <= self.bx_shown[1][i] <= self.rom.max_species:
                m = box_to_party(self.rom, c)
                if str(m.exp) != str(self.bx_cells.set(str(i), 'exp')):
                    self.bx_cells.set(str(i), 'lv', m.level)
                    self.bx_cells.set(str(i), 'exp', m.exp)

    def do_deposit(self, slot):
        name = self.bx_party.set(str(slot), 'name')
        box, cell = self.game.deposit(slot)
        self.refresh_box()
        self.mons = []
        self.say('Đã gửi %s vào Box %d, ô %d. Nhớ lưu game.' % (name, box + 1, cell + 1))

    def do_withdraw(self, cell):
        m = self.game.withdraw(self.bx_box.current(), cell)
        self.refresh_box()
        self.mons = []
        self.say('Đã lấy %s về đội. Nhớ lưu game.' % self.rom.species_name(m.species))

    def do_release(self, cell):
        _, name, lv, _, shiny, iv, item = self.bx_cells.item(str(cell), 'values')[:7]
        box = self.bx_box.current()
        msg = 'Thả %s Lv%s (IV %s) ở Box %d, ô %d?' % (name, lv, iv, box + 1, cell + 1)
        if shiny:
            msg += '\nCon này là SHINY.'
        if item:
            msg += '\nVật đang cầm (%s) sẽ mất theo.' % item
        if not messagebox.askyesno('Thả Pokémon', msg, icon='warning'):
            return
        self.game.release(box, cell)
        self.refresh_box()
        self.say('Đã thả %s. Nhớ lưu game; chưa lưu thì nạp lại save là còn.' % name)

    def do_sort_box(self):
        by, name = SORT_MODES[max(0, self.bx_sort.current())]
        if not messagebox.askyesno('Sắp xếp kho', 'Xếp toàn bộ 25 box theo "%s" và dồn về từ Box 1?' % name):
            return
        n = self.game.sort_boxes(by)
        self.refresh_box()
        self.say('Đã sắp xếp %d con. Nhớ lưu game.' % n)

    # ------------------------------------------------------------ tab Túi đồ
    def _build_bag(self):
        f = self.t_bag
        self._build_money(f)                                 # tiền: dải trên cùng của tab Túi đồ
        add = ttk.LabelFrame(f, text='Thêm vật phẩm vào túi')
        add.pack(side='bottom', fill='x', **PAD)
        Tip(add, 'Gõ tên → chọn gợi ý → nhập số lượng → bấm "Thêm / đặt số lượng" (0 = xoá).')
        self.cat_items = mm_items.load_items(self.rom) if getattr(self.prof, 'tm_moves', None) else None
        left = ttk.Frame(f)
        if self.cat_items:
            left.pack(side='left', fill='y')
            self._build_catalog(f)
        else:
            left.pack(fill='both', expand=True)
        top = ttk.Frame(left)
        top.pack(fill='x', **PAD)
        ttk.Label(top, text='Ngăn túi').pack(side='left')
        self.pocket = ttk.Combobox(top, values=self.prof.pocket_names, state='readonly', width=18)
        self.pocket.current(self.prof.default_pocket)
        self.pocket.pack(side='left', **PAD)
        self.pocket.bind('<<ComboboxSelected>>', lambda e: self.guard(self.refresh_bag)())
        self.btree = ttk.Treeview(left, columns=('id', 'name', 'qty'), show='headings', height=14)
        for c, w, t in (('id', 50, 'ID'), ('name', 220, 'Vật phẩm'), ('qty', 70, 'Số lượng')):
            self.btree.heading(c, text=t)
            self.btree.column(c, width=w, anchor='center')
        self.btree.pack(fill='both', expand=True, **PAD)
        self.btree.bind('<<TreeviewSelect>>', lambda e: self.bag_pick())
        self.drag_reorder(self.btree, self.bag_move, lambda: len(self.pocket_items))
        Tip(self.btree, 'Kéo thả một dòng để đổi vị trí trong ngăn (khi đang đi trên bản đồ).')
        self.bitem = SearchCombo(add, self.item_vals, width=34)
        self.bitem.grid(row=0, column=0, **PAD)
        self.bitem.bind('<<ComboboxSelected>>', lambda e: self.guard(self.bag_item_chosen)(), add='+')
        self.bqty = tk.IntVar(value=99)
        qty = ttk.Spinbox(add, from_=0, to=999, width=6, textvariable=self.bqty)
        qty.grid(row=0, column=1, **PAD)
        qty.bind('<Return>', lambda e: self.guard(self.bag_set)())
        ttk.Button(add, text='Thêm / đặt số lượng', command=self.guard(self.bag_set)).grid(row=0, column=2, **PAD)
        ttk.Button(add, text='Xoá khỏi túi', command=self.guard(lambda: self.bag_set(zero=True))).grid(row=0, column=3, **PAD)
        self.pocket_items = []

    def _build_catalog(self, f):
        """Danh mục mọi vật phẩm của AowVN: tìm theo tên/công dụng, lọc theo nhóm, xem chi tiết, cho con trong đội cầm."""
        self.cat_by_id = {x.id: x for x in self.cat_items}
        self.cat_have, self.cat_sel, self.give_slots = {}, None, []
        box = ttk.Frame(f)
        box.pack(side='left', fill='both', expand=True)
        top = ttk.Frame(box)
        top.pack(fill='x', **PAD)
        ttk.Label(top, text='Tìm').pack(side='left')
        self.cat_q = tk.StringVar()
        self.cat_q.trace_add('write', lambda *a: self.cat_fill())
        ttk.Entry(top, textvariable=self.cat_q, width=28).pack(side='left', **PAD)
        ttk.Label(top, text='Nhóm').pack(side='left')
        self.cat_group = ttk.Combobox(top, values=mm_items.GROUPS, state='readonly', width=18)
        self.cat_group.current(0)
        self.cat_group.pack(side='left', **PAD)
        self.cat_group.bind('<<ComboboxSelected>>', lambda e: self.cat_fill())
        self.cat_n = ttk.Label(top, text='')
        self.cat_n.pack(side='left', **PAD)
        # khung chi tiết đặt trước để luôn còn chỗ khi cửa sổ thấp
        det = ttk.LabelFrame(box, text='Chi tiết')
        det.pack(side='bottom', fill='x', **PAD)
        self.cat_head = ttk.Label(det, text='Chọn một vật phẩm để xem chi tiết.', font=('Segoe UI', 10, 'bold'))
        self.cat_head.pack(anchor='w', **PAD)
        self.cat_use = ttk.Label(det, text='', justify='left')
        self.cat_use.pack(anchor='w', fill='x', **PAD)
        self.cat_desc = ttk.Label(det, text='', justify='left', foreground='#555555')
        self.cat_desc.pack(anchor='w', fill='x', **PAD)
        det.bind('<Configure>', lambda e: (self.cat_use.config(wraplength=e.width - 16),
                                           self.cat_desc.config(wraplength=e.width - 16)))
        row = ttk.Frame(det)
        row.pack(anchor='w', **PAD)
        ttk.Label(row, text='Cho cầm:').pack(side='left')
        self.give_to = ttk.Combobox(row, state='readonly', width=40)
        self.give_to.pack(side='left', **PAD)
        ttk.Button(row, text='Cho cầm', command=self.guard(self.do_give)).pack(side='left', **PAD)
        mid = ttk.Frame(box)
        mid.pack(fill='both', expand=True, **PAD)
        self.ctree = ttk.Treeview(mid, columns=('name', 'use', 'have'), show='headings', height=10, selectmode='browse')
        for c, w, t, a in (('name', 110, 'Vật phẩm', 'w'), ('use', 460, 'Công dụng', 'w'), ('have', 54, 'Đang có', 'center')):
            self.ctree.heading(c, text=t)
            self.ctree.column(c, width=w, anchor=a, stretch=c == 'use')
        sb = ttk.Scrollbar(mid, orient='vertical', command=self.ctree.yview)
        self.ctree.configure(yscrollcommand=sb.set)
        self.ctree.pack(side='left', fill='both', expand=True)
        sb.pack(side='left', fill='y')
        self.ctree.bind('<<TreeviewSelect>>', lambda e: self.guard(self.cat_pick)())
        self.cat_fill()

    def cat_fill(self):
        """Vẽ lại danh mục theo ô tìm và nhóm đang chọn (không cần game)."""
        group, words = self.cat_group.get(), mm_items.fold(self.cat_q.get()).split()
        self.ctree.delete(*self.ctree.get_children())
        n = 0
        for x in self.cat_items:
            if x.match(group, words):
                self.ctree.insert('', 'end', iid=str(x.id), values=(x.name, x.use or x.desc, self.cat_have.get(x.id, 0)))
                n += 1
        self.cat_n.config(text='%d vật phẩm' % n)

    def cat_counts(self):
        """Cập nhật cột "Đang có" theo self.cat_have."""
        for iid in self.ctree.get_children():
            self.ctree.set(iid, 'have', self.cat_have.get(int(iid), 0))

    def cat_pick(self):
        s = self.ctree.selection()
        if s:
            self.bitem.set_id(int(s[0]))
            self.bag_item_chosen()

    def cat_show(self, item):
        x = self.cat_by_id.get(item)
        if not x:
            return
        self.cat_sel = item
        pocket = self.prof.pocket_names[x.pocket - 1] if 1 <= x.pocket <= self.prof.n_pockets else '?'
        self.cat_head.config(text='%s (ID %d)   |   %s   |   Ngăn: %s   |   Giá: %s   |   Đang có: %d' % (
            x.name, x.id, ', '.join(x.groups), pocket, format(x.price, ',').replace(',', '.') if x.price else '-',
            self.cat_have.get(x.id, 0)))
        self.cat_use.config(text='Công dụng: %s' % x.use if x.use else 'Công dụng: xem mô tả trong game bên dưới.')
        self.cat_desc.config(text='Mô tả trong game: %s' % (x.desc or '(không có)'))

    def give_refresh(self):
        """Danh sách con trong đội cho ô "Cho cầm"; giữ nguyên con đang chọn."""
        cur = self.give_to.current()
        mons = self.game.party()
        self.give_slots = [i for i, m in enumerate(mons) if not m.empty]
        vals = ['%d. %s (đang cầm: %s)' % (i + 1, self.rom.species_name(mons[i].species),
                                           self.rom.item_name(mons[i].item) if mons[i].item else 'không')
                for i in self.give_slots]
        self.give_to.config(values=vals)
        if vals:
            self.give_to.current(cur if 0 <= cur < len(vals) else 0)

    def do_give(self):
        if self.cat_sel is None:
            raise ValueError('Chọn vật phẩm trong danh mục trước.')
        if self.give_to.current() < 0:
            raise ValueError('Đội đang trống.')
        st = self.game.battle_state()
        if st and st[0]:
            raise ValueError('Đang trong trận, xong trận hãy cho cầm.')
        slot = self.give_slots[self.give_to.current()]
        m = self.game.party()[slot]
        if m.empty:
            raise ValueError('Ô này đang trống, hãy tải lại.')
        old = self.rom.item_name(m.item) if m.item else None
        m.item = self.cat_sel
        self.game.write_mon(slot, m)
        self.give_refresh()
        self.say('%s đã cầm %s%s. Không trừ trong túi. Nhớ lưu game.' % (
            self.rom.species_name(m.species), self.rom.item_name(self.cat_sel), ' (thay %s)' % old if old else ''))

    def open_bag(self):
        """Mở tab Túi đồ: đọc ngăn đang xem; có danh mục thì đọc thêm mọi ngăn và đội."""
        if self.cat_items:
            self.cat_have = {}
            for i in range(self.prof.n_pockets):
                self.cat_have.update(self.game.read_pocket(i))
            self.give_refresh()
        self.refresh_money()
        self.refresh_bag()

    def refresh_bag(self):
        idx = self.pocket.current()
        self.btree.delete(*self.btree.get_children())
        self.pocket_items = self.game.read_pocket(idx)
        for item, q in self.pocket_items:
            iid = str(item) if not self.btree.exists(str(item)) else ''
            self.btree.insert('', 'end', iid=iid, values=(item, self.rom.item_name(item), q))
        if self.cat_items:
            have = dict(self.pocket_items)
            changed = {k: v for k, v in have.items() if self.cat_have.get(k) != v}
            changed.update({x.id: 0 for x in self.cat_items if x.pocket - 1 == idx and x.id not in have and self.cat_have.get(x.id)})
            if changed:
                self.cat_have.update(changed)
                self.cat_counts()
            if self.cat_sel is not None:
                self.cat_show(self.cat_sel)
        self.say('Đã đọc ngăn "%s".' % self.prof.pocket_names[idx])

    def bag_item_chosen(self):
        """Chọn vật phẩm xong: tự nạp ngăn túi của nó, điền sẵn số lượng hiện có (hoặc mặc định nếu chưa có)."""
        item = parse_id(self.bitem.get(), self.item_vals)
        if self.cat_items:
            self.cat_show(item)
        pk = self.rom.item_pocket(item)
        if not 1 <= pk <= self.prof.n_pockets:
            raise ValueError('vật phẩm %d không có ngăn túi' % item)
        self.pocket.current(pk - 1)
        self.refresh_bag()
        have = dict(self.pocket_items).get(item)
        self.bqty.set(have if have is not None else (1 if pk - 1 == self.prof.key_pocket else 99))
        if have is not None and self.btree.exists(str(item)):
            self.btree.selection_set(str(item))
            self.btree.see(str(item))
        self.say('%s: %s. Chỉnh số lượng rồi bấm "Thêm / đặt số lượng".' % (
            self.rom.item_name(item), 'đang có ×%d' % have if have is not None else 'chưa có trong túi'))

    def bag_pick(self):
        s = self.btree.selection()
        if s:
            item, _, q = self.btree.item(s[0], 'values')
            self.bitem.set_id(int(item))
            self.bqty.set(int(q))
            if self.cat_items:
                self.cat_show(int(item))

    def bag_set(self, zero=False):
        item = parse_id(self.bitem.get(), self.item_vals)
        msg = self.game.set_item(item, 0 if zero else int(self.bqty.get()))
        # chuyển hiển thị sang ngăn chứa vật phẩm vừa sửa
        pk = self.rom.item_pocket(item)
        if 1 <= pk <= self.prof.n_pockets:
            self.pocket.current(pk - 1)
        self.refresh_bag()
        self.say('Đã đặt: %s. Nhớ lưu game.' % msg)

    # ------------------------------------------------------------ tab Bản đồ
    Q_COL = {'Vật phẩm nhặt được': '#e53935', 'Vật phẩm ẩn': '#f9a825', 'Trainer': '#8e24aa', 'Chướng ngại': '#fb8c00',
             'NPC: cho / đổi / bán': '#2e7d32', 'Đi tiếp': '#1e66d0', 'Sự kiện tự chạy': '#00838f'}

    def _build_quest(self):
        import mm_story
        self.story = mm_story.Story(self.rom)
        self.q_maps = [(g, n, '%s (%d.%d)' % (self.rom.map_name(g, n), g, n)) for g, n in self.story.maps()]
        self.q_cur, self.q_shown, self.q_sig, self.q_world, self.q_img = None, None, None, None, None
        self.q_entries, self.q_marks, self.q_player = [], {}, None
        f = self.t_quest
        self.q_follow = tk.BooleanVar(value=True)              # bản đồ theo map đang đứng (tắt khi chọn xem map khác)
        self.q_foe, self.q_wsig, self.q_wopen, self.q_wgroups = None, None, {}, {}
        self.q_fly_pts, self.q_roam, self.q_rsig = [], [], None
        # --- thanh trên (1 dòng): map đang xem + về chỗ mình | bay | tìm khắp thế giới
        top = ttk.Frame(f)
        top.pack(fill='x', **PAD)
        self.q_sum = ttk.Label(top, text='📍', font=('Segoe UI', 11, 'bold'), foreground='#c62828')
        self.q_sum.pack(side='left')
        self.q_combo = ttk.Combobox(top, values=[x[2] for x in self.q_maps], state='readonly', width=30)
        self.q_combo.pack(side='left', **PAD)
        self.q_combo.bind('<<ComboboxSelected>>', lambda e: self.guard(self.quest_pick)())
        Tip(self.q_combo, 'Chọn để xem map khác (bản đồ thôi theo nhân vật). Bấm "Xem map đang đứng" để theo lại.')
        hb = ttk.Button(top, text='👁 Xem map đang đứng', command=self.guard(self.quest_home))
        hb.pack(side='left')
        Tip(hb, 'Chỉ đổi bản đồ trong tool về map nhân vật đang đứng (dùng sau khi chọn xem map khác). Không bay. '
                'Muốn bay thì dùng ô ✈ bên cạnh.')
        self.q_fly_pts = self.game.fly_points()                 # bay thẳng tới điểm Fly của game (không cần chiêu Fly)
        names = []
        for g, n, x, y in self.q_fly_pts:
            nm = self.rom.map_name(g, n)
            names.append(nm + (' (Pokémon Center)' if nm.startswith('ROUTE') else ''))
        ttk.Label(top, text='   ✈').pack(side='left')
        self.q_fly = ttk.Combobox(top, values=names, state='readonly', width=20)
        self.q_fly.set('Bay tới…')
        self.q_fly.pack(side='left', **PAD)
        self.q_fly.bind('<<ComboboxSelected>>', lambda e: self.guard(self.quest_fly)())
        Tip(self.q_fly, 'Chọn nơi là bay luôn (như chiêu Fly, không cần có chiêu). Chỉ bay khi đang đi ngoài trời.')
        self.q_home = ttk.Button(top, text='🏠 Về chỗ cũ', command=self.guard(self.fly_home))
        self.q_home.pack(side='left', padx=(2, 0))
        self.q_home_tip = Tip(self.q_home, '')                # chữ đặt trong upd_home_btn (kèm chỗ sẽ về)
        self.upd_home_btn()
        self.hunt = None
        self.q_hunt = ttk.Button(top, text='🌿 Săn', command=self.guard(self.hunt_toggle))
        self.q_hunt.pack(side='left', padx=(2, 0))
        self.q_hunt_mb = ttk.Menubutton(top, text=self.hunt_mb_text())
        self.q_hunt_mb.pack(side='left')
        self.q_hunt_menu = tk.Menu(self.q_hunt_mb, tearoff=0)
        self.q_hunt_mb['menu'] = self.q_hunt_menu
        self.hunt_menu_build()
        Tip(self.q_hunt_mb, 'Chọn loại Pokémon tool sẽ tự bắt khi săn (tick nhiều ô được). Vd chỉ tick Shiny = săn shiny thôi, '
                            'con khác đều Chạy.')
        Tip(self.q_hunt, 'Săn tự động: đứng trong cỏ (hoặc đang lướt trên nước) rồi bấm. Tool tự đi qua lại 2 ô, gặp '
                         'Pokémon thường thì chọn Chạy. Tự BẮT các loại đã tick ở nút "Bắt gì" bên cạnh (Shiny / IV ≥ mức % / chưa có Pokédex / Huyền thoại).\n'
                         '• Huyền thoại, hoặc "% bắt" lúc gặp < 10% (như cột % bắt ở Lịch sử): ném Master Ball ngay.\n'
                         '• Còn lại: con đầu đội False Swipe (không giới hạn lần) tới khi đối thủ còn 1 HP rồi ném Ultra Ball '
                         '(hệ Ma: ném luôn).\n'
                         'False Swipe hết PP / ném 20 Ultra Ball chưa được → chuyển sang Master Ball. Bóng còn dưới 10 '
                         'quả thì tool tự nạp lên 99.\n'
                         'Gặp trainer, sang map khác, ra khỏi cỏ, con đầu gục hay bấm lại nút này cũng dừng.\n\n'
                         'Bấm phím qua mm_bridge.lua nên không cần để mGBA ở trên, bạn vẫn dùng máy bình thường.')
        self.q_find = tk.StringVar()
        ttk.Button(top, text='✕', width=3, command=lambda: self.q_find.set('')).pack(side='right')
        fe = ttk.Entry(top, textvariable=self.q_find, width=22)
        fe.pack(side='right', **PAD)
        ttk.Label(top, text='🔎').pack(side='right')
        Tip(fe, 'Tìm khắp thế giới: vật phẩm, trainer, NPC... Bấm một kết quả để mở map đó.')
        self.q_find.trace_add('write', lambda *a: (self.after_cancel(self._q_job) if getattr(self, '_q_job', None) else None,
                                                    setattr(self, '_q_job', self.after(350, self.guard(self.quest_render)))))
        pane = ttk.PanedWindow(f, orient='horizontal')
        pane.pack(fill='both', expand=True, **PAD)
        # --- trái: tab con
        left = ttk.Frame(pane)
        self.q_nb = ttk.Notebook(left)
        self.q_nb.pack(fill='both', expand=True)
        gbox = ttk.Frame(self.q_nb)                              # 📋 Việc cần làm
        self.q_nb.add(gbox, text='📋 Việc')
        self.q_text = tk.Text(gbox, wrap='word', font=('Segoe UI', 10), cursor='arrow', padx=8, pady=6, spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(gbox, orient='vertical', command=self.q_text.yview)
        self.q_text.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.q_text.pack(fill='both', expand=True)
        for T in (self.q_text,):
            T.tag_configure('head', font=('Segoe UI', 11, 'bold'), spacing1=10)
            T.tag_configure('done', foreground='#9a9a9a')
            T.tag_configure('hl', background='#fff3b0')
            T.tag_configure('route', foreground='#8e24aa')
            T.tag_configure('route_now', foreground='#8e24aa', font=('Segoe UI', 10, 'bold'), background='#f3e5f5')
            T.tag_configure('route_x', foreground='#8e24aa', underline=True)
            T.tag_configure('hint', foreground='#666', font=('Segoe UI', 9, 'italic'))
            T.tag_configure('detail', foreground='#37474f', font=('Segoe UI', 9), lmargin1=26, lmargin2=26,
                            background='#f3f6fa', spacing1=0, spacing3=4)
        gw = ttk.Frame(self.q_nb, padding=4)                     # 🐾 Pokémon hoang dã ở map đang xem
        self.q_t_wild = gw
        self.q_nb.add(gw, text='🐾 Pokémon')
        wt = ttk.Frame(gw)
        wt.pack(fill='x')
        ttk.Checkbutton(wt, text='Ẩn loài đã bắt', variable=self.hide_caught,
                        command=lambda: (self.save_area_state(), self.guard(lambda: self.quest_wild(force=True))())
                        ).pack(side='left')
        info_icon(wt, 'Tỉ lệ = xác suất mỗi lần gặp theo cách gặp (cỏ / lướt nước / đập đá / từng loại cần câu). '
                      'Nền vàng = loài đang đối đầu; tím = huyền thoại lang thang đang ở map này. '
                      'Bấm một loài để xem chi tiết; bấm vùng tô trên bản đồ để mở nhóm tương ứng.').pack(side='left', padx=6)
        ttk.Style().configure('Small.Treeview', rowheight=34)
        self.q_wtree = ttk.Treeview(gw, columns=('lv', 'pct', 'got'), show='tree headings', style='Small.Treeview')
        self.q_wtree.heading('#0', text='Pokémon')
        self.q_wtree.column('#0', width=230)
        for c, w, t in (('lv', 60, 'Level'), ('pct', 60, 'Tỉ lệ'), ('got', 60, 'Đã bắt')):
            self.q_wtree.heading(c, text=t)
            self.q_wtree.column(c, width=w, anchor='center')
        wsb = ttk.Scrollbar(gw, orient='vertical', command=self.q_wtree.yview)
        self.q_wtree.configure(yscrollcommand=wsb.set)
        wsb.pack(side='right', fill='y')
        self.q_wtree.pack(fill='both', expand=True)
        self.q_wtree.tag_configure('method', font=('Segoe UI', 10, 'bold'), background='#e8eef7')
        self.q_wtree.tag_configure('cur', background='#fff3c4')
        self.q_wtree.tag_configure('got', foreground='#8a8a8a')
        self.q_wtree.tag_configure('roam', background='#f3e5ff')
        for ev in ('<<TreeviewOpen>>', '<<TreeviewClose>>'):          # nhớ nhóm thu/mở khi danh sách vẽ lại
            self.q_wtree.bind(ev, lambda e: self.after_idle(lambda: self.q_wopen.update(
                {self.q_wtree.item(i, 'text').split('   (')[0]: bool(self.q_wtree.item(i, 'open'))
                 for i in self.q_wtree.get_children()})), add='+')
        self.q_wtree.bind('<<TreeviewSelect>>', lambda e: self.guard(self.quest_pick_species)())
        self.q_t_det = ttk.Frame(self.q_nb)                     # 🔍 Chi tiết: dùng chung khung với tab Kho
        self.q_nb.add(self.q_t_det, text='🔍 Chi tiết')
        self.q_fd = self._build_detail(self._scroll_frame(self.q_t_det))
        self.foe_clear('Chưa có dữ liệu', self.q_fd)
        self.q_fd.sub.config(text='Vào trận để xem đối thủ, hoặc bấm một loài ở tab 🐾 Pokémon.')
        gh = ttk.Frame(self.q_nb, padding=6)                     # 📜 Lịch sử đã gặp
        self.q_nb.add(gh, text='📜 Lịch sử')
        ht = ttk.Frame(gh)
        ht.pack(fill='x')
        self.q_shiny_lbl = ttk.Label(ht, text='', font=('Segoe UI', 10, 'bold'))
        self.q_shiny_lbl.pack(side='left', padx=4)
        info_icon(ht, 'Lần gặp = số Pokémon hoang dã đã gặp kể từ shiny gần nhất (tỉ lệ gốc 1/%d); dòng shiny ghi N/%d (%%). '
                      'Lưu trong shiny_count.json, tắt tool vẫn giữ.\n'
                      '%% bắt = xác suất bắt bằng Poké Ball lúc vừa gặp (công thức FireRed: tỉ lệ bắt, HP, trạng thái; '
                      'ngủ/đóng băng x2, độc/bỏng/tê x1.5). Great Ball x1.5, Ultra Ball x2.\n'
                      'IV ✔ = nên bắt (5 IV có ích ≥75%%), nền xanh đậm = tuyệt vời (≥90%%). Bấm một dòng để xem chi tiết.\n'
                      'Bật/tắt báo và tăng tỉ lệ shiny: nút ⚙ Cài đặt.' % (SHINY_ODDS, SHINY_ODDS)
                  ).pack(side='left', anchor='n', padx=4)
        hf = ttk.Frame(gh)                                       # bộ lọc (Duy 07/11)
        hf.pack(fill='x', pady=(4, 2))
        ttk.Label(hf, text='Lọc:').pack(side='left', padx=(4, 2))
        self.h_time = ttk.Combobox(hf, state='readonly', width=11, values=[t for _, t in self.HIST_TIMES])
        self.h_time.current(0)
        self.h_time.pack(side='left', padx=2)
        self.h_time.bind('<<ComboboxSelected>>', lambda e: self.guard(self.hist_render)())
        self.h_shiny, self.h_iv = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        ttk.Checkbutton(hf, text='★ Chỉ shiny', variable=self.h_shiny,
                        command=self.guard(self.hist_render)).pack(side='left', padx=4)
        ttk.Checkbutton(hf, text='✔ Chỉ IV cao', variable=self.h_iv,
                        command=self.guard(self.hist_render)).pack(side='left', padx=4)
        self.h_cnt = ttk.Label(hf, text='', foreground='#666')
        self.h_cnt.pack(side='right', padx=4)
        Tip(hf, 'Lịch sử lưu trong encounter_history.jsonl (tắt tool vẫn còn; mở tool nạp %d lần gặp gần nhất).\n'
                'IV cao = nên bắt trở lên (5 IV có ích ≥75%%, như dấu ✔ ở cột IV).' % self.HIST_KEEP)
        self.q_htree = self._make_htree(gh, 20)
        self.q_htree.pack(fill='both', expand=True)
        self.htrees.append(self.q_htree)                        # refresh_foe ghi lịch sử vào đây
        self.hist_render()
        self.q_htree.bind('<<TreeviewSelect>>', lambda e: self.guard(self.quest_pick_hist)())
        self.upd_shiny_lbl()
        gr = self.q_t_roam = ttk.Frame(self.q_nb, padding=6)     # 🐉 Pokémon huyền thoại lang thang
        self.q_nb.add(gr, text='🐉 Huyền thoại')
        rt = ttk.Frame(gr)
        rt.pack(fill='x')
        ttk.Button(rt, text='✈ Bay tới con đang chọn', command=self.guard(self.quest_fly_roamer)).pack(side='left')
        if getattr(self.prof, 'roamers', None):                   # FireRed gốc: không có bảng roamer để thả
            ttk.Button(rt, text='🐉 Thả 1 con ngay', command=self.guard(self.roam_spawn_now)).pack(side='left', padx=4)
        info_icon(rt, 'Huyền thoại chạy lung tung trên thế giới (chính là các icon trên bản đồ Fly). Đứng cùng map với nó '
                      'rồi đi trong cỏ/nước: mỗi lần gặp Pokémon hoang dã có 25% là nó. Nó đổi map khi bạn đổi map; '
                      'HP và trạng thái giữ nguyên giữa các lần gặp.\n'
                      'Bấm một dòng = mở map đó. BẤM ĐÚP = bay tới bãi cỏ trên map của nó, tới nơi tool giữ nó lại ở map đó '
                      '(bay/vào cửa làm nó nhảy chỗ khác; đi bộ sang map khác thì nó chạy tiếp như thường).\n'
                      'Tự thả huyền thoại: bật/tắt ở nút ⚙ Cài đặt. "· tool" = con do tool thả.').pack(side='left', padx=6)
        ttk.Style().configure('Roam.Treeview', rowheight=44)
        self.q_rtree = ttk.Treeview(gr, columns=('lv', 'hp', 'iv', 'where'), show='tree headings',
                                    style='Roam.Treeview', height=5)
        self.q_rtree.heading('#0', text='Pokémon')
        self.q_rtree.column('#0', width=150)
        for c, w, t in (('lv', 40, 'Lv'), ('hp', 50, 'HP'), ('iv', 110, 'IV'), ('where', 160, 'Đang ở')):
            self.q_rtree.heading(c, text=t)
            self.q_rtree.column(c, width=w, anchor='center')
        self.q_rtree.tag_configure('here', background='#fff3c4')
        self.q_rtree.pack(fill='x', pady=(4, 0))
        self.q_rtree.bind('<<TreeviewSelect>>', lambda e: self.guard(self.quest_pick_roamer)())
        self.q_rtree.bind('<Double-1>', lambda e: self.guard(self.quest_fly_roamer)())
        self.q_rtimer = ttk.Label(gr, text='', foreground='#1b5e20')
        self.q_rtimer.pack(anchor='w', pady=(4, 0))
        self.q_rnote = ttk.Label(gr, text='', foreground='gray', wraplength=440, justify='left')
        self.q_rnote.pack(anchor='w', pady=4)
        gs = ttk.Frame(self.q_nb)                                # 📖 Cốt truyện chính
        self.q_t_story = gs
        self.q_nb.add(gs, text='📖 Cốt truyện')
        ttk.Button(gs, text='🔓 Mở khoá săn shiny', command=self.guard(self.quest_unlock_all)).pack(side='top', anchor='w',
                                                                                                    padx=4, pady=(4, 0))
        self.q_stext = tk.Text(gs, wrap='word', font=('Segoe UI', 10), cursor='arrow', padx=8, pady=6, spacing1=2, spacing3=2)
        ssb = ttk.Scrollbar(gs, orient='vertical', command=self.q_stext.yview)
        self.q_stext.configure(yscrollcommand=ssb.set)
        ssb.pack(side='right', fill='y')
        self.q_stext.pack(fill='both', expand=True)
        self.q_stext.tag_configure('head', font=('Segoe UI', 11, 'bold'), spacing1=10)
        self.q_stext.tag_configure('done', foreground='#9a9a9a')
        self.q_stext.tag_configure('hint', foreground='#666', font=('Segoe UI', 9, 'italic'))
        self.q_nb.bind('<<NotebookTabChanged>>', lambda e: self.guard(self.quest_subtab)())
        self.q_fshown, self.q_auto, self.q_witems, self.q_lastfoe = None, False, {}, None
        pane.add(left, weight=3)
        # --- phải: chỉ có bản đồ + 1 dòng trạng thái
        right = ttk.Frame(pane)
        bar = ttk.Frame(right)
        bar.pack(side='bottom', fill='x')
        lg = ttk.Label(bar, text='❔ Chú thích', foreground='#1565c0', cursor='hand2')
        lg.pack(side='right', padx=4)                       # pack trước để dòng trạng thái dài không đẩy mất
        self.q_wlbl = tk.Label(bar, text='', anchor='w', justify='left', font=('Segoe UI', 10, 'bold'), foreground='#c62828',
                               cursor='hand2')
        self.q_wlbl.pack(side='left', fill='x', expand=True, padx=4)
        self.q_wlbl.bind('<Button-1>', lambda e: self.guard(self.quest_show_foe)())
        self.q_wlbl.bind('<Configure>', lambda e: self.q_wlbl.config(wraplength=max(200, e.width - 8)))   # hẹp thì xuống dòng
        lg.bind('<Button-1>', lambda e: self.quest_legend(lg))
        cbox = ttk.Frame(right)
        cbox.pack(fill='both', expand=True)
        self.q_cv = tk.Canvas(cbox, background='#222', width=560, highlightthickness=0)
        # tự kéo / lăn bản đồ = tạm ngưng đi theo nhân vật (quest_cam_pause)
        ys = ttk.Scrollbar(cbox, orient='vertical', command=lambda *a: (self.quest_cam_pause(), self.q_cv.yview(*a)))
        xs = ttk.Scrollbar(cbox, orient='horizontal', command=lambda *a: (self.quest_cam_pause(), self.q_cv.xview(*a)))
        self.q_cv.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side='right', fill='y')
        xs.pack(side='bottom', fill='x')
        self.q_cv.pack(fill='both', expand=True)
        self.q_cv.bind('<MouseWheel>', lambda e: (self.quest_cam_pause(), self.q_cv.yview_scroll(-e.delta // 120 * 3, 'units')))
        self.q_cv.bind('<Shift-MouseWheel>', lambda e: (self.quest_cam_pause(), self.q_cv.xview_scroll(-e.delta // 120 * 3, 'units')))
        self.q_cv.bind('<Control-MouseWheel>', lambda e: self.guard(self.quest_zoom)(e))
        # Tk 8.6 trên Windows chỉ gửi bánh xe chuột cho widget đang có focus (đo 06/11) -> rê vào bản đồ thì lấy focus,
        # rê ra thì trả lại chỗ cũ (ô tìm kiếm...)
        def _enter(e):
            try:
                self._q_prev_focus = self.focus_get()         # có lúc lỗi KeyError với popdown của Combobox
            except (KeyError, tk.TclError):
                self._q_prev_focus = None
            self.q_cv.focus_set()
        def _leave(e):
            w = getattr(self, '_q_prev_focus', None)
            try:
                if w is not None and w is not self.q_cv and self.focus_get() is self.q_cv:
                    w.focus_set()
            except (KeyError, tk.TclError):
                pass
        self.q_cv.bind('<Enter>', _enter)
        self.q_cv.bind('<Leave>', _leave)
        self.q_cam, self.q_cam_at, self.q_cam_map = True, None, None
        self.q_zoom = self.settings.get('map_zoom')            # None = tự chọn (map nhỏ ×2, map to ×1)
        if self.q_zoom not in (1, 2, 3, 4):
            self.q_zoom = None
        self.q_fast_key = None                                 # vòng nhanh: (map, x, y, hướng) lần vẽ trước
        self.after(300, self.tick_player_fast)
        self.q_cam_btn = tk.Button(cbox, text='🎯 Theo nhân vật', bg='#c62828', fg='white', relief='flat', cursor='hand2',
                                   font=('Segoe UI', 9, 'bold'), command=lambda: self.guard(self.quest_cam_resume)())
        self.q_zoom_lbl = tk.Label(cbox, text='', bg='#333', fg='white', font=('Segoe UI', 9))
        self.q_cv.bind('<Button-1>', lambda e: self.guard(self.quest_zone_click)(e))
        pane.add(right, weight=2)

    def quest_legend(self, anchor):
        """Bảng chú thích màu (bấm "❔ Chú thích" để bật/tắt)."""
        old = getattr(self, '_q_leg', None)
        if old is not None and old.winfo_exists():
            old.destroy()
            return
        w = self._q_leg = tk.Toplevel(self)
        w.overrideredirect(True)
        w.attributes('-topmost', True)
        box = tk.Frame(w, background='#ffffff', padx=10, pady=8, highlightthickness=1, highlightbackground='#888')
        box.pack()
        rows = [(self.Q_COL[sec], '●', txt) for sec, txt in (
            ('Chướng ngại', 'chướng ngại (cây Cut, đá...)'), ('Đi tiếp', 'lối đi sang map khác'), ('Vật phẩm ẩn', 'đồ giấu'),
            ('Vật phẩm nhặt được', 'bóng vật phẩm'), ('Trainer', 'trainer'), ('NPC: cho / đổi / bán', 'NPC cho / đổi / bán'),
            ('Sự kiện tự chạy', 'sự kiện tự chạy'))]
        rows += [('red', '■', 'bạn (xám = việc đã xong)'), ('#e6b800', '▢', 'cỏ / sàn hang có Pokémon'),
                 ('#0a5cff', '▢', 'nước có Pokémon (Surf / câu cá)')]
        for col, sym, txt in rows:
            r = tk.Frame(box, background='#ffffff')
            r.pack(anchor='w')
            tk.Label(r, text=sym, foreground=col, background='#ffffff', font=('Segoe UI', 12, 'bold')).pack(side='left')
            tk.Label(r, text=' ' + txt, background='#ffffff').pack(side='left')
        tk.Label(box, text='bấm vào vùng tô để xem loài · bấm chấm số để xem việc · bấm để đóng', foreground='#777',
                 background='#ffffff', font=('Segoe UI', 8)).pack(anchor='w', pady=(4, 0))
        for wd in [w, box] + list(box.winfo_children()):
            wd.bind('<Button-1>', lambda e: w.destroy())
        w.update_idletasks()
        w.geometry('+%d+%d' % (anchor.winfo_rootx() + anchor.winfo_width() - w.winfo_reqwidth(),
                               anchor.winfo_rooty() - w.winfo_reqheight() - 4))

    def quest_home(self):
        """Nút "Về chỗ mình": bản đồ theo lại map đang đứng."""
        self.q_follow.set(True)
        self.q_find.set('')
        self.quest_cam_resume(see=False)
        self.quest_tick(force=True)

    def quest_subtab(self):
        if self.q_nb.select() == str(self.q_t_story):
            self.quest_story()

    @staticmethod
    def circ(n):
        return chr(0x2460 + n - 1) if 1 <= n <= 20 else '(%d)' % n

    def quest_tick(self, force=False):
        gn = self.game.current_map()
        self.q_cur = gn
        if self.hunt_goal and gn == self.hunt_goal:           # chỉ đường: đã tới nơi
            self.route_set(None)
            self.say('🧭 Đã tới %s. Vào cỏ (viền vàng) rồi bấm 🌿 Săn.' % self.rom.map_name(*gn))
            force = True
        self.q_sb1 = self.game.sb1()                          # cho vòng nhanh tick_player_fast (đọc từ bản chụp)
        self.q_foe = self.quest_foe()
        if self.q_t_roam:
            self.q_roam = self.game.roamers()
            self.quest_roamers()
        if self.q_follow.get() and (gn != self.q_shown or force):
            name = next((x[2] for x in self.q_maps if (x[0], x[1]) == gn), None)
            if name:
                self.q_combo.set(name)
                self.q_shown = gn
                self.quest_render()
                return
        if force:
            self.quest_render()
            return
        if self.q_shown and not self.q_find.get().strip():
            flag = self.game.flags()
            sig = tuple(self.story.status(r, flag) for r in self.story.rows(*self.q_shown))
            if sig != self.q_sig:                             # vừa nhặt/đánh xong -> vẽ lại danh sách + chấm
                self.quest_render()
                return
        if gn == self.q_shown and not self.q_follow.get():   # tự tới đúng map đang xem (vd bay tới huyền thoại)
            self.q_follow.set(True)
        self.quest_sum_label()
        self.quest_player()
        self.quest_wild()

    def quest_roamers(self):
        """Tab con "🐉 Huyền thoại": chỉ vẽ lại khi roamer đổi map/HP hoặc bạn đổi map."""
        sig = (self.q_cur, tuple((x['slot'], x['species'], x['map'], x['hp'], x['level'], x['status']) for x in self.q_roam))
        if sig == self.q_rsig:
            return
        self.q_rsig = sig
        t = self.q_rtree
        t.delete(*t.get_children())
        here = []
        for x in self.q_roam:
            g, _, _ = iv_grade(x['iv'], self.rom.base_stats(x['species']))
            name = self.rom.species_name(x['species'])
            at = x['map'] == self.q_cur
            if at:
                here.append(name)
            mine = [x['slot'], x['pid']] in self.roam_spawned
            t.insert('', 'end', iid=str(x['slot']), text='  ' + name + (' · tool' if mine else ''),
                     image=self.photo(x['species'], False, 0.625) or '',
                     values=(x['level'], x['hp'], '%d · %s' % (sum(x['iv']), IV_GRADES[g]),
                             self.rom.map_name(*x['map']) + (' (ĐÂY)' if at else '')
                             + ('' if self.roamer_can_meet(x) else ' ✘')),
                     tags=('here',) if at else ())
        self.q_nb.tab(self.q_t_roam, text='🐉 Huyền thoại (%d)' % len(self.q_roam))
        kinds = lambda x: ' / '.join(k for k, v in (('cỏ', x['land']), ('nước', x['water'])) if v)
        self.q_rnote.config(
            text=('⚠ Đang ở cùng map với bạn: %s.\n' % ', '.join(here) if here else '')
            + '\n'.join('%s: chỉ gặp trong %s; IV HP/Atk/Def/Spe/SpA/SpD = %s%s' % (
                self.rom.species_name(x['species']), kinds(x) or '?', '/'.join(map(str, x['iv'])),
                '' if self.roamer_can_meet(x) else '\n   ✘ Map nó đang ở không có %s nên chưa gặp được, đổi map vài lần để nó '
                                                   'chạy sang chỗ khác.' % kinds(x)) for x in self.q_roam)
            or 'Hiện chưa có Pokémon huyền thoại nào đang lang thang.')
        if self.q_shown:
            self.quest_wild(force=True)

    def roamer_can_meet(self, x):
        """Map roamer đang đứng có kiểu gặp hợp với nó không (vd chỉ gặp trên cạn mà map chỉ có Surf -> chưa gặp được).
        Theo cách FireRed kiểm tra (map không có bảng cỏ thì không có lượt gặp trên cạn), chưa đọc riêng code hack."""
        w = self.rom.wild_for_map(*x['map']) or {}
        return (x['land'] and 'land' in w) or (x['water'] and 'water' in w)

    def quest_fly_roamer(self):
        """Bấm đúp: bay tới ô cỏ (hoặc bờ nước) trên map của roamer; warp làm mọi roamer nhảy chỗ khác
        (LoadMapFromWarp 0x08055970 gọi RoamerMoveToOtherLocationSet) nên tới nơi tick_roam_keep ghi nó về lại map đó."""
        s = self.q_rtree.selection()
        x = next((x for x in self.q_roam if s and str(x['slot']) == s[0]), None)
        if not x:
            return
        name, (g, n) = self.rom.species_name(x['species']), x['map']
        w = self.rom.wild_for_map(g, n) or {}
        kind = 'land' if x['land'] and 'land' in w else 'water' if x['water'] and 'water' in w else None
        spot = self.story.landing_tile(g, n, kind) if kind else None
        if not spot:
            self.fly_refused('%s đang ở %s nhưng map này không có %s nên không gặp được nó.\n\n'
                             'Đi qua lại vài map (vào cửa / qua mép map) cho nó chạy sang chỗ khác rồi bấm đúp lại.' % (
                                 name, self.rom.map_name(g, n), 'cỏ' if x['land'] else 'nước'))
            return
        why = self.fly_tool(g, n, *spot)
        if why:
            self.fly_refused(why)
            return
        self.roam_keep =dict(slot=x['slot'], species=x['species'], map=(g, n), until=time.time() + 40)
        self.q_follow.set(True)
        self.say('✈ Đang bay tới %s (ô %d,%d) để săn %s…' % (self.rom.map_name(g, n), spot[0], spot[1], name))

    def tick_roam_keep(self):
        """Sau khi bay tới map của roamer: đợi tới nơi (đúng map + overworld) rồi ghi vị trí roamer về map đó."""
        k = self.roam_keep
        if time.time() > k['until']:
            self.roam_keep = None
            self.say('Bay chưa tới nơi sau 40 giây, tool không giữ huyền thoại lại.', False)
            return
        st = self.game.battle_state()
        if self.game.current_map() != k['map'] or not st or not st[1]:
            return
        base = self.prof.roamers[0] + 0x18 * k['slot']
        raw = self.bridge.read(base, 0x18)
        if struct.unpack_from('<H', raw, 8)[0] != k['species']:
            self.roam_keep = None                             # ô roamer đã đổi (bắt/hạ rồi?): thôi
            return
        if (raw[0x16], raw[0x17]) == k['map']:                 # game chưa dời nó (còn đang tải map): đợi tối đa 5 giây
            k.setdefault('arrived', time.time())
            if time.time() - k['arrived'] < 5:
                return
        else:
            self.bridge.write(base + 0x16, bytes(k['map']))
        self.say('★ %s đã ở %s với bạn: đi trong cỏ, mỗi lần gặp có 25%% là nó.' % (
            self.rom.species_name(k['species']), self.rom.map_name(*k['map'])))
        self.roam_keep = None

    ROAM_EVERY, ROAM_MAX, ROAM_FREE = 20 * 60, 2, 5     # 20 phút chơi/con, tối đa 2 con của tool, chừa 5 ô cho sự kiện hack

    def roam_mine(self, ros):
        """Các roamer do tool thả còn sống (đúng ô + đúng PID; bắt/hạ rồi thì ô trống hoặc là con khác)."""
        live = {(x['slot'], x['pid']) for x in ros}
        return [s for s in self.roam_spawned if tuple(s) in live]

    def tick_roam_spawn(self):
        """Mỗi giây: cộng giờ chơi (chỉ khi game trả lời), đủ 20 phút và tool đang có < 2 con thì thả 1 con."""
        if not self.roam_auto.get() or not getattr(self.prof, 'roamers', None):     # FireRed gốc: không tự thả
            return
        ros = self.game.roamers()
        mine = self.roam_mine(ros)
        if mine != self.roam_spawned:                        # con của tool đã bị bắt/hạ
            self.roam_spawned = mine
            self.save_area_state()
        now = time.time()
        dt, self.roam_last = (min(2.0, now - self.roam_last) if self.roam_last else 0), now
        lbl = getattr(self, 'q_rtimer', None)
        if len(mine) >= self.ROAM_MAX:
            if lbl:
                lbl.config(text='Tool đang có %d con lang thang (tối đa %d): bắt bớt thì đồng hồ chạy tiếp.' % (
                    len(mine), self.ROAM_MAX))
            return                                           # đủ con: đồng hồ dừng, bắt xong 1 con mới chạy tiếp
        self.roam_timer += dt
        if lbl:
            left = max(0, self.ROAM_EVERY - self.roam_timer)
            lbl.config(text='Con tiếp theo sau %d:%02d phút chơi (tool đang có %d/%d con).' % (
                left // 60, left % 60, len(mine), self.ROAM_MAX))
        if now - getattr(self, '_roam_saved', 0) > 60:
            self._roam_saved = now
            self.save_area_state()                           # lưu đồng hồ mỗi phút, tắt tool không mất
        if self.roam_timer >= self.ROAM_EVERY:
            st = self.game.battle_state()
            if st and st[1] and not st[0]:                   # chỉ thả khi đang đi ngoài bản đồ
                self.roam_spawn(ros)

    def roam_spawn(self, ros=None):
        """Thả 1 huyền thoại ngẫu nhiên vào ô roamer trống cuối bảng; trả về lý do nếu không thả được."""
        ros = self.game.roamers() if ros is None else ros
        base, cnt = self.prof.roamers
        used = {x['slot'] for x in ros}
        free = [i for i in range(cnt) if i not in used]
        if len(free) <= self.ROAM_FREE:
            return 'Bảng huyền thoại gần đầy (còn %d ô), chừa chỗ cho sự kiện của game.' % len(free)
        import random
        sp = random.choice(legend_species(self.rom))
        lv = max([m.level for m in self.game.party() if not m.empty and m.checksum_ok and 1 <= m.level <= 100] or [50])
        raw = make_roamer(self.rom, sp, lv)
        slot = free[-1]                                      # sự kiện của game lấy ô trống đầu tiên -> tool lấy từ cuối
        self.bridge.write(base + 0x18 * slot, raw)
        self.roam_spawned.append([slot, struct.unpack_from('<I', raw, 4)[0]])
        self.roam_timer = 0
        self.save_area_state()
        where = self.rom.map_name(3, raw[0x17])
        self.say('🐉 Có huyền thoại mới: %s Lv %d ở %s (xem tab Huyền thoại).' % (self.rom.species_name(sp), lv, where))
        self.alert('🐉 HUYỀN THOẠI MỚI: %s Lv %d' % (self.rom.species_name(sp), lv),
                   'Đang ở %s · bấm đúp trong tab Huyền thoại để bay tới' % where, types.SimpleNamespace(species=sp), shiny=False,
                   sticky=True)                              # lúc thả có thể không nhìn màn hình -> giữ tới khi bấm
        self.q_rsig = None                                   # vẽ lại tab Huyền thoại
        return None

    def roam_spawn_now(self):
        st = self.game.battle_state()
        if not st or not st[1] or st[0]:
            self.fly_refused('Chỉ thả được khi đang đi trên bản đồ (không trong trận, không mở menu).')
            return
        if len(self.roam_mine(self.game.roamers())) >= self.ROAM_MAX:
            self.fly_refused('Tool đã thả đủ %d con đang lang thang: bắt bớt rồi thả tiếp.' % self.ROAM_MAX)
            return
        why = self.roam_spawn()
        if why:
            self.fly_refused(why)

    def quest_pick_roamer(self):
        s = self.q_rtree.selection()
        x = next((x for x in self.q_roam if s and str(x['slot']) == s[0]), None)
        if x:
            # vẽ map chưa có sẵn mất lâu, chặn Tk -> lần bấm thứ 2 xử lý trễ, không thành bấm đúp (đo trong game 06/11)
            # -> đợi qua khoảng bấm đúp rồi mới mở map
            if getattr(self, '_q_rjob', None):
                self.after_cancel(self._q_rjob)
            self._q_rjob = self.after(350, lambda gn=x['map']: (setattr(self, '_q_rjob', None),
                                                               self.guard(self.quest_open)(gn)))

    # ---------------------------------------------------------------- săn tự động (bấm phím qua mm_bridge.lua)
    HUNT_DIRS = {(1, 0): 'RIGHT', (-1, 0): 'LEFT', (0, -1): 'UP', (0, 1): 'DOWN'}
    HUNT_FACE = dict(DOWN=1, UP=2, LEFT=3, RIGHT=4)          # hướng nhìn của người chơi (object +0x18 & 0xF)

    def hunt_toggle(self):
        if self.hunt:
            self.hunt_stop('Đã dừng săn.')
            return
        g = self.game
        try:
            g.keys_left()
        except BridgeError as e:
            if 'ERR' in str(e):
                raise BridgeError('mm_bridge.lua đang chạy là bản cũ, chưa bấm phím được: trong mGBA mở Tools > '
                                  'Scripting > File > Load script, chọn lại tool\\mm_bridge.lua.')
            raise
        inb, ow = g.battle_state()
        if inb:                                               # Duy 07/11: đang trận hoang dã (vd mở lại tool giữa trận)
            foes = [m for m in g.enemy_party() if not m.empty and m.checksum_ok and m.hp > 0]
            if not foes or foes[0].otid != g.player_otid():   # thì săn luôn: nhịp đầu tự xét bắt / chạy
                return self.hunt_refused('Đang đánh trainer: đánh xong trận rồi bấm Săn.')
        elif not ow or g.b.read(self.prof.fly['lock'], 1)[0]:
            return self.hunt_refused('Chỉ bắt đầu săn được khi đang đi trên bản đồ hoặc đang trong trận với Pokémon '
                                     'hoang dã (không mở menu, không nói chuyện).')
        gn, pos = g.current_map(), g.player_xy()
        tiles = self.story.encounter_tiles(*gn)
        kind = tiles.get(pos)
        face = g.player_look()[1]
        front = tuple(a + b for a, b in zip(pos, self.HUNT_STEP.get(face, (0, 0))))
        rod = None
        if kind != 'water' and tiles.get(front) == 'water':     # đứng trên bờ quay mặt ra nước -> câu cá
            rod = self.hunt_rod(gn)
            if isinstance(rod, str):
                return self.hunt_refused(rod)
            kind = 'fish'
        if not kind:
            return self.hunt_refused('Ô bạn đang đứng không có Pokémon hoang dã. Đứng vào ô cỏ (viền vàng trên bản đồ), '
                                     'lướt trên nước (viền xanh), hoặc đứng trên bờ quay mặt ra nước để câu cá rồi bấm lại.')
        if not self.hunt_target and not any(v.get() for v in self.hunt_opt.values()):
            return self.hunt_refused('Chưa tick loại nào để bắt (nút "Bắt gì" cạnh nút Săn): tool sẽ chỉ chạy trốn mãi.')
        if self.hunt_target and not any(x[0] == gn and x[1] == kind for x in self.species_locations(self.hunt_target)):
            name = self.rom.species_name(self.hunt_target)
            if not messagebox.askyesno('Không có %s ở đây' % name,
                                       '%s không xuất hiện ở %s (%s). Vẫn săn ở đây? (chỉ bắt các mục đã tick ở "Bắt gì")\n\n'
                                       'Xem chỗ có %s: nút "%s" → 🎯 Săn theo loài…' % (
                                           name, self.rom.map_name(*gn), 'cỏ' if kind == 'land' else 'nước', name,
                                           self.hunt_mb_text()), parent=self):
                return
        self.hunt = dict(map=gn, kind=kind, a=pos, b=None, bad=set(), last=None, stuck=0, n=0, steps=0,
                         foe=None, runs=0, lock_t=None, catch=None)
        if kind == 'fish':
            try:
                g.set_auto_fish(True)                         # Lua bấm A lúc cá cắn (kịp cả khi fast forward)
            except BridgeError as e:
                self.hunt = None
                if 'ERR' in str(e):
                    return self.hunt_refused('mm_bridge.lua đang chạy là bản cũ, chưa tự bấm A khi cá cắn được: trong '
                                             'mGBA mở Tools > Scripting > File > Load script, chọn lại tool\\mm_bridge.lua.')
                raise
            self.hunt.update(rod=rod, face=face, reg0=g.registered_item(), fish_t=None, fish_st=None)
            g.set_registered_item(rod)                        # SELECT = quăng cần; dừng săn thì trả lại món cũ
        elif not self.hunt_pick_b(pos):
            self.hunt = None
            return self.hunt_refused('Quanh ô này không có ô cỏ/nước nào khác để đi qua lại.')
        self.q_hunt.config(text='⏹ Dừng săn')
        lab = dict(shiny='shiny', iv='IV ≥ %d%%' % self.hunt_iv_pct, dex='chưa có dex', legend='huyền thoại')
        what = [t for k, t in lab.items() if self.hunt_opt[k].get()]
        if self.hunt_target:
            what.insert(0, ('%s shiny' if self.hunt_target_shiny.get() else '%s') % self.rom.species_name(self.hunt_target))
        self.say('%s ở %s… (bắt: %s)%s' % (
            '🎣 Bắt đầu câu bằng %s' % self.rom.item_name(rod) if kind == 'fish' else '🌿 Bắt đầu săn',
            self.rom.map_name(*gn), ', '.join(what), ' 🔇' if self.hunt_mute.get() else ''))
        self.hunt_sound(False)
        self.after(100, self.hunt_tick)

    def hunt_refused(self, why):
        self.say('Không săn được: ' + why.split('\n')[0], False)
        messagebox.showwarning('Không săn được', why, parent=self)

    def hunt_pick_b(self, a):
        """Chọn ô kề a cùng kiểu gặp để đi qua lại (ưu tiên ngang), bỏ ô đã thử không đi được."""
        h = self.hunt
        tiles = self.story.encounter_tiles(*h['map'])
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b = (a[0] + d[0], a[1] + d[1])
            if tiles.get(b) == h['kind'] and b not in h['bad']:
                h['a'], h['b'], h['stuck'] = a, b, 0
                return True
        return False

    def hunt_sound(self, on):
        """Bật (on) / tắt tiếng mGBA trong bộ trộn Windows. Chỉ tắt khi ô 🔇 đang tick; chỉ bật lại nếu chính tool đã tắt
        (bạn tự tắt tiếng mGBA thì tool không đụng). Lỗi âm thanh không làm dừng săn."""
        if on and not self.muted_by_tool or not on and (self.muted_by_tool or not self.hunt_mute.get()):
            return
        try:
            import mm_audio
            n = mm_audio.set_mute(not on)
        except Exception:
            self.log_tick_error()
            return
        if n:
            self.muted_by_tool = not on
            self.save_area_state()

    def on_close(self):
        self.hunt_sound(True)
        self.destroy()

    def hunt_stop(self, msg, ok=True):
        h, self.hunt = self.hunt, None
        if h and h.get('kind') == 'fish':                     # trả lại món đăng ký SELECT của bạn
            try:
                self.game.set_auto_fish(False)
            except BridgeError:
                pass
            try:
                self.game.set_registered_item(h['reg0'])
            except BridgeError:
                msg += ' (chưa trả lại được món đăng ký SELECT: tự đăng ký lại trong Túi)'
        self.hunt_sound(True)
        self.q_hunt.config(text='🌿 Săn')
        self.say(msg, ok)

    def hunt_tick(self):
        if not self.hunt:
            return
        try:
            self.hunt_step()
            if self.hunt:
                self.hunt['berr'] = 0
        except BridgeError as e:
            if not self.hunt:
                return
            self.hunt['berr'] = self.hunt.get('berr', 0) + 1  # bridge bận một nhịp: thử lại, 5 lần liền mới dừng
            if self.hunt['berr'] >= 5:
                self.hunt_stop('Dừng săn: %s' % e, False)
        except Exception:
            self.log_tick_error()
            self.hunt_stop('Dừng săn: lỗi lạ (xem tick_error.log).', False)
        if self.hunt:
            self.after(120, self.hunt_tick)

    def hunt_step(self):
        h, g = self.hunt, self.game
        if g.keys_left() > 0:                                 # Lua còn đang bấm chuỗi phím trước
            return
        inb, ow = g.battle_state()
        if inb:
            mons = [m for m in g.enemy_party() if not m.empty and m.checksum_ok and 1 <= m.species <= self.rom.max_species]
            m = next((m for m in mons if m.hp > 0), None)
            if not m:
                return
            if h['foe'] != m.pid:                             # đối thủ mới: xét có bắt không
                h['foe'], h['runs'], h['steps'], h['catch'] = m.pid, 0, 0, None
                name = '%s Lv %d' % (self.rom.species_name(m.species), m.level)
                self.refresh_foe()                            # ghi Lịch sử + báo shiny / nên bắt ngay
                if m.otid != g.player_otid():
                    return self.hunt_stop('🌿 Dừng săn sau %d trận: gặp trainer (%s), bạn tự đánh nhé.' % (h['n'], name))
                h['n'] += 1
                self.q_hunt.config(text='⏹ Dừng săn (%d)' % h['n'])
                alive = [x for x in mons if x.hp > 0]
                if len(alive) > 1 and g.b.read(self.prof.battle_type, 1)[0] & 1:     # trận đôi hoang dã (CFRU)
                    wants = [(x, self.hunt_want(x)) for x in alive]
                    wants = [(x, w) for x, w in wants if w]
                    if wants:                                 # 2 đối thủ thì không ném bóng được, phải chọn mục tiêu
                        x, w = wants[0]
                        nm = '%s Lv %d' % (self.rom.species_name(x.species), x.level)
                        self.alert('%s: %s' % (w, nm), 'Trận đôi, tool không tự bắt được, bạn tự bắt nhé', x,
                                   shiny=x.is_shiny_in_game(), sticky=True)
                        return self.hunt_stop('🌿 Dừng săn: %s %s trong trận đôi, bạn tự bắt nhé.' % (w, nm), False)
                    why = None
                else:
                    why = self.hunt_want(m)
                if why:
                    plan = self.hunt_plan(m, why, name)
                    if isinstance(plan, str):
                        return self.hunt_stop('🌿 Dừng săn: %s' % plan, False)
                    h['catch'] = plan
                    self.hunt_sound(True)                     # gặp con sẽ bắt: bật tiếng lại
                    self.say('🎯 %s → bắt bằng %s%s' % (why, self.rom.item_name(plan['ball']),
                                                        ' (False Swipe trước)' if plan['swipe'] else ''))
            hp, mx = g.battle_lead_hp()
            if 0 < hp < mx * self.HUNT_HEAL_BELOW:            # Duy 07/11: Aggron gục vì chạy hụt mãi trước Slaking
                g.heal_battle_lead()
                self.say('💊 Con đầu đội còn %d/%d HP → hồi đầy (đang săn).' % (hp, mx))
            lead = next((p for p in g.party() if not p.empty), None)
            if lead is not None and lead.hp == 0 or mx and hp == 0:
                self.alert('Con đầu đội đã gục', 'Săn đã dừng: chọn con khác / chạy trong game rồi bấm Săn lại', None,
                           False, sticky=True)
                return self.hunt_stop('Dừng săn: con đầu đội đã gục.', False)
            if h['catch']:
                return self.hunt_catch(m)
            if g.battle_ui() != 'action':                     # chữ / menu con: B cho qua, chưa chọn gì
                g.press([('B', 4), (None, 10)])
                return
            h['runs'] += 1
            if h['runs'] > 30:
                return self.hunt_stop('Dừng săn: chạy mãi không thoát được.', False)
            # góc dưới phải = "Chạy", A.
            g.press([('RIGHT', 3), (None, 4), ('DOWN', 3), (None, 4), ('A', 3), (None, 30)])
            return
        if not ow:
            return                                            # đang chuyển cảnh / màn hết trận
        if h['catch']:
            c, h['catch'] = h['catch'], None
            self.hunt_done(c)
        if h.get('save'):
            return self.hunt_save_step()
        if h['kind'] == 'fish':
            return self.hunt_fish_step()
        if g.b.read(self.prof.fly['lock'], 1)[0]:             # có hội thoại / sự kiện
            h['lock_t'] = h['lock_t'] or time.time()
            if time.time() - h['lock_t'] > 8:
                return self.hunt_stop('Dừng săn: game đang có hội thoại / sự kiện.', False)
            g.press([('B', 3), (None, 10)])
            return
        h['lock_t'] = None
        gn, pos = g.current_map(), g.player_xy()
        if gn != h['map']:
            return self.hunt_stop('Dừng săn: đã sang map khác.')
        if pos not in (h['a'], h['b']):
            if self.story.encounter_tiles(*gn).get(pos) != h['kind'] or not self.hunt_pick_b(pos):
                return self.hunt_stop('Dừng săn: đã ra khỏi vùng cỏ / nước.')
        if pos == h['last']:                                  # bấm mà không đi được (vướng)
            h['stuck'] += 1
            if h['stuck'] >= 3:
                h['bad'].add(h['b'] if pos == h['a'] else h['a'])
                if not self.hunt_pick_b(pos):
                    return self.hunt_stop('Dừng săn: không đi qua lại được ở chỗ này.', False)
        else:
            h['stuck'] = 0
        h['steps'] += 1
        if h['steps'] > 400:
            return self.hunt_stop('Dừng săn: đi 400 bước không gặp con nào (đang dùng Repel?).', False)
        tgt = h['b'] if pos == h['a'] else h['a']
        key = self.HUNT_DIRS[(tgt[0] - pos[0], tgt[1] - pos[1])]
        h['last'] = pos
        # đo 06/11: giữ 8 khung = quay (nếu chưa đúng hướng) HOẶC đi đúng 1 ô; giữ 18 khung khi đã đúng hướng
        # có lúc đi 2 ô -> lố ra khỏi cỏ
        tap = [(key, 8), (None, 6)]
        g.press(tap if g.player_look()[1] == self.HUNT_FACE[key] else tap + tap)

    # ---------------------------------------------------------------- câu cá (FireRed, 09/11)
    HUNT_STEP = {1: (0, 1), 2: (0, -1), 3: (-1, 0), 4: (1, 0)}   # hướng nhìn -> ô phía trước
    ROD_LABEL = {262: 'Cần câu cũ', 263: 'Cần câu tốt', 264: 'Cần câu siêu'}
    HUNT_MAX_CASTS = 300

    def hunt_rod(self, gn):
        """Cần sẽ dùng ở map gn: đang săn theo loài thì cần câu được loài đó (tốt nhất), không thì cần tốt nhất.
        Trả về chuỗi lý do nếu không câu được."""
        if 'fish' not in (self.rom.wild_for_map(*gn) or {}):
            return 'Map này không có Pokémon câu được.'
        have = self.game.rods()
        if not have:
            return 'Bạn chưa có cần câu (Old Rod ở Dewford, Good Rod ở Route 118, Super Rod ở Mossdeep).'
        if self.hunt_target:
            labels = {x[2] for x in self.species_locations(self.hunt_target) if x[0] == gn and x[1] == 'fish'}
            ok = [r for r in have if self.ROD_LABEL[r] in labels]
            if labels and not ok:
                return 'Ở đây %s chỉ câu được bằng %s, bạn chưa có cần đó.' % (
                    self.rom.species_name(self.hunt_target), ' / '.join(sorted(labels)))
            if ok:
                return ok[-1]
        return have[-1]

    def hunt_fish_step(self):
        """Một nhịp câu: không đang câu -> SELECT quăng cần; đang câu -> bấm A khi có thông báo (bước >= 9).
        Lúc cá cắn (fishing['press_a'], Emerald 6-7, chỉ ~30 khung) thì mm_bridge.lua tự bấm (set_auto_fish), Python
        không bấm thêm: A đến trễ rơi vào lúc đang hiện dấu chấm (vòng sau) là hỏng lượt."""
        h, g = self.hunt, self.game
        st, now = g.fishing_step(), time.time()
        if st != h['fish_st'] or now - h.get('fish_seen', 0) > 2:   # đổi bước, hoặc vừa đánh trận xong
            h['fish_st'], h['fish_t'] = st, now
        elif now - h['fish_t'] > 20:
            return self.hunt_stop('Dừng câu: %s.' % ('bấm SELECT mà không quăng được cần (ô phía trước không câu được?)'
                                                    if st is None else 'game đứng yên ở bước câu %d quá 20 giây' % st), False)
        h['fish_seen'] = now
        if st is not None:
            if st >= 9 and st not in self.prof.fishing['press_a']:                                     # đo 11/11: "on the hook!" đứng ở bước 10 chờ A rồi mới vào trận
                g.press([('A', 3), (None, 20)])
            return
        if g.b.read(self.prof.fly['lock'], 1)[0]:             # chữ khác (vd cần chưa đăng ký) / sự kiện
            g.press([('B', 3), (None, 15)])
            return
        if g.current_map() != h['map'] or g.player_xy() != h['a']:
            return self.hunt_stop('Dừng câu: bạn đã đi chỗ khác.')
        if g.player_look()[1] != h['face']:                   # bị quay mặt (vd sau trận): quay lại phía nước
            key = {v: k for k, v in self.HUNT_FACE.items()}[h['face']]
            g.press([(key, 2), (None, 8)])
            return
        if g.registered_item() != h['rod']:
            g.set_registered_item(h['rod'])
        h['steps'] += 1
        if h['steps'] > self.HUNT_MAX_CASTS:
            return self.hunt_stop('Dừng câu: quăng %d lần chưa gặp con nào.' % self.HUNT_MAX_CASTS, False)
        g.press([('SELECT', 3), (None, 30)])

    # ---------------------------------------------------------------- săn → tự bắt (Duy chốt 06/11 22:40)
    HUNT_MASTER_BELOW = 0.10     # "% bắt" lúc gặp (Poké Ball, HP hiện tại, như cột Lịch sử) dưới mức này → Master Ball
    HUNT_HEAL_BELOW = 0.5            # đang săn: con đầu đội trong trận dưới mức HP này -> hồi đầy ngay
    HUNT_MAX_THROWS = 20        # ném chừng này Ultra Ball chưa được → đổi sang Master Ball (Duy 07/11: không để treo)
    FALSE_SWIPE = 206
    TELEPORT = 100                   # hoang dã dùng là bỏ chạy ngay (Abra) -> không False Swipe
    # vị trí ô chiêu trong khung Đánh: 0 trên-trái, 1 trên-phải, 2 dưới-trái, 3 dưới-phải
    MOVE_KEYS = [('UP', 'LEFT'), ('UP', 'RIGHT'), ('DOWN', 'LEFT'), ('DOWN', 'RIGHT')]

    def hunt_want(self, m):
        """Lý do bắt con hoang dã này theo các ô đã tick ở nút Săn ▾, None = bỏ chạy."""
        r, o = self.rom, {k: v.get() for k, v in self.hunt_opt.items()}
        legends = self.__dict__.setdefault('_legend_set', set(legend_species(r)))
        if o['shiny'] and m.is_shiny_in_game():
            return '★ SHINY'
        if o['legend'] and m.species in legends:
            return '🐉 HUYỀN THOẠI'
        # Duy 07/11: mọi ô đã tick đều áp dụng, kể cả khi săn theo loài; săn theo loài chỉ là thêm một điều kiện bắt
        dex = r.natdex(m.species)
        if o['dex'] and dex and dex not in (self.game.caught_dex() or set()):
            return '📕 chưa có trong Pokédex'
        if o['iv']:
            pct = 100 * iv_grade(m.iv, r.base_stats(m.species))[1] / 155
            if pct >= self.hunt_iv_pct:
                return '✔ IV %d%%' % pct
        if self.hunt_target and m.species == self.hunt_target and \
                (not self.hunt_target_shiny.get() or m.is_shiny_in_game()):
            return '🎯 %s%s' % ('★ ' if m.is_shiny_in_game() else '', r.species_name(m.species))
        return None

    def hunt_menu_build(self):
        """Menu của nút Săn ▾ (dựng lại khi đổi mức IV để chữ hiện đúng %)."""
        mn, o = self.q_hunt_menu, self.hunt_opt
        mn.delete(0, 'end')
        save = self.save_area_state
        mn.add_checkbutton(label='★ Shiny', variable=o['shiny'], command=save)
        mn.add_checkbutton(label='✔ IV có ích ≥ %d%%' % self.hunt_iv_pct, variable=o['iv'], command=save)
        mn.add_checkbutton(label='📕 Loài chưa có trong Pokédex', variable=o['dex'], command=save)
        mn.add_checkbutton(label='🐉 Huyền thoại', variable=o['legend'], command=save)
        mn.add_separator()
        mn.add_command(label='Đổi mức IV… (đang %d%%)' % self.hunt_iv_pct, command=self.guard(self.hunt_set_iv))
        mn.add_command(label='Chỉ săn shiny', command=lambda: self.hunt_only('shiny'))
        mn.add_checkbutton(label='🔇 Tắt tiếng game khi săn (bật lại khi gặp con sẽ bắt)', variable=self.hunt_mute,
                           command=lambda: (self.save_area_state(), self.hunt and self.hunt_sound(not self.hunt_mute.get())))
        mn.add_separator()
        t = self.hunt_target
        mn.add_command(label='🎯 Săn theo loài…' + (' (đang: %s)' % self.rom.species_name(t) if t else ''),
                       command=self.guard(self.hunt_target_dialog))
        if t:
            mn.add_checkbutton(label='   ★ Chỉ bắt %s khi là shiny' % self.rom.species_name(t),
                               variable=self.hunt_target_shiny, command=self.hunt_target_changed)
            mn.add_command(label='✕ Bỏ săn theo loài (%s)' % self.rom.species_name(t),
                           command=lambda: self.hunt_set_target(None))

    def hunt_set_target(self, sp):
        self.hunt_target = sp
        self.save_area_state()
        self.hunt_menu_build()
        self.q_hunt_mb.config(text=self.hunt_mb_text())
        if sp:
            self.say('🎯 Săn theo loài: %s (vẫn bắt các mục đã tick ở "Bắt gì"). Vào cỏ có loài này rồi bấm 🌿 Săn.'
                     % self.rom.species_name(sp))
        else:
            self.say('Đã bỏ săn theo loài, săn lại theo các ô tick.')

    def hunt_target_changed(self):
        self.save_area_state()
        self.q_hunt_mb.config(text=self.hunt_mb_text())

    def hunt_mb_text(self):
        if not self.hunt_target:
            return 'Bắt gì'
        return '🎯 %s%s' % ('★ ' if self.hunt_target_shiny.get() else '', self.rom.species_name(self.hunt_target))

    HUNT_OK = ('land', 'water', 'fish')                       # kiểu gặp mà săn tự động làm được (đập đá thì chưa)

    def species_locations(self, sp):
        """[(map, kiểu, nhãn, %, lv thấp, lv cao)] mọi chỗ gặp hoang dã loài sp (đã đổi theo Randomizer); kiểu săn được
        và % cao lên trước. Chỉ mục cả game dựng một lần cho mỗi TID."""
        try:
            tid = self.game.rand_tid()
        except Exception:
            tid = None
        idx = self.__dict__.get('_sp_loc')
        if not idx or idx[0] != tid:
            table = {}
            for gn in self.story.maps():
                try:
                    wild = self.rom.wild_for_map(*gn)
                except Exception:
                    continue
                for key, label, _, rows in self.wild_groups(wild or {}, None, tid):
                    for s2, lo, hi, pct, _ in rows:
                        table.setdefault(s2, []).append((gn, key, label, pct, lo, hi))
            idx = self._sp_loc = (tid, table)
        return sorted(idx[1].get(sp, []), key=lambda x: (x[1] not in self.HUNT_OK, -x[3]))

    def wild_species(self):
        """Tập loài gặp được ngoài hoang dã (theo Randomizer hiện tại), dùng chung chỉ mục của species_locations."""
        self.species_locations(1)
        return {s for s in self._sp_loc[1] if 1 <= s <= self.rom.max_species}

    def nearest_fly(self, gn):
        """(số map phải đi, (nhóm, số, x, y)) điểm bay gần map gn nhất, tính theo mép map + cửa/hang; None nếu không có."""
        pts = {(g, n): (g, n, x, y) for g, n, x, y in self.game.fly_points()}
        seen, q = {gn: 0}, [gn]
        while q:
            cur = q.pop(0)
            if cur in pts:
                return seen[cur], pts[cur]
            if seen[cur] >= 12:
                continue
            try:
                info = self.story.map_info(*cur)
            except Exception:
                continue
            for nxt in [c['to'] for c in info['connections']] + [w['to'] for w in info['warps']]:
                if nxt not in seen:
                    seen[nxt] = seen[cur] + 1
                    q.append(nxt)
        return None

    def route_set(self, goal):
        self.hunt_goal = tuple(goal) if goal else None
        self.save_area_state()

    def route_path(self, cur, goal):
        """[map...] đường ngắn nhất từ cur tới goal (đi qua mép map + cửa/hang/cầu thang), None nếu không có (≤ 16 map)."""
        cache = self.__dict__.setdefault('_route_cache', {})
        if (cur, goal) in cache:
            return cache[(cur, goal)]
        prev, q = {cur: None}, [cur]
        while q:
            m = q.pop(0)
            if m == goal:
                break
            try:
                info = self.story.map_info(*m)
            except Exception:
                continue
            for nxt in [c['to'] for c in info['connections']] + [w['to'] for w in info['warps']]:
                if nxt not in prev:
                    prev[nxt] = m
                    q.append(nxt)
        path = None
        if goal in prev:
            path, m = [], goal
            while m is not None:
                path.append(m)
                m = prev[m]
            path.reverse()
            if len(path) > 16:
                path = None
        cache[(cur, goal)] = path
        return path

    def route_steps(self, path):
        """[(map, map kế, hướng mép map hoặc None, [ô cửa])] cho từng chặng của path."""
        out = []
        for m, nxt in zip(path, path[1:]):
            info = self.story.map_info(*m)
            edge = next((c['dir'] for c in info['connections'] if c['to'] == nxt), None)
            tiles = [(w['x'], w['y']) for w in info['warps'] if w['to'] == nxt]
            out.append((m, nxt, edge, tiles))
        return out

    def route_name(self, m, prev=None):
        nm = self.rom.map_name(*m)
        return nm + (' (trong nhà)' if prev and self.rom.map_name(*prev) == nm else '')

    @staticmethod
    def route_how(edge, tiles):
        if tiles:
            return 'vào cửa ô ' + ' / '.join('%d,%d' % t for t in tiles[:3])
        way = {'Bắc': 'lên trên', 'Nam': 'xuống dưới', 'Tây': 'sang trái', 'Đông': 'sang phải'}.get(edge)
        return ('đi ra mép %s (%s)' % (edge, way) if way else 'đi ra mép %s' % edge) if edge else 'đi sang'

    def route_text(self, path):
        """'PEWTER CITY → (đi ra mép Nam) → ROUTE 2 → …' (một dòng, cho thanh trạng thái)."""
        parts = [self.route_name(path[0])]
        for m, nxt, edge, tiles in self.route_steps(path):
            parts.append('(%s)' % self.route_how(edge, tiles))
            parts.append(self.route_name(nxt, m))
        return ' → '.join(parts)

    def route_render_text(self, T):
        """Mục 🧭 ĐƯỜNG TỚI … ở đầu danh sách bên trái; chặng của map đang xem in đậm."""
        if not self.hunt_goal or not self.q_cur:
            return None
        path = self.route_path(self.q_cur, self.hunt_goal)
        goal = self.rom.map_name(*self.hunt_goal)
        T.insert('end', '🧭 ĐƯỜNG TỚI %s%s  ' % (goal, ' (săn %s)' % self.rom.species_name(self.hunt_target)
                                                  if self.hunt_target else ''), 'head')
        T.insert('end', '✕ bỏ chỉ đường\n', ('route_x', 'rx'))
        T.tag_bind('rx', '<Button-1>', lambda e: (self.route_set(None), self.guard(self.quest_render)()))
        if not path:
            T.insert('end', '• Không tìm được đường từ map này (có thể phải bay, hoặc cần Surf / sự kiện mở đường).\n',
                     'route')
            return None
        for i, (m, nxt, edge, tiles) in enumerate(self.route_steps(path)):
            now = m == self.q_shown
            T.insert('end', '%s%d. %s: %s → %s\n' % ('➜ ' if now else '    ', i + 1,
                                                    self.route_name(m, path[i - 1] if i else None),
                                                    self.route_how(edge, tiles), self.route_name(nxt, m)),
                     'route_now' if now else 'route')
        T.insert('end', 'Khung / dải tím trên bản đồ = chỗ cần đi tới. Tới nơi thì tự tắt.\n', 'hint')
        return path

    def route_draw(self, path):
        """Khung tím trên ô cửa / dải tím ở mép map cần đi ra, cho chặng của map đang xem."""
        cv, k = self.q_cv, self.q_scale * 16
        cv.delete('route')
        if not path:
            return
        step = next((x for x in self.route_steps(path) if x[0] == self.q_shown), None)
        if not step:
            return
        m, nxt, edge, tiles = step
        info = self.story.map_info(*m)
        W, H = info['w'] * k, info['h'] * k
        label = '➜ ' + self.route_name(nxt, m)
        spots = []
        for x, y in tiles:
            cv.create_rectangle(x * k - 3, y * k - 3, x * k + k + 3, y * k + k + 3, outline='#d500f9', width=4, tags='route')
            spots.append((x * k + k // 2, y * k - 6, 's'))
        if not tiles and edge in ('Bắc', 'Nam', 'Tây', 'Đông'):
            band = {'Bắc': (0, 0, W, 10), 'Nam': (0, H - 10, W, H), 'Tây': (0, 0, 10, H), 'Đông': (W - 10, 0, W, H)}[edge]
            cv.create_rectangle(*band, fill='#d500f9', outline='', stipple='gray50', tags='route')
            px, py = W // 2, H // 2                           # nhãn đặt ngay hướng nhân vật (giữa mép dễ bị khuất)
            if self.q_shown == self.q_cur:
                try:
                    x, y = self.game.player_xy()
                    px, py = min(max(x * k + k // 2, 70), W - 70), min(max(y * k + k // 2, 20), H - 20)
                except BridgeError:
                    pass
            spots.append({'Bắc': (px, 14, 'n'), 'Nam': (px, H - 14, 's'),
                          'Tây': (14, py, 'w'), 'Đông': (W - 14, py, 'e')}[edge])
        for x, y, anc in spots[:3]:
            t = cv.create_text(x, y, text=label, anchor=anc, fill='white', font=('Segoe UI', 9, 'bold'), tags='route')
            bg = cv.create_rectangle(*[a + b for a, b in zip(cv.bbox(t), (-3, -1, 3, 1))], fill='#8e24aa',
                                     outline='white', tags='route')
            cv.tag_lower(bg, t)

    def species_icon(self, v, size=40, shiny=False):
        """Hình nhỏ của loài (v = "25 - Pikachu" hoặc số loài) cho danh sách chọn loài; cắt viền trong suốt."""
        try:
            sp = int(str(v).split(' - ')[0])
        except ValueError:
            return None
        cache = self.__dict__.setdefault('_sp_icons', {})
        key = (sp, size, shiny)
        if key not in cache:
            im = self.rom.sprite(sp, shiny) if 1 <= sp <= self.rom.max_species else None
            if im is not None:
                from PIL import Image, ImageTk
                box = im.getbbox()
                if box:
                    im = im.crop(box)
                k = min(size / im.width, size / im.height, 2)
                im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.NEAREST)
                bg = Image.new('RGBA', (size, size))
                bg.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
                im = ImageTk.PhotoImage(bg)
            cache[key] = im
        return cache[key]

    def hunt_target_dialog(self):
        """Cửa sổ "Săn theo loài": gõ tên loài -> nơi gặp; chọn loài để săn, mở map, bay tới điểm gần nhất."""
        w = getattr(self, '_tgt_win', None)
        if w and w.winfo_exists():
            w.lift()
            return
        w = self._tgt_win = tk.Toplevel(self)
        w.title('🎯 Săn theo loài')
        w.geometry('640x420')
        w.transient(self)
        top = ttk.Frame(w, padding=6)
        top.pack(fill='x')
        ttk.Label(top, text='Loài:').pack(side='left')
        wild = self.wild_species()
        wild_vals = [v for v in self.species_vals if int(v.split(' - ')[0]) in wild]
        cb = SearchCombo(top, wild_vals, icon=self.species_icon)
        cb.pack(side='left', fill='x', expand=True, padx=4)
        pic = ttk.Label(top)                                  # hình loài đang chọn
        pic.pack(side='right')
        show_all = tk.BooleanVar(value=False)

        def toggle_all():
            vals = self.species_vals if show_all.get() else wild_vals
            cb.all = list(vals)
            cb.configure(values=vals)
        b = ttk.Checkbutton(top, text='Cả loài không gặp hoang dã', variable=show_all, command=toggle_all)
        b.pack(side='right', padx=6)
        Tip(b, 'Mặc định chỉ hiện %d loài gặp được ngoài hoang dã (đã tính Randomizer nếu bật). Tick để hiện cả %d loài: '
               'loài chỉ có qua tiến hoá / quà / sự kiện / trao đổi.' % (len(wild_vals), len(self.species_vals)))
        bot = ttk.Frame(w, padding=6)
        bot.pack(side='bottom', fill='x')
        info = ttk.Label(w, text='Gõ tên loài rồi chọn. Bấm đúp một dòng = mở map đó trên tab Bản đồ.', wraplength=620)
        info.pack(side='bottom', fill='x', padx=6, pady=3)
        tv = ttk.Treeview(w, columns=('m', 'k', 'p', 'lv'), show='headings', height=12)
        for c, t, wd in (('m', 'Map', 220), ('k', 'Cách gặp', 250), ('p', 'Tỉ lệ', 60), ('lv', 'Lv', 60)):
            tv.heading(c, text=t)
            tv.column(c, width=wd, anchor='w' if c in 'mk' else 'center')
        tv.tag_configure('no', foreground='#888')
        tv.pack(fill='both', expand=True, padx=6)
        st = dict(sp=None, rows=[], anc=[])

        def load(*_):
            try:
                sp = parse_id(cb.get(), self.species_vals)
            except ValueError:
                return
            if not 1 <= sp <= self.rom.max_species:
                return
            st['sp'], st['rows'] = sp, self.species_locations(sp)
            pic.config(image=self.species_icon(sp, 64) or '')
            tv.delete(*tv.get_children())
            for i, (gn, key, label, pct, lo, hi) in enumerate(st['rows']):
                ok = key in self.HUNT_OK
                tv.insert('', 'end', iid=str(i), tags=() if ok else ('no',),
                          values=(self.rom.map_name(*gn), label + ('' if ok else ' (săn tự động chưa làm được)'),
                                  '%d%%' % pct, '%d–%d' % (lo, hi) if lo != hi else str(lo)))
            name = self.rom.species_name(sp)
            st['anc'] = wild_ancestors(self.rom, sp, self.wild_species()) if not st['rows'] else []
            if st['anc']:
                a = st['anc'][0]
                b_anc.config(text='🎯 Săn %s thay' % self.rom.species_name(a))
                b_anc.pack(side='left', padx=(12, 0))
            else:
                b_anc.pack_forget()
            if st['anc']:
                info.config(text='%s không gặp hoang dã — tiến hoá từ %s (gặp ở %d chỗ). Bấm "Săn %s thay".' % (
                    name, ', '.join(self.rom.species_name(x) for x in st['anc']), len(self.species_locations(st['anc'][0])),
                    self.rom.species_name(st['anc'][0])))
            elif not st['rows']:
                info.config(text='Không có %s hoang dã ở map nào, cũng không tiến hoá từ loài hoang dã nào '
                                 '(chỉ có qua quà / sự kiện / hoá thạch / trao đổi).' % name)
            elif not any(x[1] in self.HUNT_OK for x in st['rows']):
                info.config(text='%s chỉ gặp bằng đập đá: săn tự động chưa làm được kiểu này.' % name)
            else:
                info.config(text='%s gặp ở %d chỗ. Chọn một dòng → "✈ Bay vào cỏ" → tới nơi bấm 🌿 Săn.' % (name, len(st['rows'])))
            if tv.get_children():
                tv.selection_set('0')

        def row():
            sel = tv.selection()
            return st['rows'][int(sel[0])] if sel else None

        def open_map():
            x = row()
            if x:
                self.quest_open(x[0])

        def fly():
            x = row()
            if not x:
                return
            gn, kind = x[0], x[1]
            spot = self.story.landing_tile(*gn, kind) if kind in self.HUNT_OK else None
            if spot:                                          # bay thẳng vào bãi cỏ / bờ nước (như săn huyền thoại)
                why = self.fly_tool(*gn, *spot)
                if why:
                    return self.fly_refused(why)
                self.route_set(None)
                self.q_follow.set(True)
                self.say('✈ Bay vào %s ô %d,%d. %s' % (
                    self.rom.map_name(*gn), spot[0], spot[1], 'Tới nơi bấm 🌿 Săn.' if kind == 'land' else
                    'Đáp xuống bờ: quay mặt ra nước rồi bấm 🌿 Săn (tool tự câu).' if kind == 'fish' else
                    'Đáp xuống bờ: dùng Surf ra nước rồi bấm 🌿 Săn.'))
                return
            near = self.nearest_fly(x[0])                     # không chọn được ô: bay tới điểm bay gần + chỉ đường
            if not near:
                return self.fly_refused('Không tìm được điểm bay nào gần %s. Mở map xem rồi tự đi nhé.'
                                        % self.rom.map_name(*x[0]))
            hops, (g, n, fx, fy) = near
            why = self.fly_tool(g, n, fx, fy)
            if why:
                return self.fly_refused(why)
            if hops:
                self.route_set(x[0])
                path = self.route_path((g, n), x[0])
                self.say('✈ Bay tới %s. Đường: %s' % (self.rom.map_name(g, n), self.route_text(path) if path else '?'))
            else:
                self.say('✈ Bay tới %s. Vào cỏ (viền vàng) rồi bấm 🌿 Săn.' % self.rom.map_name(g, n))
            self.q_follow.set(True)                           # tới nơi thì bản đồ tự theo, hiện chỉ đường

        def guide():
            x = row()
            if not x:
                return
            self.route_set(x[0])
            path = self.q_cur and self.route_path(self.q_cur, x[0])
            self.say('🧭 Chỉ đường tới %s: %s' % (self.rom.map_name(*x[0]), self.route_text(path) if path else
                                                  'chưa tìm được đường từ chỗ bạn đứng (thử ✈ Bay vào cỏ)'))
            if self.q_cur:
                self.quest_open(self.q_cur)

        def pick():
            if st['sp']:
                self.hunt_set_target(st['sp'])
                w.destroy()

        def hunt_anc():
            if st['anc']:
                a = st['anc'][0]
                cb.set('%d - %s' % (a, self.rom.species_name(a)))
                load()

        b_anc = ttk.Button(bot, text='', command=self.guard(hunt_anc))   # chỉ hiện khi loài cần tiến hoá từ loài khác
        cb.bind('<<ComboboxSelected>>', load, add='+')
        cb.bind('<Return>', load, add='+')
        tv.bind('<Double-1>', lambda e: self.guard(open_map)())
        ttk.Button(bot, text='🎯 Săn loài này', command=self.guard(pick)).pack(side='left')
        ttk.Button(bot, text='🗺 Mở map', command=self.guard(open_map)).pack(side='left', padx=4)
        b = ttk.Button(bot, text='✈ Bay vào cỏ', command=self.guard(fly))
        b.pack(side='left')
        Tip(b, 'Bay thẳng vào giữa bãi cỏ của map đã chọn (như bấm đúp huyền thoại lang thang). Kiểu lướt nước: đáp xuống '
               'bờ cạnh nước. Map không chọn được ô thì bay tới điểm bay gần nhất rồi chỉ đường.\n'
               'Bay vào được cả map không phải ngoài trời (rừng, hang) — lần đầu nên lưu game trước; có nút 🏠 Về chỗ cũ.')
        b = ttk.Button(bot, text='🧭 Chỉ đường', command=self.guard(guide))
        b.pack(side='left', padx=4)
        Tip(b, 'Không bay, chỉ hiện đường đi từ chỗ bạn đang đứng tới map này (đầu danh sách bên trái + khung tím '
               'trên bản đồ). Tới nơi thì tự tắt.')
        ttk.Button(bot, text='Đóng', command=w.destroy).pack(side='right')
        if self.hunt_target:
            cb.set('%d - %s' % (self.hunt_target, self.rom.species_name(self.hunt_target)))
            load()
        cb.focus_set()

    def hunt_only(self, key):
        for k, v in self.hunt_opt.items():
            v.set(k == key)
        self.save_area_state()

    # số lần gặp trung bình để có 1 con đạt mức IV có ích (5 IV ngẫu nhiên 0..31, đếm chính xác)
    @staticmethod
    def iv_odds(pct):
        need = -(-pct * 155 // 100)                      # tổng tối thiểu
        ways = [1] + [0] * 155
        for _ in range(5):
            ways = [sum(ways[t - v] for v in range(32) if t - v >= 0) for t in range(156)]
        p = sum(ways[need:]) / 32 ** 5
        return 1 / p if p else float('inf')

    def hunt_set_iv(self):
        from tkinter import simpledialog
        v = simpledialog.askinteger('Mức IV khi săn', 'Bắt con có IV có ích (5 chỉ số, bỏ Atk/SpA loài không dùng) từ bao '
                                    'nhiêu % trở lên? (50–100)', parent=self, minvalue=50, maxvalue=100,
                                    initialvalue=self.hunt_iv_pct)
        if v is None:
            return
        n = self.iv_odds(v)
        if n > 5000 and not messagebox.askyesno('Mức IV rất khó', 'IV có ích ≥ %d%%: trung bình khoảng %s lần gặp mới có '
                                                 '1 con. Vẫn đặt mức này?' % (v, '{:,}'.format(round(n)).replace(',', '.')),
                                                 parent=self):
            return
        self.hunt_iv_pct = v
        self.hunt_opt['iv'].set(True)
        self.save_area_state()
        self.hunt_menu_build()
        self.say('Săn: bắt con IV có ích ≥ %d%% (trung bình ~%s lần gặp có 1 con).' % (
            v, '{:,}'.format(round(n)).replace(',', '.')))

    def hunt_swipe_slot(self):
        for k, (mv, pp) in enumerate(self.game.lead_moves()):
            if mv == self.FALSE_SWIPE and pp > 0:
                return k
        return None

    def hunt_plan(self, m, why, name):
        """dict kế hoạch bắt, hoặc câu báo vì sao phải dừng."""
        r, g, p = self.rom, self.game, self.prof
        legend = m.species in self._legend_set
        low = catch_chance(r.catch_rate(m.species), m.hp, m.maxhp, m.status) < self.HUNT_MASTER_BELOW
        ball = p.master_ball if legend or low else p.ultra_ball
        swipe = ball == p.ultra_ball and 7 not in r.species_types(m.species)    # hệ Ma: False Swipe không trúng
        important = self.hunt_important(m)
        if self.TELEPORT in m.moves:                          # Abra...: Teleport ngay lượt 1 -> ném bóng luôn (08/11)
            swipe = False
            if important:
                ball = p.master_ball                          # không có lượt 2, con quan trọng thì chắc ăn
        if ball == p.ultra_ball and (self.hunt_balls(ball)[0] is None or (swipe and self.hunt_swipe_slot() is None)):
            ball, swipe = p.master_ball, False                # hết Ultra / không có False Swipe: Master Ball, không dừng
        idx, _, _ = self.hunt_balls(ball)
        if idx is None:
            self.alert('%s: %s' % (why, name), 'Hết %s, săn đã dừng, bạn tự bắt nhé' % r.item_name(ball), m,
                       shiny=m.is_shiny_in_game(), sticky=True)
            return 'gặp %s %s nhưng hết %s, bạn tự bắt nhé.' % (why, name, r.item_name(ball))
        return dict(ball=ball, swipe=swipe, why=why, name=name, pid=m.pid, stage=None, t=0, idx=None,
                    thrown=0, swipes=0, save=important)

    HUNT_REFILL_BELOW, HUNT_REFILL_TO = 10, 99

    def hunt_balls(self, ball):
        """ball_index, nhưng còn dưới HUNT_REFILL_BELOW quả thì tự nạp lên HUNT_REFILL_TO (Duy 07/11: không để hết bóng)."""
        g = self.game
        idx, n, q = g.ball_index(ball)
        if q < self.HUNT_REFILL_BELOW:
            try:
                g.set_item(ball, self.HUNT_REFILL_TO)
                self.say('🎒 Tự nạp %s: %d → %d.' % (self.rom.item_name(ball), q, self.HUNT_REFILL_TO))
            except BridgeError as e:                          # ngăn bóng đầy ô: giữ như cũ
                self.say('🎒 Không nạp được %s: %s' % (self.rom.item_name(ball), e), False)
            idx, n, q = g.ball_index(ball)
        return idx, n, q

    HUNT_SAVE_IV = 0.90              # IV có ích >= mức này (mức "Tuyệt vời") -> bắt xong tự lưu game

    def hunt_important(self, m):
        """Bắt xong con này thì tự lưu game (Duy 07/11 để Claude chọn): shiny, huyền thoại, IV có ích >= 90%,
        đúng loài đang săn theo loài. Con chỉ "chưa có dex" thì không (dễ gặp lại, lưu mỗi lần mất ~25 giây)."""
        r = self.rom
        if m.is_shiny_in_game() or m.species in self.__dict__.setdefault('_legend_set', set(legend_species(r))):
            return True
        if iv_grade(m.iv, r.base_stats(m.species))[1] / 155 >= self.HUNT_SAVE_IV:
            return True
        return bool(self.hunt_target) and m.species == self.hunt_target

    def hunt_catch_fail(self, m, msg):
        c = self.hunt['catch']
        self.alert('%s: %s' % (c['why'], c['name']), msg + ', bạn tự bắt nhé', m, shiny=m.is_shiny_in_game(),
                   sticky=True)
        self.hunt_stop('🌿 Dừng săn: %s %s — %s.' % (c['why'], c['name'], msg), False)

    def hunt_to_master(self, c, why):
        """Đổi kế hoạch sang Master Ball (ném ở nhịp tới); hết Master Ball thì nhịp tới tự dừng + báo."""
        c['ball'], c['swipe'], c['thrown'] = self.prof.master_ball, False, 0
        self.say('🎯 %s → đổi sang %s.' % (why, self.rom.item_name(c['ball'])))

    def hunt_catch(self, m):
        """Một nhịp bắt: chỉ bấm khi game đang chờ chọn lệnh; còn lại bấm B cho qua chữ."""
        g, c, p = self.game, self.hunt['catch'], self.prof
        ui = g.battle_ui()
        if ui == 'bag':
            if c['stage'] != 'bag':                           # túi mở mà không phải do mình: đóng lại
                g.press([('B', 3), (None, 30), ('B', 3), (None, 60)])
                return
            k, sel = g.bag_cursor()
            if k == p.ball_pocket and sel is not None and sel != c['idx'] and c.get('nudge', 0) < 30:
                # game có lúc mở túi ở món 0 dù đã ghi con trỏ (save mới 08/11, Master ở món 1): bấm lên/xuống tới đúng món
                c['nudge'] = c.get('nudge', 0) + 1
                g.press([('DOWN' if sel < c['idx'] else 'UP', 3), (None, 12)])
                return
            if k != p.ball_pocket or sel != c['idx']:
                g.press([('B', 3), (None, 30), ('B', 3), (None, 60)])
                return self.hunt_catch_fail(m, 'túi không mở đúng chỗ bóng (ngăn %s, món %s)' % (k, sel))
            g.press([('A', 3), (None, 20), ('A', 3), (None, 60)])   # chọn bóng → "Xài"
            c['stage'], c['thrown'] = 'thrown', c['thrown'] + 1
            return
        if c['stage'] == 'bag':                               # đang đợi túi mở
            if time.time() - c['t'] > 5:
                c['stage'] = None
            return
        if ui == 'move':
            g.press([('B', 3), (None, 20)])
            return
        if ui != 'action':
            g.press([('B', 3), (None, 10)])                  # chữ / "đặt biệt danh?" = Không / trang Pokédex
            return
        c['stage'] = None
        if c['ball'] != p.master_ball and c['thrown'] >= self.HUNT_MAX_THROWS:
            self.hunt_to_master(c, 'đã ném %d %s chưa bắt được' % (c['thrown'], self.rom.item_name(c['ball'])))
        if not c['swipe'] or m.hp <= 1:
            idx, n, _ = self.hunt_balls(c['ball'])
            if idx is None and c['ball'] != p.master_ball:
                return self.hunt_to_master(c, 'hết %s' % self.rom.item_name(c['ball']))
            if idx is None:
                return self.hunt_catch_fail(m, 'hết %s' % self.rom.item_name(c['ball']))
            g.set_bag_cursor(idx, n)
            c['idx'], c['stage'], c['t'], c['nudge'] = idx, 'bag', time.time(), 0
            g.press([('UP', 3), (None, 4), ('RIGHT', 3), (None, 4), ('A', 3), (None, 90)])   # Túi
            return
        slot = self.hunt_swipe_slot()
        if slot is None:                                      # hết PP: ném Master Ball luôn, không dừng chờ
            return self.hunt_to_master(c, 'False Swipe hết PP')
        c['swipes'] += 1                                      # không giới hạn lần (Duy 07/11)
        v, hz = self.MOVE_KEYS[slot]
        g.press([('UP', 3), (None, 4), ('LEFT', 3), (None, 4), ('A', 3), (None, 20),    # Đánh
                 (v, 3), (None, 4), (hz, 3), (None, 4), ('A', 3), (None, 60)])

    SAV_FILE = os.path.join(ROOT, 'Pokemon - Emerald Version (USA, Europe).sav')
    START_MENU_CURSOR = None         # Emerald: chưa dò (FR 0x020370F4) -> không tự lưu sau khi bắt
    START_MENU_SAVE = 4              # POKéDEX, POKéMON, Túi, <tên>, Lưu, CaiDat, Exit

    def _sav_mtime(self):
        try:
            return os.path.getmtime(self.SAV_FILE)
        except OSError:
            return None

    def hunt_save_step(self):
        """Lưu game bằng phím (Start → Lưu → YES → YES lưu đè), xong khi file .sav đổi; 40 giây không xong thì báo."""
        h, g = self.hunt, self.game
        sv, lock = h['save'], g.b.read(self.prof.fly['lock'], 1)[0]
        if sv['stage'] == 0:
            if lock:                                          # còn chữ sau trận: cho qua
                g.press([('B', 3), (None, 10)])
            else:
                g.press([('START', 3), (None, 40)])
                sv['stage'] = 1
        elif sv['stage'] == 1:
            if not lock:                                      # menu chưa mở: mở lại
                sv['stage'] = 0
                return
            cur = g.b.read(self.START_MENU_CURSOR, 1)[0]
            n = (self.START_MENU_SAVE - cur) % 7
            g.press([('DOWN', 3), (None, 12)] * n + [('A', 3), (None, 150)])
            sv['stage'], sv['a'] = 2, 0
        elif self._sav_mtime() != sv['mtime']:            # đã ghi file: đợi câu "đã lưu" tự đóng
            if not lock:
                h['save'] = None
                self.say('💾 Đã lưu game sau khi bắt %s. Săn tiếp…' % sv['name'])
                return
        elif lock and sv['a'] < 8:
            # Đo 07/11: bấm A dồn (60/90 khung) thì A rơi vào lúc chữ đang chạy -> câu "lưu đè?" không ai trả lời.
            # Bấm từng lần, cách 150 khung, tới khi file .sav đổi (câu hỏi lưu -> YES, lưu đè -> YES, rồi đang lưu).
            g.press([('A', 3), (None, 150)])
            sv['a'] += 1
        else:
            sv['t'] = 0                                       # menu đã đóng / bấm đủ 8 lần mà chưa lưu: báo ngay
        if time.time() - sv['t'] > 60:
            h['save'] = None
            g.press([('B', 3), (None, 20)] * 3)
            self.alert('💾 Chưa lưu được game', 'Bắt %s xong mà tự lưu không thành, bạn lưu tay nhé' % sv['name'],
                       None, False, sticky=True)
            self.hunt_stop('🌿 Dừng săn: tự lưu game sau khi bắt %s không thành, bạn lưu tay nhé.' % sv['name'], False)

    def hunt_done(self, c):
        """Hết trận có định bắt: báo đã bắt được hay chưa (tìm PID trong đội + kho)."""
        g = self.game
        got = any(not x.empty and x.pid == c['pid'] for x in g.party())
        if not got and getattr(self.prof, 'storage_ptr', None):
            _, box = g.read_box()
            sz = self.prof.box_size
            got = any(struct.unpack_from('<I', box, i)[0] == c['pid'] for i in range(0, len(box), sz))
        if got:
            self.hunt['caught'] = self.hunt.get('caught', 0) + 1
            self.say('✔ Đã bắt %s (%s) sau %d bóng. Săn tiếp…' % (c['name'], c['why'], c['thrown']))
            if c.get('save') and self.START_MENU_CURSOR:      # Duy 07/11: bắt con quan trọng xong lưu game ngay
                self.hunt['save'] = dict(stage=0, t=time.time(), mtime=self._sav_mtime(), name=c['name'])
            elif c.get('save'):                               # Emerald: chưa dò con trỏ menu Start -> nhắc lưu tay
                self.alert('💾 Nhớ lưu game', 'Vừa bắt %s (%s), tool chưa tự lưu được ở Emerald' % (c['name'], c['why']),
                           None, False, sticky=True)
        else:
            self.say('✘ Chưa bắt được %s (%s), trận đã hết. Săn tiếp…' % (c['name'], c['why']), False)
        self.hunt_sound(False)                                # săn tiếp: tắt tiếng lại

    def fly_refused(self, why):
        """Không bay: hiện hộp thoại (chữ trên thanh trạng thái nhỏ quá, dễ tưởng là không có gì xảy ra)."""
        self.say('Không bay được: ' + why.split('\n')[0], False)
        messagebox.showwarning('Không bay được', why, parent=self)

    def quest_fly(self):
        i = self.q_fly.current()
        self.q_fly.set('Bay tới…')
        self.q_fly.selection_clear()
        self.focus_set()
        if i < 0:
            return
        g, n, x, y = self.q_fly_pts[i]
        why = self.fly_tool(g, n, x, y)
        if why:
            self.fly_refused(why)
        else:
            self.say('✈ Đang bay tới %s…' % self.rom.map_name(g, n))
            self.q_follow.set(True)                           # tới nơi thì bản đồ tự theo

    def fly_tool(self, g, n, x, y):
        """Mọi lần bay bằng tool đi qua đây. Một "chuyến" = các lần bay nối nhau: đang đứng ở map tool vừa thả xuống
        (hoặc map kề nó qua mép map, vd đi tìm huyền thoại sang route bên) thì giữ chỗ cũ đầu chuyến; còn đã tự đi
        nơi khác (vào nhà, qua nhiều map...) thì chuyến cũ coi như xong -> nhớ chỗ đang đứng làm chỗ cũ mới
        (Duy 06/11: bay từ tháp Lavender phải về tháp Lavender, không về Route 10 của chuyến trước).
        Bay được cả từ trong nhà/hang (07/11) nên chỗ cũ có thể ở trong hang."""
        cur = self.game.current_map()
        here = (cur, self.game.player_xy())
        land = tuple(self.fly_landed) if self.fly_landed else None
        near = land is not None and (cur == land or any(
            c['to'] == cur for c in self.story.map_info(*land)['connections']))
        why = self.game.fly(g, n, x, y)
        if not why:
            if not (self.fly_origin and near):
                (og, on), (ox, oy) = here
                self.fly_origin = [og, on, ox, oy]
            self.fly_landed = [g, n]
            self.save_area_state()
            self.upd_home_btn()
        return why

    def fly_home(self):
        """Nút 🏠 Về chỗ cũ: bay về ô đứng ngay trước lần bay đầu tiên bằng tool, rồi quên chỗ đó."""
        if not self.fly_origin:
            self.fly_refused('Chưa có chỗ cũ: tool chỉ nhớ chỗ bạn đứng ngay trước lần bay đầu tiên bằng tool '
                             '(ô ✈ hoặc bấm đúp huyền thoại).')
            return
        g, n, x, y = self.fly_origin
        why = self.game.fly(g, n, x, y)
        if why:
            self.fly_refused(why)
            return
        self.fly_origin, self.fly_landed = None, None
        self.save_area_state()
        self.upd_home_btn()
        self.q_follow.set(True)
        self.say('🏠 Đang bay về chỗ cũ: %s (ô %d,%d)…' % (self.rom.map_name(g, n), x, y))

    def upd_home_btn(self):
        o = self.fly_origin
        self.q_home.config(text='🏠 Về chỗ cũ: %s' % self.rom.map_name(o[0], o[1]) if o else '🏠 Về chỗ cũ',
                           state='normal' if o else 'disabled')
        how = ('Bay về chỗ bạn đứng trước khi bắt đầu chuyến bay bằng tool. Bay tiếp từ chỗ tool vừa thả xuống '
               '(hoặc map ngay cạnh) vẫn cùng chuyến; tự đi nơi khác rồi bay = chuyến mới, nhớ chỗ mới. '
               'Về tới nơi thì quên chỗ đó.')
        self.q_home_tip.text = ('Sẽ bay về: %s, ô %d,%d\n\n%s' % (self.rom.map_name(o[0], o[1]), o[2], o[3], how) if o
                                else 'Chưa có chỗ cũ (chưa bay bằng tool).\n\n' + how)

    def quest_foe(self):
        """(Pokémon đối thủ đang ra sân, hoang dã?) khi đang trong trận, ngược lại None."""
        st = self.game.battle_state()
        if not st or not st[0]:
            return None
        mons = [m for m in getattr(self, 'foe_mons', []) if not m.empty and m.checksum_ok
                and 1 <= m.species <= self.rom.max_species]
        if not mons:
            return None
        m = next((m for m in mons if m.hp > 0), mons[0])      # hoang dã chỉ có ô 1; trainer: con đầu còn máu
        return m, m.otid == self.game.player_otid()

    def quest_wild(self, force=False):
        """Khung "Pokémon hoang dã ở map này": loài theo cách gặp (wild_groups),
        tô vàng loài đang đối đầu; nhãn trên báo ô đang đứng / đối thủ hiện tại. Chỉ vẽ lại khi có thay đổi."""
        if not self.q_shown:
            return
        try:
            caught = self.game.caught_dex()
        except BridgeError:
            caught = None
        foe = self.q_foe
        here = self.q_shown == self.q_cur
        tile = self.story.encounter_tiles(*self.q_shown).get(self.q_player) if here and self.q_player else None
        sig = (self.q_shown, frozenset(caught or ()), foe and (foe[0].pid, foe[0].species, foe[0].hp, tuple(foe[0].pp)), tile)
        if sig == self.q_wsig and not force:
            return
        self.q_wsig = sig
        self.quest_foe_detail()
        if foe:
            m, wild = foe
            g, _, _ = iv_grade(m.iv, self.rom.base_stats(m.species))
            txt = '⚔ Đang đối đầu%s: %s%s Lv %d  ·  HP %d/%d' % (
                '' if wild else ' (trainer)', '★ ' if m.is_shiny_in_game() else '', self.rom.species_name(m.species),
                m.level, m.hp, m.maxhp)
            if wild:
                txt += '  ·  IV %s  ·  Poké Ball bắt %.1f%%' % (
                    IV_GRADES[g].lower(), 100 * catch_chance(self.rom.catch_rate(m.species), m.hp, m.maxhp, m.status))
        elif tile == 'land':
            txt = '🌿 Đang trên cỏ / sàn hang: mỗi bước có thể gặp Pokémon.'
        elif tile == 'water':
            txt = '🌊 Đang ở ô nước có Pokémon (Surf / câu cá).'
        else:
            txt = ''
        self.q_wlbl.config(text=txt)
        t = self.q_wtree
        t.delete(*t.get_children())
        self.q_wgroups, self.q_witems = {}, {}
        wild = self.rom.wild_for_map(*self.q_shown)
        if not wild:
            t.insert('', 'end', text='Map này không có Pokémon hoang dã.')
            return
        try:
            tid = self.game.rand_tid()
        except Exception:
            tid = None
        cur = foe[0].species if foe and foe[1] else None
        roam = [x for x in self.q_roam if x['map'] == self.q_shown]
        if roam:                                              # huyền thoại lang thang đang ở map này: lên đầu
            p = t.insert('', 'end', text='★ Huyền thoại lang thang', tags=('method',), open=True)
            for x in roam:
                self.q_wgroups.setdefault('land' if x['land'] else 'water', []).insert(0, p)
                got = caught is not None and self.rom.natdex(x['species']) in caught
                iid = t.insert(p, 'end', text='  ' + self.rom.species_name(x['species']),
                               image=self.photo(x['species'], False, 0.5) or '',
                               values=(x['level'], '25%' if self.roamer_can_meet(x) else '0% ✘',
                                       '✓' if got else ''),
                               tags=('cur',) if x['species'] == cur else ('roam',))
                self.q_witems[iid] = x['species']
        for key, label, rate, rows in self.wild_groups(wild, caught, tid):
            hidden = sum(1 for row in rows if row[4]) if self.hide_caught.get() else 0
            if hidden:
                rows = [row for row in rows if not row[4]]
            p = t.insert('', 'end', text='%s   (chỉ số gặp %d)%s' % (label, rate, '   — ẩn %d đã bắt' % hidden if hidden else ''),
                         tags=('method',), open=self.q_wopen.get(label, True))
            self.q_wgroups.setdefault('water' if key == 'fish' else key, []).append(p)
            for sp, lo, hi, pct, got in rows:
                iid = t.insert(p, 'end', text='  ' + self.rom.species_name(sp), image=self.photo(sp, False, 0.5) or '',
                               values=('%d' % lo if lo == hi else '%d-%d' % (lo, hi), '%d%%' % pct, '✓' if got else ''),
                               tags=(('cur',) if sp == cur else ()) + (('got',) if got else ()))
                self.q_witems[iid] = sp

    def quest_foe_detail(self):
        """Tab con "Chi tiết Pokémon": gặp đối thủ mới -> tự mở và hiện con đó (cập nhật HP/PP khi đang xem);
        hết trận -> quay lại "Việc cần làm" nếu chính tool đã tự mở."""
        foe = self.q_foe
        if not foe:
            self.q_lastfoe = None
            if self.q_auto:
                self.q_auto = False
                self.q_nb.select(0)
            return
        m = foe[0]
        if m.pid != self.q_lastfoe:                       # đối thủ mới (hoặc trainer đổi con)
            self.q_lastfoe, self.q_fshown = m.pid, 'foe'
            if self.q_nb.index('current') == 0:
                self.q_auto = True
                self.q_nb.select(self.q_t_det)
        if self.q_fshown == 'foe':
            self.foe_render(m, self.q_fd)

    def quest_pick_species(self):
        s = self.q_wtree.selection()
        sp = self.q_witems.get(s[0]) if s else None
        if sp:
            self.q_fshown, self.q_auto = ('sp', sp), False
            self.species_preview(sp, self.q_fd)
            self.q_nb.select(self.q_t_det)

    def quest_pick_hist(self):
        s = self.q_htree.selection()
        if not s:
            return
        e = self.hist_by_id.get(int(s[0]))
        if e:
            self.q_fshown, self.q_auto = ('hist', e['id']), False
            self.foe_render(e['m'], self.q_fd)
            self.q_nb.select(self.q_t_det)

    def quest_show_foe(self):
        if self.q_foe:
            self.q_fshown = 'foe'
            self.foe_render(self.q_foe[0], self.q_fd)
            self.q_nb.select(self.q_t_det)

    def quest_zone_click(self, ev):
        """Bấm vào vùng tô trên bản đồ -> mở + cuộn tới nhóm Pokémon của kiểu gặp đó (cỏ / nước)."""
        cv = self.q_cv
        if any(t.startswith('m') for t in cv.gettags('current')) or not self.q_shown:   # bấm chấm số: để chấm xử lý
            return
        k = self.q_scale * 16
        xy = (int(cv.canvasx(ev.x)) // k, int(cv.canvasy(ev.y)) // k)
        kind = self.story.encounter_tiles(*self.q_shown).get(xy)
        if not kind or not self.q_wild_on.get():
            return
        self.q_nb.select(self.q_t_wild)                       # mở tab con 🐾 Pokémon
        t = self.q_wtree
        t.selection_remove(*t.selection())
        for i, p in enumerate(self.q_wgroups.get(kind, [])):
            t.item(p, open=True)
            if i == 0:
                t.selection_set(p)
                t.see(p)
                kids = t.get_children(p)
                if kids:
                    t.see(kids[-1])
                t.see(p)
        self.say('Ô %d,%d: %s — danh sách ở tab 🐾 Pokémon.' % (xy[0], xy[1],
                 'cỏ / sàn hang' if kind == 'land' else 'nước (Surf / câu cá)'))

    def quest_player(self):
        """Ô đỏ = chỗ bạn đứng (chỉ khi đang xem đúng map đang đứng)."""
        cv = self.q_cv
        cv.delete('player')
        if not self.q_img or self.q_shown != self.q_cur:
            return
        x, y = self.game.player_xy()
        k = self.q_scale * 16
        gfx, face = self.game.player_look()
        key = (gfx, face, self.q_scale)
        cache = self.__dict__.setdefault('_q_ow', {})
        if key not in cache:
            from PIL import Image, ImageTk
            spr = self.story.ow_sprite(gfx, face)
            cache[key] = ImageTk.PhotoImage(spr.resize((spr.width * self.q_scale, spr.height * self.q_scale), Image.NEAREST)) if spr else None
        if cache[key]:                                        # hình nhân vật thật theo hướng đang quay
            cv.create_rectangle(x * k, y * k, x * k + k, y * k + k, outline='red', width=2, tags='player')
            cv.create_image(x * k + k // 2, y * k + k, image=cache[key], anchor='s', tags='player')
        else:
            cv.create_rectangle(x * k - 2, y * k - 2, x * k + k + 2, y * k + k + 2, outline='red', width=4, tags='player')
        cv.create_rectangle(x * k + k // 2 - 17, y * k + k + 4, x * k + k // 2 + 17, y * k + k + 20, fill='red', outline='white', tags='player')
        cv.create_text(x * k + k // 2, y * k + k + 12, text='BẠN', fill='white', font=('Segoe UI', 8, 'bold'), tags='player')
        if self.q_foe:                                        # đang trong trận: hình đối thủ cạnh nhân vật
            m, wild = self.q_foe
            shiny = m.is_shiny_in_game()
            ph = self.photo(m.species, shiny, 0.75)
            ox, oy = x * k + k + 2, y * k + k
            if ph:
                cv.create_image(ox, oy, image=ph, anchor='sw', tags='player')
            lab = cv.create_text(ox + 24, oy - 50, anchor='s', fill='#ffe14d', font=('Segoe UI', 9, 'bold'), tags='player',
                                 text='%s%s Lv%d%s' % ('★ ' if shiny else '', self.rom.species_name(m.species), m.level,
                                                       '' if wild else ' (trainer)'))
            bg = cv.create_rectangle(*[a + b for a, b in zip(cv.bbox(lab), (-3, -1, 3, 1))], fill='#333', outline='#ffe14d',
                                     tags='player')
            cv.tag_lower(bg, lab)
        if self.q_cam_map != self.q_shown:                    # sang map mới: đi theo lại
            self.q_cam_map = self.q_shown
            self.quest_cam_resume(see=False)
        if self.q_cam:
            if self.q_player is None or self.quest_near_edge(x, y):
                self.quest_see(x, y)
        elif self.q_cam_at and max(abs(x - self.q_cam_at[0]), abs(y - self.q_cam_at[1])) >= 3:
            self.quest_cam_resume(see=False)                  # đi tiếp vài bước = quay lại chơi -> theo lại
            self.quest_see(x, y)
        self.q_player = (x, y)

    def quest_near_edge(self, x, y, margin=3):
        """Nhân vật cách mép khung nhìn < margin ô (hoặc ra ngoài) -> cần cuộn."""
        cv, k = self.q_cv, self.q_scale * 16
        x0, y0 = cv.canvasx(0), cv.canvasy(0)
        x1, y1 = x0 + cv.winfo_width(), y0 + cv.winfo_height()
        W, H = self.q_img.width(), self.q_img.height()
        m = margin * k
        return ((x * k < x0 + m and x0 > 0) or (x * k + k > x1 - m and x1 < W) or
                (y * k < y0 + m and y0 > 0) or (y * k + k > y1 - m and y1 < H))

    def quest_cam_pause(self):
        """Tự kéo / lăn / chọn chỗ khác trên bản đồ: ngưng đi theo, hiện nút 🎯."""
        if not self.q_cam:
            return
        self.q_cam, self.q_cam_at = False, self.q_player
        if self.q_shown == self.q_cur:
            self.q_cam_btn.place(relx=1.0, x=-22, y=6, anchor='ne')

    def quest_cam_resume(self, see=True):
        self.q_cam, self.q_cam_at = True, None
        self.q_cam_btn.place_forget()
        if see and self.q_player and self.q_shown == self.q_cur:
            self.quest_see(*self.q_player)

    def quest_zoom(self, ev):
        """Ctrl + lăn chuột: phóng to / thu nhỏ (×1..×4). Đang theo nhân vật thì giữ nhân vật giữa khung,
        không thì giữ ô dưới chuột đứng yên."""
        if not self.q_img:
            return
        z = max(1, min(4, self.q_scale + (1 if ev.delta > 0 else -1)))
        if z == self.q_scale:
            return
        cv, k = self.q_cv, self.q_scale * 16
        tx, ty = cv.canvasx(ev.x) / k, cv.canvasy(ev.y) / k   # ô (số thực) dưới chuột
        self.q_zoom = z
        self.save_area_state()
        follow = self.q_cam and self.q_shown == self.q_cur
        self.quest_render()
        if not follow:
            k = self.q_scale * 16
            cv.update_idletasks()
            cv.xview_moveto(max(0, (tx * k - ev.x) / self.q_img.width()))
            cv.yview_moveto(max(0, (ty * k - ev.y) / self.q_img.height()))
        self.q_zoom_lbl.configure(text=' ×%d ' % self.q_scale)
        self.q_zoom_lbl.place(x=6, y=6)
        if getattr(self, '_q_zoom_job', None):
            self.after_cancel(self._q_zoom_job)
        self._q_zoom_job = self.after(1200, self.q_zoom_lbl.place_forget)

    def quest_see(self, x, y):
        cv, k = self.q_cv, self.q_scale * 16
        W, H = self.q_img.width(), self.q_img.height()
        cv.update_idletasks()
        cw, ch = cv.winfo_width(), cv.winfo_height()
        cv.xview_moveto(max(0, (x * k - cw / 2) / W))
        cv.yview_moveto(max(0, (y * k - ch / 2) / H))

    def quest_pick(self):
        i = self.q_combo.current()
        if i >= 0:
            self.q_follow.set(False)
            self.q_find.set('')
            self.q_shown = self.q_maps[i][:2]
            self.quest_render()

    def quest_open(self, gn):
        if any((g, n) == gn for g, n, _ in self.q_maps):
            self.q_follow.set(gn == self.q_cur)
            self.q_find.set('')
            self.q_shown = gn
            self.q_combo.set(next(x[2] for x in self.q_maps if (x[0], x[1]) == gn))
            self.quest_render()

    def quest_have(self):
        have = set()
        for i in range(self.prof.n_pockets):
            try:
                have |= {it for it, q in self.game.read_pocket(i) if q}
            except BridgeError:
                pass
        return have

    def quest_sum_label(self):
        here = self.q_shown == self.q_cur
        txt = '📍 Bạn đang ở' if here else '👁 Đang xem'
        if self.q_sum.cget('text') != txt:
            self.q_sum.config(text=txt, foreground='#c62828' if here else '#1565c0')

    def quest_render(self):
        import mm_items
        from PIL import Image, ImageTk
        self._q_job = None
        st, T = self.story, self.q_text
        try:
            flag = self.game.flags()
        except BridgeError:
            flag = None
        q = mm_items.fold(self.q_find.get().strip())
        T.configure(state='normal')
        T.delete('1.0', 'end')
        self.q_det_i = None
        if len(q) >= 2:                                       # tìm cả thế giới: map đang đứng, map kế bên lên trước
            if self.q_world is None:
                self.q_world = [(r, mm_items.fold('%s %s %s' % (self.rom.map_name(*r['map']), r['title'], r['detail'])))
                                for g, n in st.maps() for r in st.rows(g, n)]
            here = self.q_cur or self.q_shown
            near = {r['to'] for r in st.rows(*here) if r.get('to')} if here else set()
            rows = [r for r, t in self.q_world if q in t and r['sec'] != 'Đi tiếp']
            rows.sort(key=lambda r: (r['map'] != here, r['map'] not in near, r['map']))
            T.insert('end', 'Kết quả tìm "%s": %d (bấm vào dòng để mở map đó)\n' % (self.q_find.get().strip(), len(rows)), 'head')
            for i, r in enumerate(rows[:400]):
                s = st.status(r, flag)
                tag = 'r%d' % i
                T.insert('end', '%s — %s: %s%s\n' % (self.rom.map_name(*r['map']), r['sec'], r['title'].split('  [khi:')[0],
                                                     ('  [%s]' % s[0]) if s else ''), (tag, 'done') if s and s[1] else (tag,))
                T.tag_bind(tag, '<Button-1>', lambda e, r=r: self.guard(self.quest_open)(r['map']))
            T.configure(state='disabled')
            return
        if not self.q_shown:
            T.configure(state='disabled')
            return
        g, n = self.q_shown
        info = st.map_info(g, n)
        self.quest_sum_label()
        have = self.quest_have()
        guide = st.guide(g, n, flag, have)
        rpath = self.route_render_text(T)
        self.q_sig = tuple(st.status(r, flag) for r in st.rows(g, n))
        self.q_entries, self.q_marks, num = [], {}, 0
        for head, entries in guide:
            T.insert('end', head + '\n', 'head')
            for e in entries:
                nums = []
                for r in e['rows']:
                    if r['x'] is None:
                        continue
                    if id(r) not in self.q_marks:
                        num += 1
                        self.q_marks[id(r)] = (num, r, e)
                    nums.append(self.q_marks[id(r)][0])
                i = len(self.q_entries)
                self.q_entries.append(e)
                tag = 'e%d' % i
                lead = (''.join(self.circ(k) for k in nums[:8]) + ('…' if len(nums) > 8 else '') + ' ') if nums else '• '
                T.insert('end', lead + e['text'] + '\n', (tag, 'done') if e['done'] else (tag,))
                T.tag_bind(tag, '<Button-1>', lambda ev, i=i: self.quest_select(i))
                if e.get('to'):
                    T.tag_bind(tag, '<Double-1>', lambda ev, to=e['to']: self.guard(self.quest_open)(to))
        if guide:
            T.insert('end', '\nBấm một dòng để xem chi tiết và chỗ đó trên bản đồ; bấm đúp dòng "Lối đi" để mở map kế bên. '
                            'Chỗ ghi "có thể" là tool chưa chắc.', 'hint')
        T.configure(state='disabled')
        if self.q_nb.select() == str(self.q_t_story):
            self.quest_story(flag, have)
        # bản đồ
        im = st.map_image(g, n).copy()
        if self.q_wild_on.get() and st.encounter_tiles(g, n):    # tô vùng gặp Pokémon (dưới hình NPC)
            im = im.convert('RGBA')
            im.alpha_composite(st.wild_overlay(g, n))
            im = im.convert('RGB')
        for npc in info['npcs']:                              # vẽ hình NPC còn ở trên map (cờ object bật = đã biến mất)
            if npc['flag'] >= 0x20 and flag and flag(npc['flag']):
                continue
            spr = st.ow_sprite(npc['gfx'])
            if spr:
                im.paste(spr, (npc['x'] * 16 + 8 - spr.width // 2, npc['y'] * 16 + 16 - spr.height), spr)
        self.q_scale = self.q_zoom or (2 if im.width * 2 <= 1000 else 1)
        if self.q_scale != 1:
            im = im.resize((im.width * self.q_scale, im.height * self.q_scale), Image.NEAREST)   # giữ nét pixel
        self.q_img = ImageTk.PhotoImage(im)
        cv, k = self.q_cv, self.q_scale * 16
        cv.delete('all')
        cv.create_image(0, 0, image=self.q_img, anchor='nw')
        cv.configure(scrollregion=(0, 0, im.width, im.height))
        for num, r, e in self.q_marks.values():
            s = st.status(r, flag)
            col = '#9e9e9e' if s and s[1] else self.Q_COL.get(r['sec'], '#555')
            cx, cy, rad = r['x'] * k + k // 2, r['y'] * k + k // 2, 10 if self.q_scale > 1 else 8
            tag = 'm%d' % num
            cv.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill=col, outline='white', width=2, tags=(tag,))
            cv.create_text(cx, cy, text=str(num), fill='white', font=('Segoe UI', 8, 'bold'), tags=(tag,))
            cv.tag_bind(tag, '<Button-1>', lambda ev, e=e: self.quest_select(self.q_entries.index(e)))
            cv.tag_bind(tag, '<Enter>', lambda ev: cv.configure(cursor='hand2'))
            cv.tag_bind(tag, '<Leave>', lambda ev: cv.configure(cursor=''))
        self.route_draw(rpath)
        self.q_player = None
        try:
            self.quest_player()
        except BridgeError:
            pass
        try:
            self.quest_wild(force=True)
        except BridgeError:
            pass
        if self.q_shown != self.q_cur:
            cv.xview_moveto(0)
            cv.yview_moveto(0)

    def quest_select(self, i):
        e = self.q_entries[i]
        T = self.q_text
        T.tag_remove('hl', '1.0', 'end')
        rng = T.tag_ranges('e%d' % i)
        if rng:
            T.tag_add('hl', rng[0], rng[1])
            T.see(rng[0])
        self.q_cv.delete('sel')
        k = self.q_scale * 16
        for r in e['rows']:
            if r['x'] is not None:
                cx, cy = r['x'] * k + k // 2, r['y'] * k + k // 2
                self.q_cv.create_oval(cx - 16, cy - 16, cx + 16, cy + 16, outline='#ffeb3b', width=4, tags='sel')
        pts = [r for r in e['rows'] if r['x'] is not None]
        if pts:
            self.quest_cam_pause()                            # xem chỗ khác: ngưng đi theo nhân vật
            self.quest_see(pts[0]['x'], pts[0]['y'])
        T.configure(state='normal')                          # chi tiết hiện ngay dưới dòng (bấm lại để thu)
        old = T.tag_ranges('detail')
        if old:
            T.delete(old[0], old[-1])
        again, self.q_det_i = self.q_det_i == i, None
        rng = T.tag_ranges('e%d' % i)
        lines = []
        for r in e['rows']:
            if r['detail']:
                lines += ['%s%s:' % ('ô %d,%d — ' % (r['x'], r['y']) if r['x'] is not None else '', r['title']), r['detail']]
        if rng and lines and not again:
            T.insert(rng[1], '\n'.join(lines) + '\n', 'detail')
            self.q_det_i = i
        T.configure(state='disabled')

    def quest_story(self, flag=None, have=None):
        """Tab con 📖 Cốt truyện: 8 huy hiệu + vật phẩm then chốt; bấm dòng = mở map nơi làm bước đó."""
        st, T = self.story, self.q_stext
        if flag is None:
            flag, have = self.game.flags(), self.quest_have()
        T.configure(state='normal')
        T.delete('1.0', 'end')
        for k, (head, entries) in enumerate(st.main_story(flag, have)):
            T.insert('end', head + '\n', 'head')
            for j, e in enumerate(entries):
                tag = 's%d_%d' % (k, j)
                mark = '✔ ' if e['done'] else '⬜ ' if e['done'] is False else '• '
                T.insert('end', mark + e['text'] + '\n', (tag, 'done') if e['done'] else (tag,))
                if e['maps']:
                    T.tag_bind(tag, '<Button-1>', lambda ev, m=e['maps'][0]: (self.q_nb.select(0),
                                                                               self.guard(self.quest_open)(m)))
        T.insert('end', '\nBấm một dòng để mở map nơi làm bước đó.', 'hint')
        T.configure(state='disabled')

    def quest_unlock_all(self):
        """Nút 🔓: sao lưu .sav rồi ghi gói A (Game.unlock_all). Chỉ đổi RAM: chưa lưu game thì tắt mGBA là mất."""
        if not messagebox.askyesno('Mở khoá săn shiny', (
                'Sẽ bật: 8 huy hiệu (dùng HM ngoài trận), giày chạy, Pokédex toàn quốc, Bay tới 16 thị trấn; thêm '
                'HM01-08, 3 cần câu, Mach + Acro Bike, Go-Goggles (sa mạc), Devon Scope (Kecleon).\n\n'
                'KHÔNG đụng cốt truyện, trainer, vật phẩm, huyền thoại; không tính là đã phá đảo. '
                'Gym vẫn đánh được, cốt truyện vẫn chơi tiếp được.\n\n'
                'File .sav được sao lưu vào save_backup trước. Làm tiếp?')):
            return
        if os.path.exists(self.SAV_FILE):
            os.makedirs(os.path.join(ROOT, 'save_backup'), exist_ok=True)
            with open(self.SAV_FILE, 'rb') as f:
                data = f.read()
            with open(os.path.join(ROOT, 'save_backup', time.strftime('%Y%m%d-%H%M%S') + '_truoc_mo_khoa.sav'), 'wb') as f:
                f.write(data)
        added = self.game.unlock_all()
        self.quest_story()
        self.say('Đã mở khoá%s. Dạy HM bằng đĩa trong ngăn TM/HM. Nhớ LƯU GAME.' %
                 ('; thêm ' + ', '.join(added) if added else ''))

    # ------------------------------------------------------------ tab Tiền
    def _build_money(self, f):
        row = ttk.Frame(f)
        row.pack(side='top', fill='x', padx=6, pady=(4, 2))
        self.money_lbl = ttk.Label(row, text='💰 Tiền: ?', font=('Segoe UI', 12, 'bold'))
        self.money_lbl.pack(side='left', padx=(0, 10))
        self.money_var = tk.IntVar(value=0)
        mx = self.prof.max_money
        ttk.Spinbox(row, from_=0, to=mx, increment=10000, width=12, textvariable=self.money_var).pack(side='left')
        ttk.Button(row, text='Đặt', command=self.guard(self.money_set)).pack(side='left', **PAD)
        ttk.Button(row, text='+100.000', command=self.guard(lambda: self.money_add(100000))).pack(side='left', **PAD)
        ttk.Button(row, text='Tối đa', command=self.guard(lambda: self.money_set(mx))).pack(side='left', **PAD)

    def refresh_money(self):
        v = self.game.money()
        self.money_lbl.config(text='💰 Tiền: %s' % format(v, ',').replace(',', '.'))
        self.money_var.set(v)

    def money_set(self, v=None):
        v = int(self.money_var.get()) if v is None else v
        self.game.set_money(v)
        self.refresh_money()
        self.say('Đã đặt tiền %s. Nhớ lưu game.' % format(max(0, min(self.prof.max_money, v)), ','))

    def money_add(self, n):
        self.game.set_money(self.game.money() + n)
        self.refresh_money()
        self.say('Đã cộng %s. Nhớ lưu game.' % format(n, ','))

    # ------------------------------------------------------------ chung
    def refresh_all(self):
        try:
            self.refresh_party()
            self.refresh_bag()
            self.refresh_money()
            self.say('Đã kết nối với mGBA — %s.' % self.prof.title)
        except BridgeError as e:
            self.say('Chưa kết nối: %s' % e, False)


def already_running(name='PokemonToolEmerald'):
    """Đã có một tool đang chạy (mutex tên riêng của Windows) -> True. Lua tự mở tool mỗi lần nạp script."""
    if os.name != 'nt' or '--fake' in sys.argv:
        return False
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = ctypes.c_void_p
    for _ in range(40 if '--restart' in sys.argv else 1):                    # mở lại sau Đồng bộ: đợi bản cũ thoát
        already_running.h = k32.CreateMutexW(None, False, name)   # giữ handle tới khi thoát
        if k32.GetLastError() != 183:                                       # ERROR_ALREADY_EXISTS
            return False
        k32.CloseHandle(ctypes.c_void_p(already_running.h))
        time.sleep(0.25)
    return True


if __name__ == '__main__':
    if already_running():
        sys.exit(0)
    app = App(fake='--fake' in sys.argv)
    if '--hunt' in sys.argv:                                  # mở lại rồi săn luôn (Claude mở hộ khi Duy đi vắng)
        app.after(5000, app.hunt_toggle)
    if '--selftest' in sys.argv:
        app.after(1500, lambda: (sys.stdout.reconfigure(encoding='utf-8'), print('GUI OK:', app.status.cget('text')), app.destroy()))
    app.mainloop()

