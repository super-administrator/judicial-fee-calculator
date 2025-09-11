# ui.py
import sys
from datetime import date, timedelta
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QTabWidget, QComboBox, QDateEdit, QSpinBox,
    QCalendarWidget, QFrame, QButtonGroup, QRadioButton  
)
from PySide6.QtCore import Qt, QDate, QLocale
from PySide6.QtGui import QTextCharFormat, QColor
from typing import Dict, Callable, List, Tuple

import calc
from date_calc import calculate_court_date
from interest_calc import calculate_interest, convert_to_chinese_number, calculate_days_between

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
        self.setWindowTitle("司法速算器 v1.2 BY. HSLzf")
        self.resize(700, 310)

        self.dispatch = _acceptance_dispatch()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 各功能页
        self.tabs.addTab(self._build_fee_tab(), "诉讼费用计算")
        self.tabs.addTab(self._build_date_calc_tab(), "日期计算")
        self.tabs.addTab(self._build_interest_tab(), "利息/违约金计算")
        self.tabs.addTab(self._build_reserve_tab(), "预留模块")
        
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
        type_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.combo_case_type = QComboBox()
        self.combo_case_type.setStyleSheet("QComboBox { font-size: 16pt; }")
        self.combo_case_type.addItems(list(self.dispatch.keys()))
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.combo_case_type)
        
        # 右侧金额输入布局
        amount_layout = QHBoxLayout()
        amount_label = QLabel("案件金额：")
        amount_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.input_amount = QLineEdit()
        self.input_amount.setStyleSheet("QLineEdit { font-size: 16pt; }")
        self.input_amount.setMaximumWidth(200)
        self.fee_amount_chinese = QLabel("（中文大写）")
        self.fee_amount_chinese.setStyleSheet("QLabel { font-size: 16pt; color: gray; }")
        amount_layout.addWidget(amount_label)
        amount_layout.addWidget(self.input_amount)
        amount_layout.addWidget(self.fee_amount_chinese)
        
        h_layout.addLayout(type_layout)
        h_layout.addSpacing(20)
        h_layout.addLayout(amount_layout)
        h_layout.addStretch()
        
        v.addLayout(h_layout)
        v.addSpacing(20)
        
        # 计算按钮
        btn = QPushButton("计算")
        btn.setFixedWidth(700)
        btn.setMinimumHeight(40)
        btn.setStyleSheet("QPushButton { font-size: 18pt; }")
        btn.clicked.connect(self.calc_fees)
        v.addWidget(btn, alignment=Qt.AlignCenter)
        v.addSpacing(20)
        
        # 创建居中显示的容器
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        
        # 结果显示标签居中
        self.lbl_accept = QLabel("受理费：0 元")
        self.lbl_accept_half = QLabel("减半金额：0 元")
        self.lbl_preservation = QLabel("保全费：0 元")
        self.lbl_execution = QLabel("执行费：0 元")
        
        # 设置标签居中对齐和字体大小
        for lbl in [self.lbl_accept, self.lbl_accept_half, 
                    self.lbl_preservation, self.lbl_execution]:
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("QLabel { font-size: 20pt; }")  # 设置字体大小
            center_layout.addWidget(lbl)
        
        v.addWidget(center_container)
        v.addStretch(1)
        return w

    def calc_fees(self):
        try:
            amount = float(self.input_amount.text())
            is_empty = False
            # 更新中文大写显示到诉讼费标签
            self.fee_amount_chinese.setText(f"（{convert_to_chinese_number(amount)}）")
        except ValueError:
            amount = 0
            is_empty = True
            self.fee_amount_chinese.setText("（输入有误）")

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
        
        # 第一行：合并起始日和间隔天数
        input_layout = QHBoxLayout()
        input_layout.addStretch(1)
        notice_date_label = QLabel("起始日：")
        notice_date_label.setStyleSheet("QLabel { font-size: 18pt; }")
        self.notice_date = QDateEdit()
        self.notice_date.setLocale(QLocale(QLocale.Chinese))
        self.notice_date.setDate(QDate.currentDate())
        self.notice_date.setCalendarPopup(True)
        self.notice_date.setDisplayFormat("yyyy年M月d日")
        self.notice_date.setStyleSheet("QDateEdit { font-size: 18pt; }")
        input_layout.addWidget(notice_date_label)
        input_layout.addWidget(self.notice_date)
        input_layout.addSpacing(20)
        # 间隔总天数
        days_label = QLabel("间隔总天数：")
        days_label.setStyleSheet("QLabel { font-size: 18pt; }")
        self.total_days = QLineEdit()
        self.total_days.setStyleSheet("QLineEdit { font-size: 18pt; }")
        self.total_days.setMaximumWidth(100)
        self.total_days.setPlaceholderText("0")
        input_layout.addWidget(days_label)
        input_layout.addWidget(self.total_days)
        input_layout.addStretch(1)
        layout.addLayout(input_layout)
        notice_hint = QLabel("（从第二日起计）")
        notice_hint.setStyleSheet("QLabel { font-size: 16pt; color: gray; }")
        notice_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(notice_hint)
        layout.addSpacing(5)
        # 第二排：日历显示
        self.calendar = QCalendarWidget()
        self.calendar.setFixedHeight(310)
        self.calendar.setSelectionMode(QCalendarWidget.NoSelection)
        self.calendar.setLocale(QLocale(QLocale.Chinese))
        self.calendar.setStyleSheet("""
            QCalendarWidget QTableView {
                selection-background-color: transparent;
            }
            QCalendarWidget QTableView QTableCornerButton::section {
                color: black;
            }
            QCalendarWidget QToolButton {
                color: black;
                background-color: transparent;
                font-size: 13pt;
            }
        """)
        layout.addWidget(self.calendar)
        
        # 第四排：结果显示
        self.result_label = QLabel("开庭时间：请设置参数")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("QLabel { font-size: 16pt; }")
        layout.addWidget(self.result_label)
        
        # 连接信号
        self.notice_date.dateChanged.connect(self.update_calendar)
        self.total_days.textChanged.connect(self.update_calendar)
        
        return w

    def update_calendar(self):
        """更新日历显示和结果"""
        try:
            # 获取起始日期
            start_date = self.notice_date.date().toPython()
            
            # 获取总天数
            try:
                total_days = int(self.total_days.text() or "0")
                if total_days < 0 or total_days > 365:
                    return
            except ValueError:
                return
                
            # 清除原有格式
            self.calendar.setDateTextFormat(QDate(), QTextCharFormat())
            
            # 计算开庭日期
            original_date, final_date = calculate_court_date(start_date, total_days)
            
            # 设置日期格式
            weekend_format = QTextCharFormat()
            weekend_format.setBackground(QColor(255, 255, 0))  # 黄色背景
            
            normal_format = QTextCharFormat()
            normal_format.setBackground(QColor(50, 205, 50))  # 绿色背景
            
            # 标记开庭日期
            if original_date != final_date:
                # 周末和顺延日期都标记
                original_qdate = QDate.fromString(original_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
                self.calendar.setDateTextFormat(original_qdate, weekend_format)
                
                final_qdate = QDate.fromString(final_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
                self.calendar.setDateTextFormat(final_qdate, normal_format)
            else:
                # 工作日只标记一个日期
                final_qdate = QDate.fromString(final_date.strftime("%Y-%m-%d"), "yyyy-MM-dd")
                self.calendar.setDateTextFormat(final_qdate, normal_format)
            
            # 自动翻到开庭月份
            self.calendar.setCurrentPage(final_qdate.year(), final_qdate.month())
            
            # 更新结果显示
            if original_date != final_date:
                self.result_label.setText(
                    f"开庭时间：原定于{original_date.strftime('%Y年%m月%d日')}（周末），"
                    f"顺延至{final_date.strftime('%Y年%m月%d日')}"
                )
            else:
                self.result_label.setText(
                    f"开庭时间：{final_date.strftime('%Y年%m月%d日')}"
                )
                
        except Exception as e:
            print(f"日期计算错误: {e}")
            return

    # -------------------------------
    # Tab 3: 利息计算
    # -------------------------------
    def _build_interest_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        content_layout = QVBoxLayout()
        
        # 修改：基准天数选择行
        type_layout = QHBoxLayout()
        #type_layout.addSpacing(20)  # 左侧留白
        
        type_label = QLabel("自然年天数基准：")  # 修改为中文冒号
        type_label.setStyleSheet("QLabel { font-size: 16pt; }")
        type_layout.addWidget(type_label)
        
        type_layout.addSpacing(10)  # 标签后的间距
        
        self.calc_type_group = QButtonGroup(self)
        self.days360_type = QRadioButton("360天")
        self.days365_type = QRadioButton("365天")
        self.days365_type.setChecked(True)
        
        for btn in [self.days360_type, self.days365_type]:
            btn.setStyleSheet("QRadioButton { font-size: 16pt; }")
            self.calc_type_group.addButton(btn)
            type_layout.addWidget(btn)
            if btn == self.days360_type:  # 在360天后添加间距
                type_layout.addSpacing(40)  # 增加两个选项之间的间距
    
        type_layout.addStretch()  # 右侧弹性空间
        content_layout.addLayout(type_layout)
    
    
        # 第一行：案件金额
        amount_layout = QHBoxLayout()
        amount_label = QLabel("案件金额：")
        amount_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.interest_amount = QLineEdit()
        self.interest_amount.setStyleSheet("QLineEdit { font-size: 16pt; }")
        self.interest_amount_chinese = QLabel("（中文大写）")
        self.interest_amount_chinese.setStyleSheet("QLabel { font-size: 16pt; color: gray; }")
        amount_layout.addWidget(amount_label)
        amount_layout.addWidget(self.interest_amount)
        amount_layout.addWidget(self.interest_amount_chinese)
        amount_layout.addStretch()
        content_layout.addLayout(amount_layout)        
        # 第二行：利率选择
        rate_layout = QHBoxLayout()
        rate_label = QLabel("利率选择：")
        rate_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.rate_input = QLineEdit()
        self.rate_input.setStyleSheet("QLineEdit { font-size: 16pt; }")
        self.rate_input.setMaximumWidth(100)
        
        self.rate_group = QButtonGroup(self)
        self.day_rate = QRadioButton("日利率")
        self.month_rate = QRadioButton("月利率")
        self.year_rate = QRadioButton("年利率")
        self.year_rate.setChecked(True)
        for btn in [self.day_rate, self.month_rate, self.year_rate]:
            btn.setStyleSheet("QRadioButton { font-size: 16pt; }")
            self.rate_group.addButton(btn)
        
        rate_layout.addWidget(rate_label)
        rate_layout.addWidget(self.rate_input)
        rate_layout.addWidget(QLabel("%"))
        rate_layout.addWidget(self.day_rate)
        rate_layout.addWidget(self.month_rate)
        rate_layout.addWidget(self.year_rate)
        rate_layout.addStretch()
        content_layout.addLayout(rate_layout)
        # 第三行：起算日和截止日
        date_layout = QHBoxLayout()
        # 起算日
        start_label = QLabel("起算日：")
        start_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.start_date = QDateEdit()
        self.start_date.setStyleSheet("QDateEdit { font-size: 16pt; }")
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        # 截止日
        end_label = QLabel("截止日：")
        end_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.end_date = QDateEdit()
        self.end_date.setStyleSheet("QDateEdit { font-size: 16pt; }")
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        # 间隔显示
        self.interval_label = QLabel("间隔：0年0月0天")
        self.interval_label.setStyleSheet("QLabel { font-size: 16pt; }")        
        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date)
        date_layout.addWidget(self.interval_label)
        date_layout.addStretch()
        content_layout.addLayout(date_layout)
        content_layout.addSpacing(20)
        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        content_layout.addWidget(line2)
        
        # 修改结果显示区
        self.result_amount = QLabel("金额：0.00 元")
        self.result_period = QLabel("逾期：0年0月0天")
        self.result_rate = QLabel("约定利率：0.0%")
        self.result_interest = QLabel("计算结果：0.00 元")
        self.result_total = QLabel("总计：0.00 元")
        self.result_chinese = QLabel("（零元整）")
        
        for lbl in [self.result_amount, self.result_period, self.result_rate,
                   self.result_interest, self.result_total, self.result_chinese]:
            lbl.setStyleSheet("QLabel { font-size: 20pt; }")
            lbl.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(lbl)
        
        layout.addLayout(content_layout)
        
        
        # 绑定信号
        self.interest_amount.textChanged.connect(self.update_amount)
        self.rate_input.textChanged.connect(self.calculate_result)
        self.start_date.dateChanged.connect(self.calculate_result)
        self.end_date.dateChanged.connect(self.calculate_result)
        self.days360_type.toggled.connect(self.calculate_result)
        self.days365_type.toggled.connect(self.calculate_result)
        for btn in [self.day_rate, self.month_rate, self.year_rate]:
            btn.toggled.connect(self.calculate_result)
    
        # 修改日期选择器的区域设置
        self.start_date.setLocale(QLocale(QLocale.Chinese))
        self.start_date.setDisplayFormat("yyyy年M月d日")
        self.end_date.setLocale(QLocale(QLocale.Chinese))
        self.end_date.setDisplayFormat("yyyy年M月d日")
    
        return w
    
    def update_amount(self):
        """更新金额的中文显示"""
        try:
            amount = float(self.interest_amount.text() or "0")
            self.interest_amount_chinese.setText(f"（{convert_to_chinese_number(amount)}）")
            self.calculate_result()
        except ValueError:
            self.interest_amount_chinese.setText("（输入有误）")
    
    def calculate_result(self):
        """计算利息/违约金结果"""
        try:
            # 获取输入值
            amount = float(self.interest_amount.text() or "0")
            rate = float(self.rate_input.text() or "0")
            start_date = self.start_date.date().toPython()
            end_date = self.end_date.date().toPython()
            
            # 获取利率类型和基准天数
            rate_type = "year"
            if self.day_rate.isChecked():
                rate_type = "day"
            elif self.month_rate.isChecked():
                rate_type = "month"
                
            days_base = 365 if self.days365_type.isChecked() else 360
            
            # 计算时间间隔
            years, months, days = calculate_days_between(start_date, end_date)
            self.interval_label.setText(f"间隔：{years}年{months}月{days}天")
            
            # 计算利息/违约金
            interest = calculate_interest(amount, rate, rate_type, start_date, end_date, days_base)
            total = amount + interest
        
            # 更新显示
            self.result_amount.setText(f"金额：{amount:,.2f} 元")
            self.result_period.setText(f"逾期：{years}年{months}月{days}天")
            self.result_rate.setText(f"约定利率：{rate}%")
            self.result_interest.setText(f"计算结果：{interest:,.2f} 元")
            self.result_total.setText(f"总计：{total:,.2f} 元")
            self.result_chinese.setText(f"（{convert_to_chinese_number(total)}）")
            
        except ValueError:
            self.result_interest.setText("计算结果：输入有误")
            self.result_total.setText("总计：0 元")
            self.result_chinese.setText("")
    
    # -------------------------------
    # Tab 4: 预留模块
    # -------------------------------
    def _build_reserve_tab(self) -> QWidget:
        """构建预留模块标签页"""
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # 添加顶部弹性空间
        layout.addStretch(1)
        
        # 标题
        title_label = QLabel("免责条款")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { font-size: 24pt; font-weight: bold; margin-bottom: 20px; }")
        layout.addWidget(title_label)
        
        # 添加标题后的间距
        layout.addSpacing(20)
        
        # 免责内容
        content_text = """本软件为本人工作之余开发，难免会有BUG与疏漏。

        请自行校验数据，算错概不负责。

        问题建议请提交Issue及时反馈

        感谢您的支持与配合"""
        
        content_label = QLabel(content_text)
        content_label.setAlignment(Qt.AlignCenter)
        content_label.setStyleSheet("""
            QLabel { 
                font-size: 16pt; 
                line-height: 1.5;
                color: #333333;
                margin: 10px;
            }
        """)
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        
        # 添加底部弹性空间
        layout.addStretch(2)
        
        return w