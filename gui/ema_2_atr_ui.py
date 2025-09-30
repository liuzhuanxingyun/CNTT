from typing import Dict, Any, Tuple
import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox

from gui.base_ui import BaseStrategyUI

class EmaAtrUI(BaseStrategyUI):
    """
    EMA + 2 ATR 策略的UI界面。
    这个类现在负责将自己的选项卡添加到传递给它的 master (notebook) 中。
    """
    def __init__(self, master: ttk.Notebook):
        super().__init__(master)
        self.create_frames()
        
        # 将创建的框架作为选项卡添加到 master (notebook)
        self.master.add(self.single_frame, text='  单次回测  ')
        self.master.add(self.grid_frame, text='  范围回测  ')

    def create_frames(self):
        """创建单次回测和范围回测的参数Frame。"""
        
        # --- 单次回测UI ---
        # 注意：这里的父级现在是 master (notebook)，而不是一个中间容器
        single_tab = ttk.Frame(self.master, padding=15)
        
        ttk.Label(single_tab, text='EMA 周期:').grid(row=0, column=0, sticky='w', pady=5)
        self.ema_entry = ttk.Entry(single_tab, width=12)
        self.ema_entry.insert(0, '9')
        self.ema_entry.grid(row=0, column=1, sticky='w', pady=5)

        ttk.Label(single_tab, text='ATR1 倍数:').grid(row=1, column=0, sticky='w', pady=5)
        self.atr1_entry = ttk.Entry(single_tab, width=12)
        self.atr1_entry.insert(0, '3.0')
        self.atr1_entry.grid(row=1, column=1, sticky='w', pady=5)

        ttk.Label(single_tab, text='ATR2 倍数:').grid(row=2, column=0, sticky='w', pady=5)
        self.atr2_entry = ttk.Entry(single_tab, width=12)
        self.atr2_entry.insert(0, '3.0')
        self.atr2_entry.grid(row=2, column=1, sticky='w', pady=5)

        self.save_single_trades_var = tk.BooleanVar(value=False)
        save_check = ttk.Checkbutton(single_tab, text='保存详细交易记录 (至 result/once)', variable=self.save_single_trades_var, bootstyle='round-toggle')
        save_check.grid(row=3, column=0, columnspan=2, sticky='w', pady=10)

        # --- 范围回测UI ---
        grid_tab = ttk.Frame(self.master, padding=15)

        ttk.Label(grid_tab, text='EMA 范围:').grid(row=0, column=0, sticky='w', pady=5)
        self.ema_range_entry = ttk.Entry(grid_tab, width=30)
        self.ema_range_entry.insert(0, '1-50')
        self.ema_range_entry.grid(row=0, column=1, sticky='w', pady=5)
        ttk.Label(grid_tab, text='格式: 1-50 或 1,2,3', bootstyle='secondary').grid(row=0, column=2, sticky='w', padx=10)

        ttk.Label(grid_tab, text='ATR1 列表:').grid(row=1, column=0, sticky='w', pady=5)
        self.atr1_range_entry = ttk.Entry(grid_tab, width=30)
        self.atr1_range_entry.insert(0, '1.0,2.0,3.0')
        self.atr1_range_entry.grid(row=1, column=1, sticky='w', pady=5)

        ttk.Label(grid_tab, text='ATR2 列表:').grid(row=2, column=0, sticky='w', pady=5)
        self.atr2_range_entry = ttk.Entry(grid_tab, width=30)
        self.atr2_range_entry.insert(0, '2.0,3.0,4.0')
        self.atr2_range_entry.grid(row=2, column=1, sticky='w', pady=5)

        self.save_grid_summary_var = tk.BooleanVar(value=True)
        save_check = ttk.Checkbutton(grid_tab, text='保存范围回测总结 (至 result/many)', variable=self.save_grid_summary_var, bootstyle='round-toggle')
        save_check.grid(row=3, column=0, columnspan=2, sticky='w', pady=10)
        
        self.single_frame = single_tab
        self.grid_frame = grid_tab

    def get_single_run_params(self) -> Dict[str, Any]:
        """从UI控件中收集单次回测的所有参数值。"""
        try:
            params = {
                'ema_period': int(self.ema_entry.get()),
                'atr1': float(self.atr1_entry.get()),
                'atr2': float(self.atr2_entry.get()),
                'save_trades': self.save_single_trades_var.get()
            }
            return params
        except ValueError:
            messagebox.showwarning('输入错误', 'EMA 必须是整数，ATR 必须是数字。')
            return None

    def get_grid_search_params(self) -> Dict[str, Any]:
        """从UI控件中收集范围回测的所有参数值。"""
        try:
            def parse_float_list(text: str):
                parts = [p.strip() for p in text.split(',') if p.strip()]
                return [float(p) for p in parts]

            def parse_int_range_or_list(text: str):
                text = text.strip()
                if '-' in text:
                    start, end = map(int, text.split('-'))
                    return list(range(start, end + 1))
                return [int(p) for p in text.split(',') if p.strip()]

            params = {
                'ema_range': parse_int_range_or_list(self.ema_range_entry.get()),
                'atr1_range': parse_float_list(self.atr1_range_entry.get()),
                'atr2_range': parse_float_list(self.atr2_range_entry.get()),
                'save_summary': self.save_grid_summary_var.get()
            }
            return params
        except ValueError:
            messagebox.showwarning('输入错误', '范围或列表参数格式不正确。')
            return None
