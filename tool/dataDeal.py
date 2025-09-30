"""
dataDeal.py

数据清洗工具：把交易所原始 kline CSV（例如 Binance）转换为回测库可读的格式。

主要功能：
 - 自动识别时间列（open_time 或 timestamp 等常见字段）
 - 将时间戳转换为标准字符串 Date（%Y-%m-%d %H:%M:%S）
 - 保留列：Date, Open, High, Low, Close, Volume
"""

import os
from typing import Optional, Sequence

import pandas as pd


def _find_time_column(columns: Sequence[str]) -> Optional[str]:
    """在列名中尝试找到一个时间戳列的候选名。"""
    candidates = ['open_time', 'timestamp', 'time', 'date', 'OpenTime']
    for c in candidates:
        if c in columns:
            return c
    # 没找到返回 None
    return None


def clean_csv_to_backtesting(input_path: str, output_dir: str, time_col: Optional[str] = None) -> Optional[str]:
    """将交易所 CSV 清洗为回测格式并写到 output_dir，返回写入路径。

    参数:
      - input_path: 源 CSV 路径
      - output_dir: 输出目录
      - time_col: 如果明确知道时间列名可传入，否则自动检测
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    os.makedirs(output_dir, exist_ok=True)

    # 读取 CSV，允许较大的文件
    df = pd.read_csv(input_path)

    # 自动检测时间列
    if time_col is None:
        time_col = _find_time_column(df.columns)
    if time_col is None:
        raise ValueError("无法识别时间列，请提供 time_col 参数")

    # 将时间戳转换为 datetime，优先尝试毫秒级(ms)，失败再尝试秒级(s)
    try:
        df['Date'] = pd.to_datetime(df[time_col], unit='ms', utc=True)
    except Exception:
        df['Date'] = pd.to_datetime(df[time_col], unit='s', utc=True)

    # 需要的列映射
    col_map = {
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }

    missing = [c for c in col_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必要行情列: {missing}")

    out_df = df[['Date'] + list(col_map.keys())].copy()
    out_df = out_df.rename(columns=col_map)
    out_df['Date'] = out_df['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')

    base = os.path.basename(input_path)
    name, _ = os.path.splitext(base)
    out_path = os.path.join(output_dir, f"{name}_cleaned.csv")
    out_df.to_csv(out_path, index=False)
    return out_path
