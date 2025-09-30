# 项目文档

本文档旨在说明 `tradingTest` 项目的结构、核心模块功能以及如何使用和扩展该框架。

## 1. 项目结构

```
tradingTest/
├── config.json             # 核心配置文件，用于注册策略和应用设置
├── main.py                 # 主应用程序入口
├── requirements.txt        # Python 依赖列表
├── data/                   # 存放原始和已清洗的数据
│   ├── no/                 # 存放原始未处理的CSV数据
│   └── ok/                 # 存放经过清洗可用于回测的CSV数据
├── doc/                    # 项目文档
│   └── project_docs.md
├── gui/                    # 存放策略的UI界面模块
│   ├── base_ui.py          # 所有策略UI模块必须继承的抽象基类
│   └── ema_2_atr_ui.py     # "EMA + 2 ATR" 策略的具体UI实现
├── result/                 # 存放回测结果
│   ├── many/               # 存放范围回测（网格搜索）的总结CSV
│   └── once/               # 存放单次回测的详细交易记录CSV
├── strategy/               # 存放策略的逻辑实现模块
│   └── ema_2_atr.py        # "EMA + 2 ATR" 策略的核心回测逻辑
└── tool/                   # 通用工具模块
    └── dataDeal.py         # 数据处理工具，如清洗CSV
```

## 2. 核心模块说明

### `config.json`
这是整个框架的神经中枢。它通过一个JSON文件定义了所有可用的策略及其相关信息。

- **`strategies`**: 一个策略对象的数组。
  - `name`: 策略在UI中显示的名称。
  - `enabled`: 是否启用该策略。
  - `ui_module`, `ui_class`: 指向策略UI实现。
  - `logic_module`, `single_run_func`, `batch_run_func`: 指向策略逻辑实现。
- **`app_settings`**: 全局应用设置，如UI主题。

### `main.py`
应用程序的主入口。它负责：
1.  读取 `config.json` 并动态加载所有已启用的策略。
2.  构建主GUI窗口，包括策略选择下拉菜单、文件选择、操作按钮和日志区域。
3.  根据用户选择，动态地在`Notebook`中加载和显示相应策略的UI界面。
4.  管理回测线程，处理UI与后端逻辑的交互（如开始/停止回测）。

### `gui/base_ui.py`
定义了一个抽象基类 `BaseStrategyUI`。所有策略的UI模块都必须继承这个类，并实现其抽象方法：
- `create_frames()`: 创建并返回单次和范围回测的UI组件（`Frame`）。
- `get_single_run_params()`: 从UI收集单次回测的参数。
- `get_grid_search_params()`: 从UI收集范围回测的参数。

这确保了主程序可以与任何策略UI进行标准化的交互。

### `strategy/` 和 `gui/` 目录
这两个目录体现了**UI与逻辑分离**的设计思想。
- `strategy/` 目录下的文件专注于回测算法本身。
- `gui/` 目录下的文件专注于如何通过图形界面来配置这些算法的参数。

## 3. 如何使用

1.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **准备数据**:
    将你的原始 `*.csv` 数据文件放入 `data/no/` 文件夹中。程序在首次使用某个数据文件时会自动进行清洗，并将结果存入 `data/ok/`。
3.  **运行程序**:
    ```bash
    python main.py
    ```
4.  **执行回测**:
    - 在UI界面选择一个策略。
    - 选择一个数据文件。
    - 在“单次回测”或“范围回测”选项卡中填写参数。
    - 点击“运行回测”按钮。
    - 结果会自动保存在 `result/` 目录下。

## 4. 如何扩展（添加新策略）

假设你要添加一个名为 "RSI Crossover" 的新策略。

1.  **创建策略逻辑文件**:
    在 `strategy/` 目录下创建 `rsi_crossover.py`。此文件应包含策略类（继承自 `backtesting.Strategy`）以及执行回测的函数（如 `run_single_rsi_backtest` 和 `run_batch_rsi_backtest`）。

2.  **创建策略UI文件**:
    在 `gui/` 目录下创建 `rsi_crossover_ui.py`。
    - 在此文件中创建一个类，如 `RsiCrossoverUI`，它必须继承自 `gui.base_ui.BaseStrategyUI`。
    - 实现 `create_frames`, `get_single_run_params`, `get_grid_search_params` 方法，以提供RSI策略所需的参数输入框。

3.  **注册新策略**:
    打开 `config.json` 文件，在 `strategies` 列表中添加一个新的JSON对象：
    ```json
    {
      "name": "RSI 交叉策略",
      "enabled": true,
      "description": "一个基于RSI指标交叉的交易策略。",
      "ui_module": "gui.rsi_crossover_ui",
      "ui_class": "RsiCrossoverUI",
      "logic_module": "strategy.rsi_crossover",
      "single_run_func": "run_single_rsi_backtest",
      "batch_run_func": "run_batch_rsi_backtest"
    }
    ```

4.  **完成**！
    重新启动 `main.py`，新的 "RSI 交叉策略" 就会自动出现在下拉菜单中，并可以正常使用。
