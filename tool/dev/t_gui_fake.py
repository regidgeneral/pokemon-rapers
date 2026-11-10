"""Mở giao diện ở chế độ giả (cửa sổ ẩn, không chụp màn hình), đi qua mọi tab/tab con, in nội dung các bảng + lỗi.
  py -3 dev\\t_gui_fake.py"""
import os, sys, traceback
from tkinter import ttk
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.chdir(HERE)
sys.argv.append('--fake')
sys.stdout.reconfigure(encoding='utf-8')
from tkinter import messagebox
for k in ('showinfo', 'showwarning', 'showerror', 'askyesno', 'askokcancel', 'askyesnocancel'):
    setattr(messagebox, k, lambda *a, _k=k, **kw: print('[hộp thoại %s]' % _k, *a) or False)
import mm_gui

LOG = os.path.join(HERE, 'tick_error.log')
if os.path.exists(LOG):
    os.remove(LOG)
errors = []
app = mm_gui.App(fake=True)
app.withdraw()
app.report_callback_exception = lambda e, v, tb: errors.append(''.join(traceback.format_exception(e, v, tb)))
steps = []


def dump(title):
    print('=== %s | trạng thái: %s' % (title, app.status.cget('text')))

    def walk(w):
        if isinstance(w, ttk.Treeview) and w.winfo_ismapped() is not None:
            rows = w.get_children()
            if rows:
                print('  bảng %s: %d dòng' % (w.winfo_name(), len(rows)))
                for r in rows[:4]:
                    print('    ', w.item(r, 'text'), w.item(r, 'values'))
        for c in w.winfo_children():
            walk(c)
    walk(app.nb.nametowidget(app.nb.select()))


def run_steps():
    if not steps:
        if os.path.exists(LOG):
            print(open(LOG, encoding='utf-8').read()[-6000:])
        for e in errors:
            print(e)
        print('LỖI: %d bấm, log nền: %s' % (len(errors), os.path.exists(LOG)))
        app.destroy()
        return
    fn, wait = steps.pop(0)
    try:
        fn()
    except Exception:
        errors.append(traceback.format_exc())
    app.after(wait, run_steps)


def start():
    for i, t in enumerate(app.nb.tabs()):
        steps.append((lambda t=t: app.nb.select(t), 1500))
        if i == 0 and hasattr(app, 'q_nb'):
            for j, st in enumerate(app.q_nb.tabs()):
                steps.append((lambda st=st: app.q_nb.select(st), 900))
                steps.append((lambda j=j: dump('Bản đồ / tab con %d %s' % (j, app.q_nb.tab(app.q_nb.tabs()[j], 'text'))), 50))
        else:
            steps.append((lambda i=i: dump(app.nb.tab(app.nb.tabs()[i], 'text')), 50))
    run_steps()


app.after(2500, start)
app.mainloop()
