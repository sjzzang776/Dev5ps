"""Dev5ps server-query/filtered_func.calculate_statics 를 DB 없이 검증한다.
- shared.connect_db.engine 과 pd.read_sql 만 가짜로 바꿔, 원본 함수 코드를 그대로 실행
"""
import sys, types, json, math
import pandas as pd

REPO = sys.argv[1]
fake = types.ModuleType("shared.connect_db"); fake.engine = None
sys.modules["shared"] = types.ModuleType("shared"); sys.modules["shared.connect_db"] = fake
sys.path.insert(0, REPO + "/server-query")
import filtered_func as ff

class _Conn:
    def __enter__(self): return self
    def __exit__(self, *a): return False
ff.engine = types.SimpleNamespace(connect=lambda: _Conn())

def run(rows, label):
    df = pd.DataFrame(rows)
    ff.pd.read_sql = lambda *a, **k: df.copy()
    out = ff.calculate_statics()
    bad = [k for k, v in out.items() if isinstance(v, float) and (math.isnan(v) or math.isinf(v))]
    try:
        json.dumps(out, allow_nan=False); js = "JSON 가능"
    except ValueError as e:
        js = f"JSON 불가({e})"
    print(f"\n[{label}]")
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items() if k in
           ("total_count", "tp_rate", "mdd", "high_time", "low_time", "final_profit_rate", "profit_std", "loss_mean")})
    print("NaN 항목:", bad or "없음", "|", js)
    return out

def trades(rates, start="2024-01-01"):
    eq, rows = 1.0, []
    for i, r in enumerate(rates):
        eq *= 1 + r / 100
        rows.append({"entry_time": pd.Timestamp(start, tz="UTC") + pd.Timedelta(days=i),
                     "result": "TP" if r > 0 else "SL", "profit_rate": r, "cum_profit_rate": (eq - 1) * 100})
    return rows

# 1) MDD: 퍼센트포인트 낙폭이 가장 큰 구간 vs 비율 낙폭이 가장 큰 구간이 다를 때
#    자산 1.0 → 0.4(−60%) → 4.0 → 3.0(−25%)
r1 = trades([-60, 900, -25])
out1 = run(r1, "MDD 검증: 앞쪽 −60% 낙폭, 뒤쪽 −25% 낙폭")
eq = pd.Series([1] + [1 + x["cum_profit_rate"] / 100 for x in r1])
true_mdd = ((eq - eq.cummax()) / eq.cummax()).min() * 100
print(f"정답 MDD(자산 기준) = {true_mdd:.1f}%  /  코드 결과 = {out1['mdd']:.1f}%")

# 2) 익절(TP)이 1번뿐이면 표준편차가 NaN → `NaN or 0.0`은 NaN 그대로
run(trades([4.0, -2.0, -2.0]), "TP 1건뿐일 때")

# 3) 행 순서: SELECT * 에 ORDER BY가 없어 순서가 바뀌면 MDD 시점이 바뀌는지
r3 = trades([-60, 900, -25])
run(list(reversed(r3)), "같은 거래, 행 순서만 반대로 읽힌 경우")
