"""웹 데모용 데이터(btcusdt_1h.json)를 만든다.

    python docs/demo/build_data.py     # 저장소 루트에서 실행

docs/figures/data/btcusdt_1h.csv(고정 시세)에 팀 코드(server-collect_data/indicators)로 지표를 계산해
브라우저가 바로 읽을 수 있는 열(column) 배열 JSON으로 저장한다.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "docs" / "figures"))
sys.path.insert(0, str(ROOT / "server-collect_data"))
from make_figures import load_btc_1h  # noqa: E402  (팀 지표 계산 포함)

COLS = ["open", "high", "low", "close", "volume", "rsi", "rsi_signal", "ema_7", "ema_25", "ema_99",
        "macd", "macd_signal", "boll_ma", "boll_upper", "boll_lower", "volume_ma_20"]

df = load_btc_1h()
out = {"symbol": "BTCUSDT", "interval": "1h",
       "t": [int(ts.timestamp() * 1000) for ts in df.timestamp]}
for c in COLS:
    out[c] = [None if v != v else round(float(v), 4) for v in df[c]]
(HERE / "btcusdt_1h.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
print(len(df), "rows ->", HERE / "btcusdt_1h.json")
