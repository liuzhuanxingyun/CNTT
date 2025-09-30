"""
gui/base_ui.py

定义所有策略UI模块必须继承的抽象基类。
它为策略UI规定了一个标准接口，以便主应用程序可以统一地与它们交互。
"""
import tkinter as tk
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class BaseStrategyUI(ABC):
    """
    抽象基类，定义了策略UI模块的标准接口。
    """

    def __init__(self, master):
        """
        构造函数。
        :param master: 父级tk组件。
        """
        self.master = master
        self.params_frame: tk.Frame = None

    @abstractmethod
    def create_frames(self):
        """
        创建并返回包含单次回测和范围回测参数的Frame元组。
        主应用会将这些Frame放置在对应的选项卡中。
        """
        pass

    @abstractmethod
    def get_single_run_params(self) -> Dict[str, Any]:
        """
        从UI控件中收集单次回测的所有参数值，并以字典形式返回。
        """
        pass
    
    @abstractmethod
    def get_grid_search_params(self) -> Dict[str, Any]:
        """
        从UI控件中收集范围回测的所有参数值，并以字典形式返回。
        """
        pass
