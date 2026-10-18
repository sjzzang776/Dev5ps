"""run_conditional_lateral_backtest 의 SQL 논리를 pandas로 그대로 옮겨, 진입이 겹치는지 확인한다.
SQL: 조건을 만족하고 close > low*1.005 인 '모든' 봉을 진입으로 보고,
     각 진입마다 그 뒤 첫 봉 중 low <= SL 또는 high >= TP 인 봉을 청산으로 잡는다(이전 포지션 보유 여부 확인 없음).
"""
import pandas as pd

# 8개 봉. 1~3번 봉이 모두 조건 만족(예: rsi < 30이 3봉 연속)
bars = pd.DataFrame({
    "t":     [0, 1, 2, 3, 4, 5, 6, 7],
    "close": [100, 101, 102, 103, 104, 106, 108, 110],
    "low":   [99, 98, 99, 100, 101, 103, 105, 107],
    "high":  [101, 102, 103, 104, 105, 107, 109, 111],
    "cond":  [False, True, True, True, False, False, False, False],   # 예: ema_7 > ema_25 가 3봉 연속 참
})
rr = 2.0
rows = []
for _, e in bars[bars.cond & (bars.close > bars.low * 1.005)].iterrows():
    tp = e.close + (e.close - e.low) * rr
    after = bars[bars.t > e.t]
    hit = after[(after.low <= e.low) | (after.high >= tp)].head(1)
    x = hit.iloc[0] if len(hit) else None
    res = "OPEN" if x is None else ("SL" if x.low <= e.low else "TP")
    pr = 0.0 if res == "OPEN" else ((tp if res == "TP" else e.low) - e.close) / e.close * 100
    rows.append({"entry_t": e.t, "exit_t": None if x is None else x.t, "result": res, "profit_rate%": round(pr, 2)})
df = pd.DataFrame(rows)
df["cum%"] = (((1 + df["profit_rate%"] / 100).cumprod()) - 1) * 100
print(df.to_string(index=False))
open_at_entry = [int(((df.entry_t < r.entry_t) & (df.exit_t > r.entry_t)).sum()) for r in df.itertuples()]
print("각 진입 시점에 이미 열려 있던 포지션 수:", open_at_entry)
print("→ 같은 기간에 포지션이 겹쳐도 누적수익률은 순서대로 곱해져, 실제로 한 계좌로 거래했을 때와 다르다")
