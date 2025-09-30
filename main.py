import threading
import queue
import os
import datetime
import tkinter as tk
import subprocess
import sys
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

import json
import importlib

# --- 动态策略注册 ---
def load_strategy_registry():
    """从 config.json 加载并构建策略注册表。"""
    registry = {}
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        for strategy_config in config.get('strategies', []):
            if not strategy_config.get('enabled', False):
                continue

            name = strategy_config['name']
            
            # 动态导入UI类
            ui_module = importlib.import_module(strategy_config['ui_module'])
            ui_class = getattr(ui_module, strategy_config['ui_class'])
            
            # 动态导入逻辑函数
            logic_module = importlib.import_module(strategy_config['logic_module'])
            single_run_func = getattr(logic_module, strategy_config['single_run_func'])
            batch_run_func = getattr(logic_module, strategy_config['batch_run_func'])

            registry[name] = {
                "ui": ui_class,
                "logic": {
                    "single": single_run_func,
                    "batch": batch_run_func,
                }
            }
        return registry, config.get('app_settings', {})
    except (FileNotFoundError, json.JSONDecodeError, ImportError, AttributeError) as e:
        messagebox.showerror("配置错误", f"加载 config.json 或策略模块失败: {e}")
        return {}, {}

STRATEGY_REGISTRY, APP_SETTINGS = load_strategy_registry()


class MainApp:
    def __init__(self, root: ttk.Window):
        self.root = root
        root.title('模块化策略回测框架')
        root.geometry('850x800')

        # 通用组件
        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.current_strategy_ui = None

        # --- 主布局 ---
        main_frame = ttk.Frame(root, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        # --- 顶部：策略和文件选择 ---
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=X, expand=NO, pady=(0, 10))
        top_frame.grid_columnconfigure(1, weight=1)

        # 策略选择
        ttk.Label(top_frame, text='选择策略:').grid(row=0, column=0, padx=(0, 10), sticky='w')
        self.strategy_var = tk.StringVar()
        self.strategy_combo = ttk.Combobox(top_frame, textvariable=self.strategy_var, state='readonly', values=list(STRATEGY_REGISTRY.keys()))
        self.strategy_combo.grid(row=0, column=1, columnspan=2, sticky='ew', padx=(0, 10))
        if self.strategy_combo['values']:
            self.strategy_combo.current(0)
        self.strategy_combo.bind('<<ComboboxSelected>>', self.on_strategy_select)

        # 文件选择
        ttk.Label(top_frame, text='数据文件:').grid(row=1, column=0, padx=(0, 10), pady=(10, 0), sticky='w')
        self.csv_var = tk.StringVar()
        self.csv_combo = ttk.Combobox(top_frame, textvariable=self.csv_var, state='readonly')
        self.csv_combo.grid(row=1, column=1, sticky='ew', pady=(10, 0))
        self._refresh_csv_list()
        
        self.btn_choose = ttk.Button(top_frame, text='浏览...', command=self.choose_file, bootstyle='outline')
        self.btn_choose.grid(row=1, column=2, padx=(10, 0), pady=(10, 0))

        # --- 中部：策略专属UI区域 ---
        self.strategy_notebook = ttk.Notebook(main_frame)
        self.strategy_notebook.pack(fill=BOTH, expand=YES, pady=(10, 10))

        # --- 底部：操作与日志 ---
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=X, expand=NO, pady=(0, 10))
        action_frame.grid_columnconfigure(0, weight=1)

        self.run_button = ttk.Button(action_frame, text='运行回测', command=self.start_backtest, bootstyle='success-outline', width=12)
        self.run_button.pack(side=LEFT, padx=(0, 5))

        self.stop_button = ttk.Button(action_frame, text='中止', command=self.stop_backtest, bootstyle='danger-outline', width=8, state='disabled')
        self.stop_button.pack(side=LEFT, padx=(0, 15))

        self.open_folder_button = ttk.Button(action_frame, text='打开结果目录', command=self.open_result_folder, bootstyle='info-outline', width=15)
        self.open_folder_button.pack(side=LEFT)

        self.status_var = tk.StringVar(value='就绪')
        self.status_label = ttk.Label(action_frame, textvariable=self.status_var, anchor='e')
        self.status_label.pack(side=RIGHT, fill=X, expand=YES)
        
        self.progress = ttk.Progressbar(action_frame, mode='indeterminate', length=180)
        self.progress.pack(side=RIGHT, padx=10)

        log_frame = ttk.Labelframe(main_frame, text='日志输出', padding=10)
        log_frame.pack(fill=BOTH, expand=YES)
        self.log_text = ScrolledText(log_frame, height=12, font=('Courier New', 10), relief='flat', bg='#f0f0f0')
        self.log_text.pack(fill=BOTH, expand=YES)

        # 初始加载默认策略UI
        self.on_strategy_select()

        # 周期性更新日志
        self.root.after(200, self._poll_log_queue)

    def on_strategy_select(self, event=None):
        """当用户选择一个新策略时触发。"""
        strategy_name = self.strategy_var.get()
        if not strategy_name:
            return

        # 清空旧的UI
        for tab in self.strategy_notebook.tabs():
            self.strategy_notebook.forget(tab)
        
        # 加载新的UI
        strategy_info = STRATEGY_REGISTRY.get(strategy_name)
        if strategy_info:
            ui_class = strategy_info["ui"]
            # 直接将 notebook 作为父级传递给策略UI类
            self.current_strategy_ui = ui_class(self.strategy_notebook)
            
            # 将策略UI的Frame添加到Notebook中
            # UI类现在负责将自己的框架添加到作为父级的 notebook 中
            # 因此这里不需要再调用 add
        
        self._log(f"已加载策略: {strategy_name}")

    def _refresh_csv_list(self, selected: str = None):
        """刷新 data/no 下的 csv 列表并填充到 Combobox"""
        try:
            data_no = os.path.join(os.getcwd(), 'data', 'no')
            files = []
            if os.path.isdir(data_no):
                for f in os.listdir(data_no):
                    if f.lower().endswith('.csv'):
                        name, _ = os.path.splitext(f)
                        files.append(name)
            files.sort()
            self.csv_combo['values'] = files
            
            default_file = 'btc_usdt_24-至今'
            if selected and selected in files:
                self.csv_var.set(selected)
            elif default_file in files:
                self.csv_var.set(default_file)
            elif files:
                self.csv_var.set(files[0])
        except Exception as e:
            self._log(f"错误: 刷新CSV列表失败 - {e}")

    def choose_file(self):
        path = filedialog.askopenfilename(initialdir=os.path.join(os.getcwd(), 'data', 'no'), filetypes=[('CSV files','*.csv')])
        if path:
            base = os.path.basename(path)
            name, _ = os.path.splitext(base)
            self._refresh_csv_list(selected=name)

    def _log(self, msg: str):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_queue.put(f'[{ts}] {msg}')

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + '\n')
                self.log_text.see(tk.END)
                if '| 预计剩余:' in msg:
                    status_content = msg.split('] ', 1)[-1]
                    self.status_var.set(status_content)
        except queue.Empty:
            pass
        self.root.after(200, self._poll_log_queue)

    def start_backtest(self):
        """根据当前激活的选项卡启动相应的回测"""
        if not self.current_strategy_ui:
            messagebox.showwarning('无策略', '请先选择一个策略。')
            return
        
        selected_tab = self.strategy_notebook.select()
        if not selected_tab:
            messagebox.showwarning('无选项卡', '没有检测到有效的回测选项卡。')
            return
            
        self.stop_event.clear()
        selected_tab_index = self.strategy_notebook.index(selected_tab)
        
        if selected_tab_index == 0: # 单次回测
            params = self.current_strategy_ui.get_single_run_params()
            if params:
                self.start_single(params)
        elif selected_tab_index == 1: # 范围回测
            params = self.current_strategy_ui.get_grid_search_params()
            if params:
                self.start_grid(params)

    def stop_backtest(self):
        if not self.stop_event.is_set():
            self._log(">>> 用户请求中止操作，请等待当前任务完成...")
            self.stop_event.set()
            self.stop_button.config(state='disabled')

    def open_result_folder(self):
        path = os.path.join(os.getcwd(), 'result')
        try:
            os.makedirs(path, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            self._log(f"已在文件浏览器中打开: {path}")
        except Exception as e:
            self._log(f"错误: 无法打开文件夹 {path} - {e}")

    def start_single(self, params: dict):
        csv_name = self.csv_var.get().strip()
        if not csv_name:
            messagebox.showwarning('输入错误', '请先选择一个 CSV 文件')
            return

        strategy_name = self.strategy_var.get()
        logic_func = STRATEGY_REGISTRY[strategy_name]["logic"]["single"]

        self._set_running(True, '正在运行单次回测...')
        
        # 准备线程参数
        thread_args = (csv_name,) + tuple(params.values())
        # 移除 plot，因为它现在是 kwargs 的一部分
        thread_kwargs = {'plot': False, 'save_trades': params.get('save_trades', False), 'stop_event': self.stop_event, 'log_queue': self.log_queue}

        # 从 params 中移除已经处理过的 save_trades，避免重复传递
        clean_params = params.copy()
        clean_params.pop('save_trades', None)
        
        thread_args = (csv_name,) + tuple(clean_params.values())

        t = threading.Thread(target=self._run_single_thread, args=(logic_func, thread_args, thread_kwargs), daemon=True)
        t.start()

    def _run_single_thread(self, logic_func, args, kwargs):
        # 从kwargs中提取save_trades，并从args中移除它，以避免重复
        printable_args = args[1:] # 去掉csv_name
        self._log(f'准备单次回测: {args[0]}, 参数: {printable_args}')
        start_time = datetime.datetime.now()
        try:
            # 直接将kwargs传递给函数
            stats = logic_func(*args, **kwargs)
            if self.stop_event.is_set():
                self._log('>>> 单次回测被用户中止。')
            elif stats is None:
                self._log('单次回测失败或无结果。')
            else:
                self._log('单次回测完成，结果:')
                self._log(stats.to_string())
        except Exception as e:
            self._log(f'单次回测异常: {e}')
        finally:
            end_time = datetime.datetime.now()
            self._log(f"总耗时: {end_time - start_time}")
            self.root.after(0, lambda: self._set_running(False, '就绪'))

    def start_grid(self, params: dict):
        csv_name = self.csv_var.get().strip()
        if not csv_name:
            messagebox.showwarning('输入错误', '请先选择一个 CSV 文件')
            return

        strategy_name = self.strategy_var.get()
        logic_func = STRATEGY_REGISTRY[strategy_name]["logic"]["batch"]
        
        self._set_running(True, '正在运行范围回测...')

        # 准备线程参数
        thread_kwargs = {'plot': False, 'stop_event': self.stop_event, 'log_queue': self.log_queue}
        
        # 从params中移除save_summary，因为它不直接传递给run_batch_backtest
        # 这个逻辑应该在run_batch_backtest内部处理
        clean_params = params.copy()
        clean_params.pop('save_summary', None)
        thread_args = (csv_name,) + tuple(clean_params.values())


        t = threading.Thread(target=self._run_grid_thread, args=(logic_func, thread_args, thread_kwargs), daemon=True)
        t.start()

    def _run_grid_thread(self, logic_func, args, kwargs):
        self._log(f'开始范围回测...')
        start_time = datetime.datetime.now()
        try:
            logic_func(*args, **kwargs)
            if self.stop_event.is_set():
                self._log(f'>>> 范围回测被用户中止。总耗时: {datetime.datetime.now() - start_time}')
            else:
                self._log(f'范围回测完成。总耗时: {datetime.datetime.now() - start_time}')
        except Exception as e:
            self._log(f'范围回测异常: {e}')
        finally:
            self.root.after(0, lambda: self._set_running(False, '就绪'))

    def _set_running(self, running: bool, status: str = ''):
        new_state = 'disabled' if running else 'normal'
        stop_state = 'normal' if running else 'disabled'

        self.run_button.config(state=new_state)
        self.stop_button.config(state=stop_state)
        self.open_folder_button.config(state=new_state)
        self.strategy_combo.config(state=new_state)
        self.csv_combo.config(state=new_state)
        self.btn_choose.config(state=new_state)

        try:
            for tab in self.strategy_notebook.tabs():
                self.strategy_notebook.tab(tab, state=new_state)
        except tk.TclError:
            print("警告: 无法更改选项卡状态。")

        if running:
            self.progress.start(10)
        else:
            self.progress.stop()
        
        if status:
            self.status_var.set(status)


def main():
    # 确保项目根目录在 sys.path 中
    if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 从配置加载主题，如果失败则使用默认值
    theme = APP_SETTINGS.get('default_theme', 'litera')
    root = ttk.Window(themename=theme)
    
    if not STRATEGY_REGISTRY:
        messagebox.showerror("启动失败", "没有可用的策略。请检查 config.json 文件。")
        root.destroy()
        return

    app = MainApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
