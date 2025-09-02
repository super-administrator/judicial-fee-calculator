# ui.py
import sys
from datetime import date
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QTabWidget, QComboBox, QDateEdit, QSpinBox,
    QCalendarWidget  # 添加日历控件
)
from PySide6.QtCore import Qt, QDate, QLocale
from PySide6.QtGui import QTextCharFormat, QColor
from typing import Dict, Callable, List, Tuple

import calc

# 受理类型（含申请类） → 对应计算函数（返回受理费）
def _acceptance_dispatch() -> Dict[str, Callable[[float, bool], float]]:
    """
    返回一个映射：显示名称 -> (amount, is_amount_empty) -> 受理费
    is_amount_empty 用于决定"空金额时是否显示0"
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
        self.setWindowTitle("司法速算器 v1.1 BY. HSLzf")
        self.resize(700, 310)

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
        
        # 添加一些垂直间距
        v.addSpacing(20)
        
        # 创建居中显示的容器
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        
        # 计算按钮居中且宽度与窗口一致
        btn = QPushButton("计算")
        btn.setFixedWidth(700)  # 设置固定宽度，略小于窗口宽度(560)留出边距
        btn.setMinimumHeight(40)  # 可选：设置按钮高度
        btn.clicked.connect(self.calc_fees)
        center_layout.addWidget(btn)
        
        # 结果显示标签居中
        self.lbl_accept = QLabel("受理费：0 元")
        self.lbl_accept_half = QLabel("减半金额：0 元")
        self.lbl_preservation = QLabel("保全费：0 元")
        self.lbl_execution = QLabel("执行费：0 元")
        
        # 设置标签居中对齐和字体大小
        for lbl in [self.lbl_accept, self.lbl_accept_half, 
                    self.lbl_preservation, self.lbl_execution]:
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("QLabel { font-size: 16pt; }")  # 设置字体大小
            center_layout.addWidget(lbl)
        
        v.addWidget(center_container)
        v.addStretch(1)  # 底部添加弹性空间
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
        layout = QVBoxLayout(w)
        
        # 第一排：公告日期选择（居中显示）
        notice_date_layout = QHBoxLayout()
        notice_date_layout.addStretch(1)
        notice_date_label = QLabel("公告日期：")
        # 设置第一行字体大小
        notice_date_label.setStyleSheet("QLabel { font-size: 14pt; }")
        
        self.notice_date = QDateEdit()
        self.notice_date.setLocale(QLocale(QLocale.Chinese))
        self.notice_date.setDate(QDate.currentDate())
        self.notice_date.setCalendarPopup(True)
        self.notice_date.setDisplayFormat("yyyy年M月d日")
        # 设置日期选择器字体大小
        self.notice_date.setStyleSheet("QDateEdit { font-size: 14pt; }")
        
        notice_date_layout.addWidget(notice_date_label)
        notice_date_layout.addWidget(self.notice_date)
        notice_date_layout.addStretch(1)
        layout.addLayout(notice_date_layout)
        
        # 第二排：各期限输入（修改为居中显示）
        periods_layout = QHBoxLayout()
        periods_layout.addStretch(1)  # 左侧添加弹性空间
    
        # 公告期
        notice_period_layout = QHBoxLayout()
        notice_period_label = QLabel("公告期：")
        notice_period_label.setStyleSheet("QLabel { font-size: 14pt; }")
        self.notice_period = QSpinBox()
        self.notice_period.setRange(0, 365)
        self.notice_period.setValue(30)
        self.notice_period.setStyleSheet("QSpinBox { font-size: 14pt; }")
        notice_period_layout.addWidget(notice_period_label)
        notice_period_layout.addWidget(self.notice_period)
        
        # 添加间距
        periods_layout.addLayout(notice_period_layout)
        periods_layout.addSpacing(20)  # 控件之间的间距
    
        # 答辩期
        reply_period_layout = QHBoxLayout()
        reply_period_label = QLabel("答辩期：")
        reply_period_label.setStyleSheet("QLabel { font-size: 14pt; }")
        self.reply_period = QSpinBox()
        self.reply_period.setRange(0, 365)
        self.reply_period.setValue(15)
        self.reply_period.setStyleSheet("QSpinBox { font-size: 14pt; }")
        reply_period_layout.addWidget(reply_period_label)
        reply_period_layout.addWidget(self.reply_period)
        
        # 添加间距
        periods_layout.addLayout(reply_period_layout)
        periods_layout.addSpacing(20)  # 控件之间的间距
    
        # 开庭日
        court_day_layout = QHBoxLayout()
        court_day_label = QLabel("开庭日第")
        court_day_label.setStyleSheet("QLabel { font-size: 14pt; }")
        self.court_day = QSpinBox()
        self.court_day.setRange(1, 365)
        self.court_day.setValue(3)
        self.court_day.setStyleSheet("QSpinBox { font-size: 14pt; }")
        court_day_suffix = QLabel("日")
        court_day_suffix.setStyleSheet("QLabel { font-size: 14pt; }")
        court_day_layout.addWidget(court_day_label)
        court_day_layout.addWidget(self.court_day)
        court_day_layout.addWidget(court_day_suffix)
        
        periods_layout.addLayout(court_day_layout)
        periods_layout.addStretch(1)  # 右侧添加弹性空间
        layout.addLayout(periods_layout)
        
        # 第三排：日历显示
        self.calendar = QCalendarWidget()
        self.calendar.setFixedHeight(300)
        # 禁用选择功能
        self.calendar.setSelectionMode(QCalendarWidget.NoSelection)
        
        # 设置中文月份显示
        self.calendar.setLocale(QLocale(QLocale.Chinese))
        
        # 设置样式表
        self.calendar.setStyleSheet("""
            QCalendarWidget QTableView {
                selection-background-color: transparent;
            }
            /* 设置日期文字颜色为黑色 */
            QCalendarWidget QTableView QTableCornerButton::section {
                color: black;
            }
            /* 设置月份和年份显示的样式 */
            QCalendarWidget QToolButton {
                color: black;
                background-color: transparent;
                font-size: 13pt;
            }
        """)
        layout.addWidget(self.calendar)
        
        # 第四排：结果显示
        self.result_label = QLabel("开庭时间：请设置各项参数")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("QLabel { font-size: 16pt; }")  # 设置字体大小
        layout.addWidget(self.result_label)
        
        # 连接信号
        self.notice_date.dateChanged.connect(self.update_calendar)
        self.notice_period.valueChanged.connect(self.update_calendar)
        self.reply_period.valueChanged.connect(self.update_calendar)
        self.court_day.valueChanged.connect(self.update_calendar)
        
        return w
    
    def update_calendar(self):
        """更新日历显示和结果"""
        # 清除原有格式
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
        
        # 获取输入值
        notice_date = self.notice_date.date().toPython()
        notice_days = self.notice_period.value()
        reply_days = self.reply_period.value()
        court_day = self.court_day.value()
        
        # 计算日期
        key_dates, final_court_date = calc.calculate_court_date(
            notice_date, notice_days, reply_days, court_day
        )
        
        # 设置日期格式
        weekend_format = QTextCharFormat()
        weekend_format.setBackground(QColor(255, 255, 0))  # 黄色背景 - 周末
        
        normal_format = QTextCharFormat()
        normal_format.setBackground(QColor(50, 205, 50))  # 绿色背景 - 工作日
        
        # 获取原始开庭日期和最终开庭日期
        original_court_date = key_dates[-2]  # 原始计划开庭日
        final_court_date = key_dates[-1]    # 最终开庭日
        
        # 标记开庭日期
        if calc.is_weekend(original_court_date):
            # 如果原始开庭日是周末，用黄色标记
            original_qdate = QDate.fromString(original_court_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
            self.calendar.setDateTextFormat(original_qdate, weekend_format)
            
            # 同时用绿色标记顺延后的周一
            final_qdate = QDate.fromString(final_court_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
            self.calendar.setDateTextFormat(final_qdate, normal_format)
        else:
            # 如果是工作日，直接用绿色标记
            final_qdate = QDate.fromString(final_court_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
            self.calendar.setDateTextFormat(final_qdate, normal_format)
        
        # 自动将日历翻到开庭月份
        final_qdate = QDate.fromString(final_court_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
        # 直接使用最终开庭日期的年月
        self.calendar.setCurrentPage(final_qdate.year(), final_qdate.month())
        
        # 更新结果显示
        if final_court_date != original_court_date:
            self.result_label.setText(
                f"开庭时间：原定于{original_court_date.strftime('%Y年%m月%d日')}（周末），"
                f"顺延至{final_court_date.strftime('%Y年%m月%d日')}"
            )
        else:
            self.result_label.setText(
                f"开庭时间：{final_court_date.strftime('%Y年%m月%d日')}"
            )

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
