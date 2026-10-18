"""README 그림을 직접 만든다(발표 자료 이미지를 쓰지 않음).

    python docs/figures/make_figures.py            # 저장소 루트에서 실행 (Edge 또는 Chrome 필요)
    python docs/figures/make_figures.py --refetch  # Binance에서 시세를 다시 받아 data/btcusdt_1h.csv 갱신

만드는 그림 (docs/img/):
  fig_architecture.png   서비스 구조도
  fig_backtest_rule.png  실제 BTC 1시간 봉에서 진입·손절·익절·청산 한 건
  fig_backtest_demo.png  팀 코드와 같은 규칙: 신호마다 진입 vs 한 번에 한 포지션
  fig_data_used.txt      그림에 쓴 데이터 구간·전략·통계 (재현용 기록)

시세는 docs/figures/data/btcusdt_1h.csv(Binance BTCUSDT 1h, 2026-10-18 07:00 UTC까지 5,000개)에 고정해 둔다.
지표 계산은 팀 코드(server-collect_data/indicators)를 그대로 import 해서 쓰고,
진입·청산 규칙은 server-query/filtered_func.py 의 SQL 과 같은 규칙을 pandas 로 옮겼다.
스타일·렌더러: figstyle.py
"""
import json, sys, time, urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs" / "img"
DATA = HERE / "data" / "btcusdt_1h.csv"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "server-collect_data"))
from figstyle import page, render                      # noqa: E402
from indicators.calculate import calculate_indicators  # noqa: E402  팀 코드

W = 1240
STRATEGY = "rsi > 70 and ema_7 > ema_25"
RR = 2.0
END_UTC = "2026-10-18 07:00"


def _marker(mid, color, size=7):
    return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="{size}" markerHeight="{size}" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')


# ------------------------------------------------------------------ 1. 구조도
ICONS = HERE / "icons"        # Simple Icons 13.21.0 (CC0-1.0), 로고는 각 상표권자 소유
BRAND = {"git": "#F05032", "githubactions": "#2088FF", "docker": "#2496ED", "amazonec2": "#FF9900",
         "binance": "#F0B90B", "python": "#3776AB", "postgresql": "#4169E1", "fastapi": "#009688",
         "streamlit": "#FF4B4B"}


def _logo(name, cx, cy, size, color=None):
    """Simple Icons의 24x24 path를 (cx, cy) 중심, size 크기로 그린다."""
    import re
    d = re.search(r'<path d="([^"]+)"', (ICONS / f"{name}.svg").read_text(encoding="utf-8")).group(1)
    k = size / 24
    return (f'<path d="{d}" fill="{color or BRAND[name]}" '
            f'transform="translate({cx - size/2:.1f},{cy - size/2:.1f}) scale({k:.4f})"/>')


def _person(cx, cy, size, color="#14202B"):
    r = size * 0.2
    return (f'<circle cx="{cx}" cy="{cy - size*0.2}" r="{r}" fill="{color}"/>'
            f'<path d="M{cx - size*0.36},{cy + size*0.38} a{size*0.36},{size*0.34} 0 0 1 {size*0.72},0 z" fill="{color}"/>')


def _tile(cx, cy, s, inner, mine=False):
    fill, stroke, sw = ("#E8EDFD", "#2B50E0", 2.4) if mine else ("#FFFFFF", "#D3DAE1", 1.4)
    return (f'<rect x="{cx - s/2}" y="{cy - s/2}" width="{s}" height="{s}" rx="{s*0.24:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>' + inner)


def _label(cx, y, title, lines, color="#14202B"):
    s = f'<text x="{cx}" y="{y}" text-anchor="middle" font-size="15.5" font-weight="700" fill="{color}">{title}</text>'
    for k, ln in enumerate(lines):
        s += f'<text x="{cx}" y="{y + 21 + k*17}" text-anchor="middle" font-size="12.5" fill="#5A6876">{ln}</text>'
    return s


def _wire(x1, y1, x2, y2, label="", color="#9AA6B2", mid=None, dash=""):
    mx = (x1 + x2) / 2
    path = f"M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}" if y1 != y2 else f"M{x1},{y1} L{x2},{y2}"
    s = (f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2" marker-end="url(#ar{color[1:]})"'
         + (f' stroke-dasharray="{dash}"' if dash else "") + '/>')
    if label:
        lx, ly = mid or (mx, min(y1, y2) - 9)
        s += f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="12" fill="#5A6876">{label}</text>'
    return s


def fig_architecture():
    W2, H2 = 1152, 492
    yd, y, T, t = 70, 330, 72, 56          # 배포 선, 데이터 선, 데이터 타일 크기, 배포 타일 크기
    defs = "".join(_marker(f"ar{c[1:]}", c, 6) for c in ("#9AA6B2", "#2B50E0"))
    s = [f'<svg width="{W2}" height="{H2}" viewBox="0 0 {W2} {H2}"><defs>{defs}</defs>']
    # EC2 영역
    s.append('<rect x="196" y="188" width="872" height="288" rx="18" fill="#F7F9FB" stroke="#C9D2DA" stroke-width="1.4"/>')
    s.append(_logo("amazonec2", 226, 216, 22))
    s.append('<text x="246" y="221" font-size="13.5" font-weight="700" fill="#5A6876">AWS EC2 · Docker Compose 서비스 4개</text>')
    # 배포 선
    dep = [(330, "git", "git push", "main 브랜치"), (560, "githubactions", "GitHub Actions", "test → build → deploy"),
           (790, "docker", "Docker Hub", "이미지 3개")]
    for (x1, *_), (x2, *_) in zip(dep, dep[1:]):
        s.append(_wire(x1 + t/2 + 6, yd, x2 - t/2 - 8, yd))
    s.append(_wire(790 + t/2 + 6, yd, 930, 186, "pull, up -d", mid=(905, 112)))
    for x, ic, title, sub in dep:
        s.append(_tile(x, yd, t, _logo(ic, x, yd, 30)))
        s.append(_label(x, yd + t/2 + 22, title, [sub]))
    # 데이터 선
    st = [(150, "binance", "Binance", ["공개 시세 API"], False),
          (330, "python", "collect_data", ["60초마다 수집", "보조지표 계산"], False),
          (530, "postgresql", "PostgreSQL 15", ["코인·간격별 테이블"], False),
          (750, "fastapi", "query", ["API 11개", "조건식 백테스트·통계"], True),
          (960, "streamlit", "frontend", ["전략 입력·차트", "수익률·통계 화면"], True)]
    xs = [p[0] for p in st]
    s.append(_wire(xs[0] + T/2 + 6, y, xs[1] - T/2 - 8, y, "캔들"))
    s.append(_wire(xs[1] + T/2 + 6, y, xs[2] - T/2 - 8, y, "upsert"))
    s.append(_wire(xs[3] - T/2 - 6, y, xs[2] + T/2 + 8, y, "SQL (LATERAL JOIN)", color="#2B50E0"))
    s.append(_wire(xs[4] - T/2 - 6, y, xs[3] + T/2 + 8, y, "HTTP", color="#2B50E0"))
    s.append(_wire(1098 - 26, y, xs[4] + T/2 + 8, y))
    for x, ic, title, lines, mine in st:
        s.append(_tile(x, y, T, _logo(ic, x, y, 38), mine))
        s.append(_label(x, y + T/2 + 24, title, lines, "#2B50E0" if mine else "#14202B"))
    s.append(_person(1098, y, 30, "#5A6876"))
    s.append(_label(1098, y + T/2 + 24, "사용자", ["전략 입력"]))
    # 내 담당
    s.append(f'<path d="M{xs[3]-T/2-4},{y-T/2-22} L{xs[3]-T/2-4},{y-T/2-30} L{xs[4]+T/2+4},{y-T/2-30} L{xs[4]+T/2+4},{y-T/2-22}" '
             'fill="none" stroke="#2B50E0" stroke-width="1.8"/>')
    s.append(f'<text x="{(xs[3]+xs[4])/2}" y="{y-T/2-38}" text-anchor="middle" font-size="13.5" font-weight="700" fill="#2B50E0">'
             '내 담당: 손익점 계산, 승률·기대수익·MDD 통계 API와 화면</text>')
    s.append('</svg>')
    body = ('<div class="frame"><div class="title">Binance 시세를 60초마다 모으고, 사용자가 고른 조건으로 과거 매매를 다시 계산해 보여 준다</div>'
            '<div class="lede">BTC·ETH·XRP·SOL × 15분·1시간·4시간·1일. main에 push하면 GitHub Actions가 테스트, 이미지 빌드, EC2 배포까지 진행</div>'
            '<div style="margin-top:16px">' + "".join(s) + '</div>'
            '<div class="src">로고: Simple Icons(CC0). 각 로고의 상표권은 해당 회사에 있음</div></div>')
    render(page(body, W), OUT / "fig_architecture.png", W, 670)


# ------------------------------------------------------------------ 2. 데이터
def fetch_btc_1h(n_batches=5):
    end = int(pd.Timestamp(END_UTC, tz="UTC").timestamp() * 1000) + 3_599_999
    rows = []
    for _ in range(n_batches):
        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000&endTime={end}"
        with urllib.request.urlopen(url, timeout=30) as r:
            batch = json.loads(r.read())
        rows = batch + rows
        end = batch[0][0] - 1
        time.sleep(0.3)
    df = pd.DataFrame(rows, columns=list(range(12)))
    df = pd.DataFrame({"open_time_ms": df[0].astype("int64"), "open": df[1], "high": df[2], "low": df[3],
                       "close": df[4], "volume": df[5]}).drop_duplicates("open_time_ms").tail(5000)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA, index=False)


def load_btc_1h():
    raw = pd.read_csv(DATA)
    df = pd.DataFrame({"timestamp": pd.to_datetime(raw.open_time_ms, unit="ms", utc=True),
                       "open": raw.open.astype(float), "high": raw.high.astype(float),
                       "low": raw.low.astype(float), "close": raw.close.astype(float),
                       "volume": raw.volume.astype(float)}).reset_index(drop=True)
    return calculate_indicators(df)


# ------------------------------------------------------------------ 3. 팀 규칙 그대로 백테스트
def backtest(df, cond, rr, one_position=False):
    """filtered_func.run_conditional_lateral_backtest 와 같은 규칙.
    one_position=True 이면 이전 포지션이 청산되기 전 신호는 건너뛴다(비교용)."""
    entries = df[cond & (df["close"] > df["low"] * 1.005)]
    lows, highs = df["low"].to_numpy(), df["high"].to_numpy()
    rows, busy_until = [], -1
    for i, e in entries.iterrows():
        if one_position and i <= busy_until:
            continue
        sl, tp = e["low"], e["close"] + (e["close"] - e["low"]) * rr
        hit = np.where((lows[i + 1:] <= sl) | (highs[i + 1:] >= tp))[0]
        if len(hit) == 0:
            res, j = "OPEN", None
        else:
            j = i + 1 + hit[0]
            res = "SL" if lows[j] <= sl else "TP"          # SQL CASE 와 같은 순서(손절 먼저)
        pr = 0.0 if res == "OPEN" else ((tp if res == "TP" else sl) - e["close"]) / e["close"]
        rows.append(dict(i=i, j=j, entry_time=e["timestamp"], entry=e["close"], sl=sl, tp=tp, result=res, pr=pr))
        busy_until = j if j is not None else len(df)
    out = pd.DataFrame(rows)
    out["cum"] = (1 + out["pr"]).cumprod() - 1
    return out


def stats(t):
    eq = 1 + t["cum"]
    peak = eq.cummax().clip(lower=1.0)
    closed = t[t.result != "OPEN"]
    return dict(trades=len(closed), tp=int((closed.result == "TP").sum()),
                win=float((closed.result == "TP").mean() * 100) if len(closed) else 0.0,
                final=float(t["cum"].iloc[-1] * 100) if len(t) else 0.0,
                mdd=float(((eq / peak) - 1).min() * 100) if len(t) else 0.0)


# ------------------------------------------------------------------ 4. 규칙 그림
def fig_rule(df, t):
    pick = t[t.result == "TP"].iloc[len(t[t.result == "TP"]) // 2]
    i, j = int(pick.i), int(pick.j)
    a, b = max(0, i - 12), min(len(df), j + 7)
    seg = df.iloc[a:b]
    w, h, l, r, top, bot = 1152, 400, 62, 300, 14, 40
    lo, hi = min(seg.low.min(), pick.sl), max(seg.high.max(), pick.tp)
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad
    n = b - a
    X = lambda k: l + (k - a + 0.5) / n * (w - l - r)
    Y = lambda v: top + (hi - v) / (hi - lo) * (h - top - bot)
    cw = (w - l - r) / n * 0.56
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    # 눈금
    step = 10 ** np.floor(np.log10((hi - lo) / 4))
    step = step * (2 if (hi - lo) / step > 8 else 1)
    for v in np.arange(np.ceil(lo / step) * step, hi, step):
        s.append(f'<line x1="{l}" y1="{Y(v)}" x2="{w-r}" y2="{Y(v)}" stroke="#EEF1F5"/>')
        s.append(f'<text x="{l-10}" y="{Y(v)+4}" text-anchor="end" font-size="11.5" fill="#8C98A4">{v:,.0f}</text>')
    # 보상·위험 영역
    xi, xj = X(i), X(j)
    s.append(f'<rect x="{xi}" y="{Y(pick.tp)}" width="{xj-xi}" height="{Y(pick.entry)-Y(pick.tp)}" fill="#E3F4EC"/>')
    s.append(f'<rect x="{xi}" y="{Y(pick.entry)}" width="{xj-xi}" height="{Y(pick.sl)-Y(pick.entry)}" fill="#FBE9E7"/>')
    # 캔들: 상승 = 청록, 하락 = 빨강 (심지도 같은 색)
    for k, c in seg.iterrows():
        x = X(k)
        s.append(f'<line x1="{x}" y1="{Y(c.high)}" x2="{x}" y2="{Y(c.low)}" stroke="#14202B" stroke-width="1.3"/>')
        y0, y1 = Y(max(c.open, c.close)), Y(min(c.open, c.close))
        col = "#16A383" if c.close >= c.open else "#E5484D"     # 상승 = 청록, 하락 = 빨강
        s[-1] = s[-1].replace('stroke="#14202B"', f'stroke="{col}"')
        s.append(f'<rect x="{x-cw/2}" y="{y0}" width="{cw}" height="{max(y1-y0, 1.2)}" rx="1.5" fill="{col}"/>')
    for v, col, dash in ((pick.tp, "#0F8A5F", "7 5"), (pick.sl, "#D23F37", "7 5"), (pick.entry, "#2B50E0", "")):
        s.append(f'<line x1="{xi}" y1="{Y(v)}" x2="{w-r+10}" y2="{Y(v)}" stroke="{col}" stroke-width="2.4"'
                 + (f' stroke-dasharray="{dash}"' if dash else "") + '/>')
    s.append(f'<circle cx="{xi}" cy="{Y(pick.entry)}" r="7" fill="#2B50E0" stroke="#fff" stroke-width="2"/>')
    s.append(f'<circle cx="{xj}" cy="{Y(pick.tp)}" r="7" fill="#0F8A5F" stroke="#fff" stroke-width="2"/>')
    lx = w - r + 22
    labels = [(pick.tp, "#0F8A5F", "익절선 TP", f"종가 + (종가 − 저가) × {RR:g}"),
              (pick.entry, "#2B50E0", "진입", "조건을 만족한 봉의 종가"),
              (pick.sl, "#D23F37", "손절선 SL", "그 봉의 저가")]
    ys = [Y(v) for v, *_ in labels]
    for k in range(1, 3):                     # 이름표가 겹치지 않게 아래로 밀기
        ys[k] = max(ys[k], ys[k-1] + 44)
    for (v, col, t1, t2), yy in zip(labels, ys):
        if abs(yy - Y(v)) > 2:
            s.append(f'<line x1="{w-r+10}" y1="{Y(v)}" x2="{lx-4}" y2="{yy-6}" stroke="{col}" stroke-width="1.2"/>')
        s.append(f'<text x="{lx}" y="{yy-2}" font-size="15" font-weight="700" fill="{col}">{t1}</text>')
        s.append(f'<text x="{lx}" y="{yy+16}" font-size="12.5" fill="#5A6876">{t2}</text>')
    s.append(f'<text x="{xj+12}" y="{Y(pick.tp)+20}" text-anchor="start" font-size="12.5" font-weight="700" fill="#0F8A5F">청산</text>')
    for k in (i, j):
        s.append(f'<text x="{X(k)}" y="{h-14}" text-anchor="middle" font-size="12" fill="#5A6876">'
                 f'{df.timestamp[k].tz_convert("Asia/Seoul"):%m-%d %H시}</text>')
    s.append('</svg>')
    body = ('<div class="frame"><div class="title">조건을 만족한 봉의 종가에 진입하고, 익절선과 손절선 중 먼저 닿는 쪽에서 청산한다</div>'
            f'<div class="lede">실제 BTCUSDT 1시간 봉, 조건 <span class="code">{STRATEGY}</span>, 손익비 {RR:g} '
            '(이익 폭 = 손실 폭의 2배). 내가 처음 구현한 손익점 규칙을 팀이 SQL로 옮긴 것과 같다</div>'
            '<div style="margin-top:16px">' + "".join(s) + '</div></div>')
    render(page(body, W), OUT / "fig_backtest_rule.png", W, 540)


# ------------------------------------------------------------------ 5. 진입 중복 비교
def _m(s):
    return s.replace("-", "−")


def fig_demo(df, t_all, t_one, s_all, s_one):
    w, h, l, r, top, bot = 790, 380, 56, 76, 16, 34
    t0, t1 = df.timestamp.iloc[0], df.timestamp.iloc[-1]
    vals = np.concatenate([[0], t_all.cum * 100, t_one.cum * 100])
    lo, hi = vals.min(), vals.max()
    pad = (hi - lo) * 0.08
    lo, hi = lo - pad, hi + pad
    X = lambda ts: l + (ts - t0) / (t1 - t0) * (w - l - r)
    Y = lambda v: top + (hi - v) / (hi - lo) * (h - top - bot)
    s = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for v in range(int(np.ceil(lo / 10) * 10), int(hi) + 1, 10):
        s.append(f'<line x1="{l}" y1="{Y(v)}" x2="{w-r}" y2="{Y(v)}" stroke="{"#B8C2CC" if v == 0 else "#EEF1F5"}"'
                 f' stroke-width="{1.5 if v == 0 else 1}"/>')
        s.append(f'<text x="{l-10}" y="{Y(v)+4}" text-anchor="end" font-size="11.5" fill="#8C98A4">{_m(format(v, "+d"))}%</text>'.replace("+0%", "0%"))
    for m in pd.date_range(t0.normalize() + pd.offsets.MonthBegin(1), t1, freq="MS"):
        s.append(f'<text x="{X(m)}" y="{h-10}" text-anchor="middle" font-size="11.5" fill="#8C98A4">{m.month}월</text>')
    for t, col, wd in ((t_all, "#E0700B", 2.6), (t_one, "#2B50E0", 2.6)):
        pts, prev = [f"{X(t0):.1f},{Y(0):.1f}"], 0.0
        for ts, c in zip(t.entry_time, t.cum * 100):
            pts += [f"{X(ts):.1f},{Y(prev):.1f}", f"{X(ts):.1f},{Y(c):.1f}"]
            prev = c
        pts.append(f"{X(t1):.1f},{Y(prev):.1f}")
        s.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="{wd}" stroke-linejoin="round"/>')
    for st, col in ((s_all, "#E0700B"), (s_one, "#2B50E0")):
        s.append(f'<text x="{w-r+8}" y="{Y(st["final"])+5}" font-size="15" font-weight="800" fill="{col}">{_m(format(st["final"], "+.1f"))}%</text>')
    s.append('</svg>')
    tb = ('<table class="st"><tr><th></th><th style="color:#E0700B">신호마다 진입<br><span>팀 코드 규칙</span></th>'
          '<th style="color:#2B50E0">한 번에 한 포지션<br><span>보유 중 신호는 건너뜀</span></th></tr>'
          f'<tr><td>청산된 거래</td><td>{s_all["trades"]}회</td><td>{s_one["trades"]}회</td></tr>'
          f'<tr><td>승률</td><td>{s_all["win"]:.1f}%</td><td>{s_one["win"]:.1f}%</td></tr>'
          f'<tr><td>최종 수익률</td><td class="big" style="color:#E0700B">{_m(format(s_all["final"], "+.1f"))}%</td>'
          f'<td class="big" style="color:#2B50E0">{_m(format(s_one["final"], "+.1f"))}%</td></tr>'
          f'<tr><td>MDD (비율)</td><td>{_m(format(s_all["mdd"], ".1f"))}%</td><td>{_m(format(s_one["mdd"], ".1f"))}%</td></tr></table>'
          '<p class="why">신호가 연달아 나오면 팀 코드는 이미 보유 중이어도 또 진입한다. '
          '한 계좌로는 불가능한 동시 포지션이 수익률에 섞여, 같은 전략의 결론이 뒤집힌다.</p>')
    css = ('<style>.row{display:flex;gap:28px;margin-top:16px;align-items:flex-start}'
           '.st{border-collapse:collapse;font-size:14px;width:330px;margin-top:8px}.st th{font-size:13.5px;text-align:right;padding:6px 0 10px 12px;'
           'vertical-align:bottom;line-height:1.35}.st th span{font-size:11.5px;color:#8C98A4;font-weight:400}'
           '.st td{padding:9px 0 9px 12px;text-align:right;border-top:1px solid #D9DFE6}.st td:first-child{text-align:left;color:#5A6876;padding-left:0}'
           '.st td.big{font-size:20px;font-weight:800}.why{font-size:13px;color:#5A6876;line-height:1.6;margin:14px 0 0;width:330px}</style>')
    span = f"{df.timestamp.iloc[0]:%Y-%m-%d} ~ {df.timestamp.iloc[-1]:%Y-%m-%d}"
    body = (css + '<div class="frame"><div class="title">같은 규칙인데 진입이 겹치게 두면 +29.1%, 한 번에 한 포지션만 잡으면 −4.5%</div>'
            f'<div class="lede">BTCUSDT 1시간 봉 {len(df):,}개({span}), 조건 <span class="code">{STRATEGY}</span>, 손익비 {RR:g}, '
            '수수료 미반영. 그래프는 누적수익률</div>'
            f'<div class="row"><div>{"".join(s)}</div><div>{tb}</div></div></div>')
    render(page(body, W), OUT / "fig_backtest_demo.png", W, 530)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if "--refetch" in sys.argv or not DATA.exists():
        fetch_btc_1h()
    fig_architecture()
    df = load_btc_1h()
    cond = (df["rsi"] > 70) & (df["ema_7"] > df["ema_25"])
    t_all = backtest(df, cond, RR)
    t_one = backtest(df, cond, RR, one_position=True)
    s_all, s_one = stats(t_all), stats(t_one)
    fig_rule(df, t_all)
    fig_demo(df, t_all, t_one, s_all, s_one)
    span = f"{df.timestamp.iloc[0]:%Y-%m-%d} ~ {df.timestamp.iloc[-1]:%Y-%m-%d}, 1시간 봉 {len(df):,}개"
    (OUT / "fig_data_used.txt").write_text(
        f"데이터: Binance BTCUSDT 1h, {span} (docs/figures/data/btcusdt_1h.csv)\n전략: {STRATEGY}, 손익비 {RR}\n"
        f"신호마다 진입: {json.dumps(s_all, ensure_ascii=False)}\n한 포지션만: {json.dumps(s_one, ensure_ascii=False)}\n",
        encoding="utf-8")
    print(span); print("all", s_all); print("one", s_one)
