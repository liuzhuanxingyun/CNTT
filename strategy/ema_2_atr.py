import os
import pandas as pd
import datetime
from typing import Optional, Dict, Any, List, Tuple
import threading
import queue

from backtesting import Backtest, Strategy as BTStrategy
import numpy as np

from tool.dataDeal import clean_csv_to_backtesting

def _log_to_queue(log_queue: Optional[queue.Queue], msg: str):
    """如果提供了队列，则向其发送日志消息。"""
    if log_queue:
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        log_queue.put(f'[{ts}] {msg}')
    else:
        print(msg)

# --- 核心策略逻辑 ---

class CustomStrategy(BTStrategy):
    """
    基于 backtesting.py 的策略实现。
    EMA+ATR通道突破策略。
    """
    ema_period: int = 38
    atr1: float = 1.0
    atr2: float = 2.0

    def init(self):
        self.ema = self.I(lambda x: pd.Series(x).ewm(span=self.ema_period, adjust=False).mean(), self.data.Close)

        def atr_func(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
            h_l = high - low
            h_pc = np.abs(high - np.roll(close, 1))
            l_pc = np.abs(low - np.roll(close, 1))
            tr = np.maximum.reduce([h_l, h_pc, l_pc])
            return pd.Series(tr).rolling(window=self.ema_period, min_periods=1).mean().values

        self.atr = self.I(atr_func, self.data.High, self.data.Low, self.data.Close)

    def next(self):
        if len(self.data.Close) < 3:
            return

        atr_prev = float(self.atr[-2])
        atr2_val = float(self.atr2) * float(self.atr[-3])
        upper2 = float(self.ema[-3]) + atr2_val
        lower2 = float(self.ema[-3]) - atr2_val

        k2_open = float(self.data.Open[-3]); k2_close = float(self.data.Close[-3]); k2_high = float(self.data.High[-3]); k2_low = float(self.data.Low[-3]); k2_vol = float(self.data.Volume[-3])
        k1_open = float(self.data.Open[-2]); k1_close = float(self.data.Close[-2]); k1_vol = float(self.data.Volume[-2])
        k1_low = float(self.data.Low[-2]); k1_high = float(self.data.High[-2])
        k0_close = float(self.data.Close[-1])

        long_break = k2_high > upper2
        short_break = k2_low < lower2

        k2_bull = k2_close > k2_open
        k2_bear = k2_close < k2_open
        long_color = long_break and k2_bull
        short_color = short_break and k2_bear

        k1_bull = k1_close > k1_open
        k1_bear = k1_close < k1_open
        long_reverse = long_color and k1_bear
        short_reverse = short_color and k1_bull

        vol_ok = k1_vol <= k2_vol / 2

        if long_break and long_color and long_reverse and vol_ok:
            sl = float(self.ema[-2]) - atr_prev * float(self.atr1)
            entry = k0_close
            tp = entry + (entry - sl)
            if sl < entry < tp:
                self.buy(sl=sl, tp=tp)
        elif short_break and short_color and short_reverse and vol_ok:
            sl = float(self.ema[-2]) + atr_prev * float(self.atr1)
            entry = k0_close
            tp = entry - (sl - entry)
            if tp < entry < sl:
                self.sell(sl=sl, tp=tp)

# --- 回测应用封装 ---

def apply_backtest(df: pd.DataFrame, ema_period: int, atr1: float, atr2: float, cash: int = 100000, plot: bool = True, stop_event: Optional[threading.Event] = None) -> Optional[Tuple[Dict[str, Any], pd.DataFrame]]:
    """
    使用 backtesting 库回测策略并返回统计结果和交易记录。
    """
    def make_strategy(ema_period: int, atr1: float, atr2: float):
        class ParamStrategy(CustomStrategy):
            pass
        ParamStrategy.ema_period = ema_period
        ParamStrategy.atr1 = atr1
        ParamStrategy.atr2 = atr2
        return ParamStrategy

    df2 = df.copy()
    if 'Date' in df2.columns:
        df2.index = pd.to_datetime(df2['Date'])
        df2 = df2.drop(columns=['Date'])

    try:
        max_price = max(df2['High'].max(), df2['Close'].max())
        if cash < max_price * 10:
            cash = max(cash, int(max_price * 100))
    except Exception:
        pass

    bt = Backtest(df2, make_strategy(ema_period, atr1, atr2), cash=cash)
    try:
        # 注意：backtesting.py 本身不支持在 .run() 中中止，
        # 这里的 stop_event 主要用于在外层循环中提前终止。
        if stop_event and stop_event.is_set():
            return None, pd.DataFrame()
        output = bt.run()
        stats = output
        trades = output._trades
    except Exception as e:
        print(f'回测出错: ema={ema_period}, atr1={atr1}, atr2={atr2}, error={e}')
        return None, pd.DataFrame()

    if plot:
        bt.plot()

    return stats, trades

# --- 执行器 ---

def run_single_backtest(
    csv_name: str, 
    ema_period: int, 
    atr1: float, 
    atr2: float, 
    plot: bool = False, 
    save_trades: bool = False,
    stop_event: Optional[threading.Event] = None,
    log_queue: Optional[queue.Queue] = None
) -> Optional[Dict[str, Any]]:
    """
    执行单次回测。
    """
    _log_to_queue(log_queue, f"开始处理: EMA={ema_period}, ATR1={atr1}, ATR2={atr2}")
    input_path = f'data/no/{csv_name}.csv'
    output_dir = 'data/ok'
    cleaned_name = f'{csv_name}-ok.csv'
    cleaned_path = os.path.join(output_dir, cleaned_name)

    if not os.path.isfile(cleaned_path):
        try:
            if stop_event and stop_event.is_set(): return None
            _log_to_queue(log_queue, f"清洗数据: {input_path}")
            temp_cleaned = clean_csv_to_backtesting(input_path, output_dir)
            os.rename(temp_cleaned, cleaned_path)
            _log_to_queue(log_queue, f'数据清洗完成: {cleaned_path}')
        except Exception as e:
            _log_to_queue(log_queue, f'数据清洗失败: {e}')
            return None
    
    try:
        if stop_event and stop_event.is_set(): return None
        df = pd.read_csv(cleaned_path)
    except Exception as e:
        _log_to_queue(log_queue, f'读取清洗数据失败: {e}')
        return None

    if stop_event and stop_event.is_set(): return None
    stats, trades = apply_backtest(df, ema_period, atr1, atr2, plot=plot, stop_event=stop_event)

    if stats is not None and save_trades and trades is not None and not trades.empty:
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'trades_{csv_name}_ema{ema_period}_atr{atr1}-{atr2}_{ts}.csv'
        output_path = os.path.join('result', 'once', filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        trades.to_csv(output_path)
        _log_to_queue(log_queue, f"交易记录已保存: {os.path.abspath(output_path)}")

    return stats

def run_batch_backtest(
    csv_name: str, 
    ema_range: List[int], 
    atr1_range: List[float], 
    atr2_range: List[float], 
    plot: bool = False, # 这个plot参数实际上没有被使用
    save_summary: bool = True,
    stop_event: Optional[threading.Event] = None,
    log_queue: Optional[queue.Queue] = None
):
    """
    执行批量回测。
    """
    results = []
    total = len(ema_range) * len(atr1_range) * len(atr2_range)
    _log_to_queue(log_queue, f'准备运行 {total} 次组合回测...')

    count = 0
    start_time = datetime.datetime.now()

    for ema_period in ema_range:
        for atr1 in atr1_range:
            for atr2 in atr2_range:
                if stop_event and stop_event.is_set():
                    _log_to_queue(log_queue, "批量回测被中止。")
                    return

                count += 1
                
                # 时间预测
                if count > 1:
                    elapsed = datetime.datetime.now() - start_time
                    avg_time_per_run = elapsed / (count - 1)
                    remaining_runs = total - count + 1
                    eta = avg_time_per_run * remaining_runs
                    # 将 eta 转换为更易读的格式
                    eta_str = str(datetime.timedelta(seconds=int(eta.total_seconds())))
                    status_msg = f'[{count}/{total}] EMA={ema_period}, ATR1={atr1}, ATR2={atr2} | 预计剩余: {eta_str}'
                else:
                    status_msg = f'[{count}/{total}] EMA={ema_period}, ATR1={atr1}, ATR2={atr2}'
                
                _log_to_queue(log_queue, status_msg)

                stats = run_single_backtest(
                    csv_name, ema_period, atr1, atr2, 
                    plot=False, save_trades=False, # 批量回测中不绘图、不单独保存交易
                    stop_event=stop_event, log_queue=None # 子调用不直接写队列
                )
                if stats is not None:
                    # 将Series转换为dict
                    stats_dict = stats.to_dict()
                    stats_dict['ema_period'] = ema_period
                    stats_dict['atr1'] = atr1
                    stats_dict['atr2'] = atr2
                    results.append(stats_dict)

    if results and save_summary:
        df_result = pd.DataFrame(results)
        columns = ['ema_period', 'atr1', 'atr2', 'Equity Final [$]', 'Return [%]', '# Trades', 'Win Rate [%]']
        existing_cols = [c for c in columns if c in df_result.columns]
        df_simple = df_result[existing_cols]
        
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'result/many/grid_summary_{ts}.csv'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_simple.to_csv(output_path, index=False)
        _log_to_queue(log_queue, f'批量回测结果已保存: {os.path.abspath(output_path)}')
    elif not (stop_event and stop_event.is_set()):
        _log_to_queue(log_queue, '没有有效的回测结果。')

# --- 主函数入口 ---

def main():
    """
    主函数，用于直接运行脚本进行测试。
    可以修改这里的配置来进行单次或批量测试。
    """
    # --- 单次回测配置 ---
    # print("--- 执行单次回测 ---")
    # single_stats = run_single_backtest(
    #     csv_name='btc_usdt_24-至今',
    #     ema_period=9,
    #     atr1=3.0,
    #     atr2=3.0,
    #     plot=True,
    #     save_trades=True
    # )
    # if single_stats:
    #     print(single_stats)

    # --- 批量回测配置 ---
    print("\n--- 执行批量回测 ---")
    run_batch_backtest(
        csv_name='btc_usdt_24-至今',
        ema_range=range(10, 21, 5), # 示例: 10, 15, 20
        atr1_range=[1.0, 1.5],
        atr2_range=[2.0, 2.5],
        plot=False
    )

if __name__ == '__main__':
    main()
