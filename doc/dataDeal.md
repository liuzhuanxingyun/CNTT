# dataDeal.py 说明

`dataDeal.py` 是一个数据清洗工具，其主要职责是将从交易所下载的原始 K 线数据（通常是 CSV 格式）转换为回测框架（如 `backtesting.py`）可以识别和使用的标准格式。

## 主要功能

1.  **自动识别时间列**:
    -   脚本能够自动在 CSV 文件中查找常见的时间戳列名，如 `open_time`, `timestamp`, `time`, `date` 等。
    -   如果自动识别失败，用户也可以在调用函数时手动指定时间列的名称。

2.  **时间戳转换**:
    -   将交易所提供的 Unix 时间戳（无论是秒级还是毫秒级）转换为人类可读的、标准化的 `YYYY-MM-DD HH:MM:SS` 格式。

3.  **列名标准化**:
    -   将常见的 K 线数据列名（如 `open`, `high`, `low`, `close`, `volume`）重命名为回测库通常期望的标准格式（`Open`, `High`, `Low`, `Close`, `Volume`）。

4.  **数据筛选**:
    -   从原始 CSV 文件中只保留回测所需的核心列：`Date`, `Open`, `High`, `Low`, `Close`, `Volume`，并丢弃其他无关信息。

5.  **文件输出**:
    -   将清洗和格式化后的数据保存为一个新的 CSV 文件，通常保存在 `data/ok/` 目录下，以便与原始数据 `data/no/` 分开管理。

## 函数

-   `clean_csv_to_backtesting(input_path, output_dir, time_col=None)`
    -   **`input_path`**: 原始 CSV 文件的路径。
    -   **`output_dir`**: 清洗后文件的输出目录。
    -   **`time_col` (可选)**: 如果需要手动指定时间列的名称，可以通过此参数传入。
    -   **返回**: 清洗后文件的完整路径。

## 使用示例

```python
from utils.dataDeal import clean_csv_to_backtesting

# 将 'binance_data.csv' 清洗并保存到 'cleaned_data' 目录
cleaned_file_path = clean_csv_to_backtesting(
    input_path='downloads/binance_data.csv',
    output_dir='cleaned_data'
)

print(f"数据已清洗并保存到: {cleaned_file_path}")
```
