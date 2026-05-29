"""
Salary Ticker - 实时工资进度桌面小工具
迷你：金额+进度条背景，单击切换日/月
详情：双击展开，时钟+进度+倒计时+设置按钮
"""

import tkinter as tk
import json
import os
import math
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

SETTINGS_FILE = Path(os.environ.get("APPDATA", Path.home())) / "salary-ticker" / "settings.json"

DEFAULT_SETTINGS = {
    "monthly_salary": 0,
    "daily_hours": 8,
    "lunch_start": "12:00",
    "lunch_end": "13:00",
    "clock_in_time": None,
}

BG = "#0a0a14"
BG2 = "#12122a"
BG3 = "#1a1a36"
FG = "#ffffff"
FG2 = "#8888aa"
FG3 = "#555570"
A_S = (40, 90, 220)
A_E = (0, 210, 165)
GREEN = "#00d4aa"
ORANGE = "#ffaa44"

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    except Exception:
        return {**DEFAULT_SETTINGS}

def save_settings(st):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ── Salary Engine ─────────────────────────────────────────────────────────────

def wd_in_month(year, month):
    n = 0
    for d in range(1, (datetime(year, month+1, 1) - timedelta(days=1)).day + 1):
        if datetime(year, month, d).weekday() < 5: n += 1
    return n

def t2m(s):
    if not s: return 0
    p = s.split(":")
    return int(p[0])*60 + int(p[1]) if len(p) == 2 else 0

def m2t(mins):
    return f"{int(mins)//60:02d}:{int(mins)%60:02d}"

def daily_rate(st):
    wd = wd_in_month(datetime.now().year, datetime.now().month)
    return st["monthly_salary"] / wd if wd > 0 else 0

def sec_rate(st):
    ds = st["daily_hours"] * 3600
    return daily_rate(st) / ds if ds > 0 else 0

def get_work_start(st):
    ci = st.get("clock_in_time")
    if ci: return t2m(ci)
    return datetime.now().hour * 60 + datetime.now().minute

def get_work_end(st):
    return get_work_start(st) + int(st["daily_hours"] * 60) + get_lunch_duration(st)

def get_lunch_start(st):
    return t2m(st.get("lunch_start", "12:00"))

def get_lunch_end(st):
    return t2m(st.get("lunch_end", "13:00"))

def get_lunch_duration(st):
    return get_lunch_end(st) - get_lunch_start(st)

def calc_daily(st):
    rate = sec_rate(st)
    if rate == 0: return 0
    now = datetime.now()
    if now.weekday() >= 5: return 0

    ws = get_work_start(st)
    we = get_work_end(st)
    ls = get_lunch_start(st)
    le = get_lunch_end(st)
    m = now.hour * 60 + now.minute + now.second / 60.0

    if m < ws:
        return 0
    elif m >= we:
        return rate * st["daily_hours"] * 3600
    else:
        worked = m - ws
        # 扣除已过的午休时间
        if m > le:
            worked -= (le - ls)  # 午休全部过了
        elif m > ls:
            worked -= (m - ls)  # 午休中，只扣已过的部分
        return rate * max(0, worked) * 60

def calc_monthly(st):
    dr = daily_rate(st)
    if dr == 0: return 0
    now = datetime.now()
    days = 0
    for d in range(1, now.day):
        if datetime(now.year, now.month, d).weekday() < 5: days += 1
    return days * dr + calc_daily(st)

def is_working(st):
    now = datetime.now()
    if now.weekday() >= 5: return False
    m = now.hour * 60 + now.minute
    ws = get_work_start(st)
    we = get_work_end(st)
    ls = get_lunch_start(st)
    le = get_lunch_end(st)
    if ws <= m < we:
        # 在工作时间范围内，但午休期间不算
        if ls <= m < le:
            return False
        return True
    return False

def is_lunch(st):
    now = datetime.now()
    if now.weekday() >= 5: return False
    m = now.hour * 60 + now.minute
    ls = get_lunch_start(st)
    le = get_lunch_end(st)
    return ls <= m < le

def today_pct(st):
    ws = get_work_start(st)
    we = get_work_end(st)
    m = datetime.now().hour * 60 + datetime.now().minute
    t = we - ws
    return min(1.0, max(0.0, (m - ws) / t)) if t > 0 else 0

def month_pct(st):
    now = datetime.now()
    wd = wd_in_month(now.year, now.month)
    if wd == 0: return 0
    e = 0
    for d in range(1, now.day):
        if datetime(now.year, now.month, d).weekday() < 5: e += 1
    if now.weekday() < 5: e += today_pct(st)
    return min(1.0, e / wd)

def get_countdown(st):
    """返回 (文本, 颜色) 午休倒计时或下班倒计时"""
    now = datetime.now()
    if now.weekday() >= 5:
        return ("周末", FG3)
    m = now.hour * 60 + now.minute + now.second / 60.0
    ls = get_lunch_start(st)
    le = get_lunch_end(st)
    we = get_work_end(st)

    if m < ls:
        # 午休前，显示午休倒计时
        remain = ls - m
        return (f"午休 {int(remain)}min", ORANGE)
    elif m < le:
        # 午休中，显示午休结束倒计时
        remain = le - m
        return (f"午休剩余 {int(remain)}min", ORANGE)
    elif m < we:
        # 下午，显示下班倒计时
        remain = we - m
        h = int(remain // 60)
        mi = int(remain % 60)
        if h > 0:
            return (f"下班 {h}h{mi}min", GREEN)
        else:
            return (f"下班 {mi}min", GREEN)
    else:
        return ("已下班 ✓", GREEN)

# ── Particle System ───────────────────────────────────────────────────────────

class P:
    __slots__ = ['x','y','vx','vy','l','d','s','r','g','b']

class PS:
    def __init__(self, c):
        self.c = c; self.ps = []; self._a = None; self._i = []

    def emit(self, x, y, n=2):
        for _ in range(n):
            p = P(); p.x=x+random.uniform(-8,8); p.y=y+random.uniform(-3,3)
            p.vx=random.uniform(-0.7,0.7); p.vy=random.uniform(-1.5,-0.2)
            p.l=1.0; p.d=random.uniform(0.04,0.06); p.s=random.uniform(0.7,1.5)
            p.r=255; p.g=random.randint(190,230); p.b=random.randint(40,80)
            self.ps.append(p)
        if not self._a: self._st()

    def burst(self, x, y, n=8):
        for i in range(n):
            a=2*math.pi*i/n+random.uniform(-.2,.2); sp=random.uniform(1,2.2)
            p=P(); p.x=x+random.uniform(-3,3); p.y=y+random.uniform(-3,3)
            p.vx=math.cos(a)*sp; p.vy=math.sin(a)*sp-.5
            p.l=1.0; p.d=random.uniform(.025,.04); p.s=random.uniform(1,2)
            p.r=255; p.g=random.randint(180,240); p.b=random.randint(20,70)
            self.ps.append(p)
        if not self._a: self._st()

    def _st(self):
        for i in self._i: self.c.delete(i)
        self._i.clear(); al=[]
        for p in self.ps:
            p.x+=p.vx; p.y+=p.vy; p.vy+=.04; p.l-=p.d
            if p.l>0:
                al.append(p); sz=p.s*p.l
                cr=min(255,int(p.r*p.l)); cg=min(255,int(p.g*p.l)); cb=min(255,int(p.b*p.l))
                it=self.c.create_oval(p.x-sz,p.y-sz,p.x+sz,p.y+sz,
                    fill=f"#{cr:02x}{cg:02x}{cb:02x}",outline="")
                self._i.append(it)
        self.ps=al
        self._a=self.c.after(33,self._st) if self.ps else None

# ── Main Application ──────────────────────────────────────────────────────────

class App:
    MW, MH = 160, 38
    DW, DH = 280, 190

    def __init__(self):
        self.st = load_settings()
        self.prev = ""; self.pk = 0; self.gp = 0.0
        self.ox = 0; self.oy = 0; self._dragged = False
        self.detail = False
        self.show_month = False
        self.sp_open = False

        # 首次启动或新的一天：自动打卡
        today = datetime.now().strftime("%Y-%m-%d")
        ci_day = self.st.get("clock_in_day")
        if ci_day != today:
            now = datetime.now()
            self.st["clock_in_time"] = f"{now.hour:02d}:{now.minute:02d}"
            self.st["clock_in_day"] = today
            save_settings(self.st)

        self.root = tk.Tk()
        self.root.title("")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg=BG)
        self.root.geometry(f"{self.MW}x{self.MH}")
        self.root.resizable(False, False)

        # ── Mini canvas ──
        self.cv = tk.Canvas(self.root, bg=BG, highlightthickness=0, cursor="fleur")
        self.cv.pack(fill="both", expand=True)
        self.cv.bind("<ButtonPress-1>", self._on_press)
        self.cv.bind("<B1-Motion>", self._on_drag)
        self.cv.bind("<ButtonRelease-1>", self._on_release)
        self.cv.bind("<Double-Button-1>", self._on_dbl)
        self.cv.bind("<Button-3>", self._on_right)

        self.ps = PS(self.cv)
        self.dot = self.cv.create_oval(5,5,11,11, fill="#333350", outline="")
        self.txt = self.cv.create_text(self.MW//2+4, self.MH//2,
            text="¥0.00", font=("Consolas", 14, "bold"), fill=FG, anchor="center")
        self.hint = self.cv.create_text(self.MW-4, self.MH-3,
            text="", font=("Segoe UI", 6), fill="#333350", anchor="se")

        # ── Detail frame ──
        self.df = tk.Frame(self.root, bg=BG)

        self.dcv = tk.Canvas(self.df, width=self.DW-16, height=40, bg=BG, highlightthickness=0, cursor="fleur")
        self.dcv.pack(padx=8, pady=(8,2))
        self.dcv.bind("<ButtonPress-1>", self._on_press)
        self.dcv.bind("<B1-Motion>", self._on_drag)
        self.dcv.bind("<Double-Button-1>", self._on_dbl)
        self.dcv.bind("<Button-3>", self._on_right)

        self.dps = PS(self.dcv)
        self.ddot = self.dcv.create_oval(4,4,10,10, fill="#333350", outline="")
        self.dtxt = self.dcv.create_text((self.DW-16)//2+4, 20,
            text="¥0.00", font=("Consolas", 20, "bold"), fill=FG, anchor="center")

        # Time + countdown
        info = tk.Frame(self.df, bg=BG, cursor="fleur")
        info.pack(fill="x", padx=8)
        info.bind("<ButtonPress-1>", self._on_press)
        info.bind("<B1-Motion>", self._on_drag)
        info.bind("<Double-Button-1>", self._on_dbl)
        info.bind("<Button-3>", self._on_right)

        self.dtime = tk.Label(info, text="", font=("Consolas", 9), bg=BG, fg=FG3, cursor="fleur")
        self.dtime.pack(side="right")
        self.dtime.bind("<ButtonPress-1>", self._on_press)
        self.dtime.bind("<B1-Motion>", self._on_drag)
        self.dtime.bind("<Double-Button-1>", self._on_dbl)
        self.dtime.bind("<Button-3>", self._on_right)

        self.dcountdown = tk.Label(info, text="", font=("Segoe UI", 8, "bold"), bg=BG, fg=GREEN, cursor="fleur")
        self.dcountdown.pack(side="left")
        self.dcountdown.bind("<ButtonPress-1>", self._on_press)
        self.dcountdown.bind("<B1-Motion>", self._on_drag)
        self.dcountdown.bind("<Double-Button-1>", self._on_dbl)
        self.dcountdown.bind("<Button-3>", self._on_right)

        # Work hours info
        self.dwork = tk.Label(self.df, text="", font=("Segoe UI", 8), bg=BG, fg=FG3, cursor="fleur")
        self.dwork.pack(anchor="w", padx=8)
        self.dwork.bind("<ButtonPress-1>", self._on_press)
        self.dwork.bind("<B1-Motion>", self._on_drag)
        self.dwork.bind("<Double-Button-1>", self._on_dbl)
        self.dwork.bind("<Button-3>", self._on_right)

        # Toggle
        self.dlbl = tk.Label(self.df, text="▶ 今日累计", font=("Segoe UI",7),
                             bg=BG, fg=FG3, cursor="hand2")
        self.dlbl.pack(anchor="w", padx=8, pady=(2,0))
        self.dlbl.bind("<Button-1>", self._toggle_view)

        # Progress
        pf = tk.Frame(self.df, bg=BG, cursor="fleur")
        pf.pack(fill="x", padx=8, pady=(4,2))
        pf.bind("<ButtonPress-1>", self._on_press)
        pf.bind("<B1-Motion>", self._on_drag)
        pf.bind("<Double-Button-1>", self._on_dbl)
        pf.bind("<Button-3>", self._on_right)

        r1 = tk.Frame(pf, bg=BG); r1.pack(fill="x")
        tk.Label(r1, text="今日", font=("Segoe UI",8), bg=BG, fg=FG3, width=4, anchor="w").pack(side="left")
        self.dt_cv = tk.Canvas(r1, width=190, height=8, bg=BG3, highlightthickness=0)
        self.dt_cv.pack(side="left", padx=4)
        self.dt_pct = tk.Label(r1, text="0%", font=("Consolas",8), bg=BG, fg=FG3, width=5, anchor="e")
        self.dt_pct.pack(side="left")

        r2 = tk.Frame(pf, bg=BG); r2.pack(fill="x")
        tk.Label(r2, text="本月", font=("Segoe UI",8), bg=BG, fg=FG3, width=4, anchor="w").pack(side="left")
        self.dm_cv = tk.Canvas(r2, width=190, height=8, bg=BG3, highlightthickness=0)
        self.dm_cv.pack(side="left", padx=4)
        self.dm_pct = tk.Label(r2, text="0%", font=("Consolas",8), bg=BG, fg=FG3, width=5, anchor="e")
        self.dm_pct.pack(side="left")

        # Settings button
        self.sbtn = tk.Button(self.df, text="⚙ 设置", font=("Segoe UI",8), bd=0, bg=BG2, fg=FG3,
            activebackground=BG3, activeforeground=FG2, cursor="hand2",
            command=self._open_settings)
        self.sbtn.pack(fill="x", padx=8, pady=(4,6))

        # ── Settings panel ──
        self._build_settings()

        self._tick()

        if not self.st.get("monthly_salary") or self.st["monthly_salary"] <= 0:
            self.cv.pack_forget()
            self.df.pack(fill="both", expand=True)
            self.root.geometry(f"{self.DW}x{self.DH}")
            self.detail = True
            self._open_settings()

    def _build_settings(self):
        self.sp = tk.Frame(self.root, bg=BG, padx=10, pady=6)

        def row(parent, label, default, w=8):
            f = tk.Frame(parent, bg=BG); f.pack(fill="x", pady=1)
            tk.Label(f, text=label, font=("Segoe UI",8), bg=BG, fg=FG2, width=8, anchor="w").pack(side="left")
            e = tk.Entry(f, font=("Consolas",9), bg=BG2, fg=FG, insertbackground=FG, bd=0, width=w,
                highlightthickness=1, highlightcolor="#4a9eff", highlightbackground=BG2)
            e.insert(0, str(default)); e.pack(side="left", fill="x", expand=True, ipady=2)
            return e

        self.e_sal = row(self.sp, "月薪 ¥", self.st.get("monthly_salary",0) or "")
        self.e_hrs = row(self.sp, "每日工时", self.st.get("daily_hours",8), 4)
        self.e_ls = row(self.sp, "午休开始", self.st.get("lunch_start","12:00"), 5)
        self.e_le = row(self.sp, "午休结束", self.st.get("lunch_end","13:00"), 5)
        self.e_ci = row(self.sp, "上班时间", self.st.get("clock_in_time","09:00"), 5)

        self.lbl_co = tk.Label(self.sp, text="", font=("Segoe UI",8), bg=BG, fg=GREEN)
        self.lbl_co.pack(anchor="w", padx=2, pady=(2,0))

        bf = tk.Frame(self.sp, bg=BG); bf.pack(fill="x", pady=(6,2))
        tk.Button(bf, text="保存", font=("Segoe UI",8), bd=0, bg="#4a9eff", fg="#fff",
            command=self._save, cursor="hand2", padx=4, pady=2).pack(side="left", expand=True, fill="x", padx=(0,2))
        tk.Button(bf, text="取消", font=("Segoe UI",8), bd=0, bg=BG2, fg=FG2,
            command=self._close_settings, cursor="hand2", padx=4, pady=2).pack(side="left", expand=True, fill="x", padx=(2,0))

        for e in [self.e_ci, self.e_hrs, self.e_ls, self.e_le]:
            e.bind("<KeyRelease>", lambda ev: self._update_end_time())

    def _update_end_time(self):
        try:
            ci = self.e_ci.get()
            hrs = float(self.e_hrs.get()) or 8
            ls = self.e_ls.get()
            le = self.e_le.get()
            lunch_dur = t2m(le) - t2m(ls)
            end_mins = t2m(ci) + int(hrs * 60) + max(0, lunch_dur)
            self.lbl_co.configure(text=f"→ 预计下班 {m2t(end_mins)}")
        except Exception:
            self.lbl_co.configure(text="")

    # ── Interaction ──

    def _on_press(self, e):
        self.ox = e.x; self.oy = e.y; self._dragged = False

    def _on_drag(self, e):
        dx = e.x - self.ox; dy = e.y - self.oy
        if abs(dx) > 3 or abs(dy) > 3:
            self._dragged = True
            self.root.geometry(f"+{self.root.winfo_x()+dx}+{self.root.winfo_y()+dy}")

    def _on_release(self, e):
        if not self._dragged:
            self._toggle_view()

    def _on_right(self, e):
        menu = tk.Menu(self.root, tearoff=0, bg=BG2, fg=FG2, activebackground=BG3,
                       activeforeground=FG, font=("Segoe UI", 9))
        menu.add_command(label="退出 Salary Ticker", command=self._quit)
        menu.tk_popup(e.x_root, e.y_root)

    def _quit(self):
        self.root.destroy()

    def _on_dbl(self, e):
        if self.sp_open:
            return  # 设置打开时，双击不切换模式
        if self.detail:
            self.df.pack_forget()
            self.cv.pack(fill="both", expand=True)
            self.root.geometry(f"{self.MW}x{self.MH}")
            self.detail = False
        else:
            self.cv.pack_forget()
            self.df.pack(fill="both", expand=True)
            self.root.geometry(f"{self.DW}x{self.DH}")
            self.detail = True

    def _toggle_view(self, e=None):
        self.show_month = not self.show_month
        label = "月累计" if self.show_month else "今日累计"
        self.dlbl.configure(text=f"▶ {label}")
        self.prev = ""

    def _open_settings(self):
        self.e_sal.delete(0, tk.END)
        v = self.st.get("monthly_salary", 0)
        self.e_sal.insert(0, str(int(v)) if v > 0 else "")
        self.e_hrs.delete(0, tk.END)
        self.e_hrs.insert(0, str(self.st.get("daily_hours", 8)))
        self.e_ls.delete(0, tk.END)
        self.e_ls.insert(0, self.st.get("lunch_start", "12:00"))
        self.e_le.delete(0, tk.END)
        self.e_le.insert(0, self.st.get("lunch_end", "13:00"))
        self.e_ci.delete(0, tk.END)
        self.e_ci.insert(0, self.st.get("clock_in_time", "09:00"))
        self._update_end_time()

        self.sp.pack(fill="x")
        self.sp_open = True
        w = self.DW if self.detail else self.MW
        h_base = self.DH if self.detail else self.MH
        self.root.geometry(f"{w}x{h_base + 210}")

    def _close_settings(self):
        self.sp.pack_forget()
        self.sp_open = False
        w = self.DW if self.detail else self.MW
        h = self.DH if self.detail else self.MH
        self.root.geometry(f"{w}x{h}")

    def _save(self):
        try: sal = float(self.e_sal.get())
        except ValueError: sal = 0
        if sal <= 0: self.e_sal.configure(highlightbackground="#c0392b"); return

        self.st["monthly_salary"] = sal
        try: self.st["daily_hours"] = float(self.e_hrs.get()) or 8
        except ValueError: self.st["daily_hours"] = 8
        ls = self.e_ls.get()
        le = self.e_le.get()
        if ls and ":" in ls: self.st["lunch_start"] = ls
        if le and ":" in le: self.st["lunch_end"] = le
        ci = self.e_ci.get()
        if ci and ":" in ci: self.st["clock_in_time"] = ci
        save_settings(self.st)
        self._close_settings()
        self.prev = ""

    # ── Tick ──

    def _tick(self):
        self._update()
        self.root.after(1000, self._tick)

    def _lc(self, a, b, t):
        return (int(a[0]+(b[0]-a[0])*t), int(a[1]+(b[1]-a[1])*t), int(a[2]+(b[2]-a[2])*t))

    def _update(self):
        daily = calc_daily(self.st)
        monthly = calc_monthly(self.st)
        val = monthly if self.show_month else daily
        fmt = f"¥{val:,.2f}"
        tp = today_pct(self.st)
        mp = month_pct(self.st)
        # 切换月累计时进度条也跟着变
        bg_pct = mp if self.show_month else tp
        working = is_working(self.st)
        lunch = is_lunch(self.st)
        label = "月" if self.show_month else "日"

        ws = get_work_start(self.st)
        we = get_work_end(self.st)

        if not self.detail:
            self._draw_bg(self.cv, bg_pct, self.MW, self.MH)
            if fmt != self.prev:
                self.cv.itemconfig(self.txt, text=fmt)
                self.cv.itemconfig(self.hint, text=label)
                self.prev = fmt
                bb = self.cv.bbox(self.txt)
                if bb:
                    cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2
                    ck=int(val/1000)
                    if ck>self.pk and self.pk>0: self.ps.burst(cx,cy,8)
                    elif working: self.ps.emit(cx,cy,2)
                    self.pk=ck
            # 午休中显示橙色，工作中绿色
            if lunch:
                self.cv.itemconfig(self.dot, fill=ORANGE)
            elif working:
                self.cv.itemconfig(self.dot, fill=GREEN)
            else:
                self.cv.itemconfig(self.dot, fill="#333350")
        else:
            self._draw_bg(self.dcv, bg_pct, self.DW-16, 40)
            if fmt != self.prev:
                self.dcv.itemconfig(self.dtxt, text=fmt)
                self.prev = fmt
                bb = self.dcv.bbox(self.dtxt)
                if bb:
                    cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2
                    ck=int(val/1000)
                    if ck>self.pk and self.pk>0: self.dps.burst(cx,cy,8)
                    elif working: self.dps.emit(cx,cy,2)
                    self.pk=ck

            if lunch:
                self.dcv.itemconfig(self.ddot, fill=ORANGE)
            elif working:
                self.dcv.itemconfig(self.ddot, fill=GREEN)
            else:
                self.dcv.itemconfig(self.ddot, fill="#333350")

            self.dtime.configure(text=datetime.now().strftime("%H:%M:%S"))
            self.dwork.configure(text=f"⏰ {m2t(ws)} - {m2t(we)}  午休 {self.st.get('lunch_start','12:00')}-{self.st.get('lunch_end','13:00')}")

            # Countdown
            cd_text, cd_color = get_countdown(self.st)
            self.dcountdown.configure(text=cd_text, fg=cd_color)

            self._draw_bar(self.dt_cv, tp, 190, 8)
            self.dt_pct.configure(text=f"{int(tp*100)}%")
            self._draw_bar(self.dm_cv, mp, 190, 8)
            self.dm_pct.configure(text=f"{int(mp*100)}%")

    def _draw_bg(self, cv, frac, w, h):
        cv.delete("bg")
        fw = max(0, frac * w)
        if fw < 2: return
        self.gp = (self.gp + 0.08) % (2*math.pi)
        pu = 0.88 + 0.12 * math.sin(self.gp)
        sw = 3
        for x in range(0, int(fw), sw):
            r = x / max(1, w)
            cr,cg,cb = self._lc(A_S, A_E, r)
            pr=min(255,int(cr*pu)); pg=min(255,int(cg*pu)); pb=min(255,int(cb*pu))
            cv.create_rectangle(x,0,x+sw,h, fill=f"#{pr:02x}{pg:02x}{pb:02x}", outline="", tags="bg")
        # Leading edge glow (soft fade, no hard line)
        for i in range(8):
            a=0.4*(1.0-i/8); gx=int(fw)+i
            if gx<w:
                cr,cg,cb=self._lc(A_S,A_E,min(1,fw/w))
                gr=min(255,int(cr*a)); gg=min(255,int(cg*a)); gb=min(255,int(cb*a))
                cv.create_line(gx,0,gx,h, fill=f"#{gr:02x}{gg:02x}{gb:02x}", tags="bg")
        cv.tag_lower("bg")

    def _draw_bar(self, cv, frac, w, h):
        cv.delete("all")
        cv.create_rectangle(1,1,w-1,h-1, fill=BG3, outline="")
        fw=max(0,frac*(w-2))
        if fw<1: return
        for i in range(int(fw)):
            r=i/max(1,w); cr,cg,cb=self._lc(A_S,A_E,r)
            cv.create_line(i+1,2,i+1,h-2, fill=f"#{cr:02x}{cg:02x}{cb:02x}")
        self.gp=(self.gp+.05)%(2*math.pi)
        a=.3+.3*math.sin(self.gp)
        gr=min(255,int(100*a+30)); gg=min(255,int(220*a+30)); gb=min(255,int(255*a+30))
        cv.create_rectangle(0,0,fw+1,h, fill="", outline=f"#{gr:02x}{gg:02x}{gb:02x}", width=1)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()