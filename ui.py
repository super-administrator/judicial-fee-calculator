# ui.py
import sys
from datetime import date
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QTabWidget, QComboBox, QDateEdit, QSpinBox,
    QCalendarWidget  # 添加日历控件
)
from PySide6.QtCore import Qt
from typing import Callable, Dict

import calc

# 受理类型（含申请类） → 对应计算函数（返回受理费）
def _acceptance_dispatch() -> Dict[str, Callable[[float, bool], float]]:
    """
    返回一个映射：显示名称 -> (amount, is_amount_empty) -> 受理费
    is_amount_empty 用于决定“空金额时是否显示0”
    """
    return {
        "一般财产案件": lambda amount, empty: 0.0 if empty else calc.calc_property_case_fee(amount),
        "离婚无财产案件（基数200）": lambda amount, empty: calc.calc_non_property_case("离婚无财产案件（基数200）", amount),
        "人格权侵权案件（基数100）": lambda amount, empty: calc.calc_non_property_case("人格权侵权案件（基数100）", amount),
        "商标/专利/海事海商行政案件": lambda amount, empty: calc.calc_non_property_case("行政-商标/专利/海事海商"),
        "其他行政案件": lambda amount, empty: calc.calc_non_property_case("行政-其他"),
        "知识产权案件": lambda amount, empty: 750.0 if (empty or amount <= 0) else calc.calc_property_case_fee(amount),
        # 申请类（按受理费栏展示其申请费）
        "申请公示催告": lambda amount, empty: calc.calc_application_fee("公示催告"),
        "申请撤销仲裁或认定仲裁效力": lambda amount, empty: calc.calc_application_fee("撤销仲裁裁决/认定仲裁效力"),
        "申请破产": lambda amount, empty: 0.0 if empty else calc.calc_application_fee("破产", amount),
    }

class FeeCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("司法速算器 v1.0")
        self.resize(560, 300)

        self.dispatch = _acceptance_dispatch()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 各功能页
        self.tabs.addTab(self._build_fee_tab(), "诉讼费用计算")
        self.tabs.addTab(self._build_date_calc_tab(), "日期计算")
        self.tabs.addTab(self._build_interest_tab(), "利息计算（预留）")

    # -------------------------------
    # Tab 1: 诉讼费用计算
    # -------------------------------
    def _build_fee_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        
        # 创建水平布局来放置案件类型和金额输入
        h_layout = QHBoxLayout()
        
        # 左侧案件类型布局
        type_layout = QHBoxLayout()
        type_label = QLabel("案件类型：")
        self.combo_case_type = QComboBox()
        self.combo_case_type.addItems(list(self.dispatch.keys()))
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.combo_case_type)
        
        # 右侧金额输入布局
        amount_layout = QHBoxLayout()
        amount_label = QLabel("案件金额：")
        self.input_amount = QLineEdit()
        amount_layout.addWidget(amount_label)
        amount_layout.addWidget(self.input_amount)
        
        # 将两个部分添加到水平布局中
        h_layout.addLayout(type_layout)
        h_layout.addSpacing(20)  # 添加一些间距
        h_layout.addLayout(amount_layout)
        
        # 将水平布局添加到主布局
        v.addLayout(h_layout)

        # 计算按钮
        btn = QPushButton("计算")
        btn.clicked.connect(self.calc_fees)

        # 结果显示标签
        self.lbl_accept = QLabel("受理费：0 元")
        self.lbl_accept_half = QLabel("减半金额：0 元")
        self.lbl_preservation = QLabel("保全费：0 元")
        self.lbl_execution = QLabel("执行费：0 元")

        v.addWidget(btn)
        v.addWidget(self.lbl_accept)
        v.addWidget(self.lbl_accept_half)
        v.addWidget(self.lbl_preservation)
        v.addWidget(self.lbl_execution)
        v.addStretch(1)
        return w

    def calc_fees(self):
        try:
            amount = float(self.input_amount.text())
            is_empty = False
        except ValueError:
            amount = 0
            is_empty = True

        # 获取选中的案件类型并计算对应的受理费
        case_type = self.combo_case_type.currentText()
        calc_func = self.dispatch[case_type]
        accept = calc_func(amount, is_empty)
        
        # 计算保全费和执行费
        preservation = calc.calc_preservation_fee(amount)
        execution = calc.calc_execution_fee(amount)

        self.lbl_accept.setText(f"受理费：{accept:.2f} 元")
        self.lbl_accept_half.setText(f"减半金额：{accept/2:.2f} 元")
        self.lbl_preservation.setText(f"保全费：{preservation:.2f} 元")
        self.lbl_execution.setText(f"执行费：{execution:.2f} 元")

    # -------------------------------
    # Tab 2: 日期计算
    # -------------------------------
    def _build_date_calc_tab(self) -> QWidget:
        w = QWidget()
        
        # 创建水平布局来放置左右两部分
        main_layout = QHBoxLayout(w)
        
        # 左侧日历部分
        left_layout = QVBoxLayout()
        calendar = QCalendarWidget()
        calendar.setFixedSize(300, 200)  # 设置日历大小
        calendar.clicked.connect(self.on_calendar_clicked)
        left_layout.addWidget(calendar)
        left_layout.addStretch(1)  # 添加弹性空间，使日历靠上
        
        # 右侧控件部分
        right_layout = QVBoxLayout()
        form = QFormLayout()

        # 起始日期（使用 QLabel 替代 QDateEdit，因为我们现在用日历选择）
        self.date_label = QLabel(date.today().strftime('%Y-%m-%d'))
        form.addRow("起始日期：", self.date_label)

        # 类型选择
        self.combo_type = QComboBox()
        self.combo_type.addItems(list(calc.DEFAULT_DAYS.keys()))
        self.combo_type.currentTextChanged.connect(self.on_type_changed)
        form.addRow("计算类型：", self.combo_type)

        # 天数输入
        self.spin_days = QSpinBox()
        self.spin_days.setRange(0, 365)
        self.spin_days.setValue(calc.DEFAULT_DAYS["公告开庭日"])
        form.addRow("天数：", self.spin_days)

        # 计算按钮
        btn = QPushButton("计算目标日期")
        btn.clicked.connect(self.calc_date)

        # 结果显示
        self.lbl_date_result = QLabel("结果日期将显示在这里")
        self.lbl_date_result.setAlignment(Qt.AlignCenter)

        right_layout.addLayout(form)
        right_layout.addWidget(btn)
        right_layout.addWidget(self.lbl_date_result)
        right_layout.addStretch(1)

        # 将左右两部分添加到主布局
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        
        return w

    def on_calendar_clicked(self, qdate):
        """当用户点击日历时更新起始日期"""
        self.date_label.setText(qdate.toPython().strftime('%Y-%m-%d'))
        self.calc_date()  # 自动重新计算结果

    def on_type_changed(self, text: str):
        self.spin_days.setValue(calc.DEFAULT_DAYS.get(text, 0))

    def calc_date(self):
        """修改计算方法以使用新的日期获取方式"""
        date_str = self.date_label.text()
        base = date.fromisoformat(date_str)
        days = self.spin_days.value()
        result = calc.add_days(base, days)
        self.lbl_date_result.setText(f"结果日期：{result.strftime('%Y-%m-%d')}")

    # -------------------------------
    # Tab 3: 利息计算（预留）
    # -------------------------------
    def _build_interest_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        lbl = QLabel("利息计算功能开发中…   免责条款请自行校验数据 算错概不负责")
        lbl.setAlignment(Qt.AlignCenter)
        v.addWidget(lbl)
        w.setLayout(v)
        return w


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = FeeCalculator()
    win.show()
    sys.exit(app.exec())
