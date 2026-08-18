# ui.py
from datetime import timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QLabel,
    QTabWidget, QComboBox, QDateEdit, QCalendarWidget, QFrame, QButtonGroup,
    QRadioButton, QPushButton, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QDate, QLocale, QTimer
from PySide6.QtGui import QTextCharFormat, QColor
from typing import Dict, Callable

import calc
from date_calc import calculate_court_date
from interest_calc import calculate_interest, convert_to_chinese_number, calculate_days_between
from settings import fee_config_exists, load_fee_bases, save_fee_bases


class CopyableLabel(QLabel):
    def __init__(self, text: str = "", copy_callback=None):
        super().__init__(text)
        self.copy_callback = copy_callback
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("单击复制")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            text = self.text().strip()
            if self.copy_callback:
                text = self.copy_callback(text)
            if text:
                self.window().copy_text(text)
        super().mousePressEvent(event)


def money_copy_text(text: str) -> str:
    """金额标签保留界面格式，复制时只返回便于填写的数字。"""
    return text.rsplit("：", 1)[-1].replace(",", "").replace("元", "").strip()

class FeeCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("司法速算器 v1.3 BY. HSLzf")
        self.resize(760, 330)

        self.has_fee_config = fee_config_exists()
        self.fee_bases = load_fee_bases()
        self.dispatch = self._acceptance_dispatch()

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 各功能页
        self.tabs.addTab(self._build_fee_tab(), "诉讼费用计算")
        self.tabs.addTab(self._build_date_calc_tab(), "日期计算")
        self.tabs.addTab(self._build_interest_tab(), "利息/违约金计算")
        self.tabs.addTab(self._build_reserve_tab(), "关于")

        if not self.has_fee_config:
            QTimer.singleShot(0, self.open_fee_base_dialog)

    def copy_text(self, text: str):
        self.window().clipboard().setText(text)
        self.copy_hint.setText(f"已复制：{text}")
        QTimer.singleShot(1400, self.reset_copy_hint)

    def clipboard(self):
        from PySide6.QtWidgets import QApplication

        return QApplication.clipboard()

    def reset_copy_hint(self):
        self.copy_hint.setText("单击计算结果可复制")

    def _acceptance_dispatch(self) -> Dict[str, Callable[[float, bool], float]]:
        return {
            "一般财产案件": lambda amount, empty: 0.0 if empty else calc.calc_property_case_fee(amount),
            "离婚无财产案件": lambda amount, empty: calc.calc_non_property_case(
                "离婚无财产案件",
                amount,
                self.fee_bases["divorce_base"],
            ),
            "人格权侵权案件": lambda amount, empty: calc.calc_non_property_case(
                "人格权侵权案件",
                amount,
                self.fee_bases["personality_base"],
            ),
            "商标/专利/海事海商行政案件": lambda amount, empty: calc.calc_non_property_case("行政-商标/专利/海事海商"),
            "其他行政案件": lambda amount, empty: calc.calc_non_property_case("行政-其他"),
            "知识产权案件": lambda amount, empty: 750.0 if (empty or amount <= 0) else calc.calc_property_case_fee(amount),
            # 申请类（按受理费栏展示其申请费）
            "申请公示催告": lambda amount, empty: calc.calc_application_fee("公示催告"),
            "申请撤销仲裁或认定仲裁效力": lambda amount, empty: calc.calc_application_fee("撤销仲裁裁决/认定仲裁效力"),
            "申请破产": lambda amount, empty: 0.0 if empty else calc.calc_application_fee("破产", amount),
        }
        
    # -------------------------------
    # Tab 1: 诉讼费用计算
    # -------------------------------
    def _build_fee_tab(self) -> QWidget:
        w = QWidget()
        page_layout = QHBoxLayout(w)
        page_layout.setContentsMargins(24, 24, 24, 24)
        page_layout.setSpacing(28)

        input_panel = QWidget()
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(18)
        
        # 案件类型选择
        type_label = QLabel("案件类型：")
        type_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.combo_case_type = QComboBox()
        self.combo_case_type.setStyleSheet("QComboBox { font-size: 16pt; }")
        self.combo_case_type.addItems(list(self.dispatch.keys()))
        input_layout.addWidget(type_label)
        input_layout.addWidget(self.combo_case_type)
        
        # 案件金额输入
        amount_label = QLabel("案件金额：")
        amount_label.setStyleSheet("QLabel { font-size: 16pt; }")
        self.input_amount = QLineEdit()
        self.input_amount.setStyleSheet("QLineEdit { font-size: 16pt; }")
        self.input_amount.setMinimumWidth(280)
        self.input_amount.setPlaceholderText("例如 100,000")
        self.fee_amount_chinese = QLabel("（中文大写）")
        self.fee_amount_chinese.setStyleSheet("QLabel { font-size: 14pt; color: #111111; font-weight: bold; }")
        self.fee_amount_chinese.setWordWrap(True)
        input_layout.addWidget(amount_label)
        input_layout.addWidget(self.input_amount)
        input_layout.addWidget(self.fee_amount_chinese)

        self.btn_fee_base = QPushButton("基数设置")
        self.btn_fee_base.setStyleSheet("QPushButton { font-size: 13pt; }")
        self.btn_fee_base.clicked.connect(self.open_fee_base_dialog)
        input_layout.addWidget(self.btn_fee_base, alignment=Qt.AlignLeft)
        input_layout.addStretch(1)
        
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Sunken)
        
        # 计算结果显示
        result_panel = QWidget()
        result_layout = QGridLayout(result_panel)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setHorizontalSpacing(24)
        result_layout.setVerticalSpacing(16)

        result_title = QLabel("计算结果")
        result_title.setStyleSheet("QLabel { font-size: 18pt; font-weight: bold; }")
        result_layout.addWidget(result_title, 0, 0, 1, 2)

        self.lbl_accept = CopyableLabel("0.00 元", money_copy_text)
        self.lbl_accept_half = CopyableLabel("0.00 元", money_copy_text)
        self.lbl_preservation = CopyableLabel("0.00 元", money_copy_text)
        self.lbl_execution = CopyableLabel("0.00 元", money_copy_text)

        result_rows = [
            ("受理费", self.lbl_accept),
            ("减半金额", self.lbl_accept_half),
            ("保全费", self.lbl_preservation),
            ("执行费", self.lbl_execution),
        ]
        for row, (name, value_label) in enumerate(result_rows, start=1):
            name_label = QLabel(name)
            name_label.setStyleSheet("QLabel { font-size: 15pt; color: #444444; }")
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_label.setMinimumWidth(180)
            value_label.setStyleSheet("QLabel { font-size: 20pt; font-weight: bold; }")
            result_layout.addWidget(name_label, row, 0)
            result_layout.addWidget(value_label, row, 1)

        self.copy_hint = QLabel("单击计算结果可复制")
        self.copy_hint.setAlignment(Qt.AlignCenter)
        self.copy_hint.setStyleSheet("QLabel { font-size: 14pt; color: #999999; }")
        result_layout.addWidget(self.copy_hint, len(result_rows) + 1, 0, 1, 2)

        result_layout.setColumnStretch(0, 1)
        result_layout.setColumnStretch(1, 2)
        result_layout.setRowStretch(len(result_rows) + 2, 1)
        
        page_layout.addWidget(input_panel, 3)
        page_layout.addWidget(divider)
        page_layout.addWidget(result_panel, 4)

        self.input_amount.textChanged.connect(self.calc_fees)
        self.combo_case_type.currentTextChanged.connect(self.calc_fees)
        self.calc_fees()
        return w

    def _parse_amount(self, text: str) -> float:
        return float(text.replace(",", "").replace("，", ""))

    def _format_money(self, amount: float) -> str:
        return f"{amount:,.2f} 元"

    def _format_base_value(self, amount: float) -> str:
        return f"{amount:g}"

    def open_fee_base_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("基数设置")
        dialog.setModal(True)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(22, 18, 22, 18)
        dialog_layout.setSpacing(12)

        title = QLabel("案件基数")
        title.setStyleSheet("QLabel { font-size: 18pt; font-weight: bold; }")
        dialog_layout.addWidget(title)

        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(10)

        divorce_editor = QLineEdit(self._format_base_value(self.fee_bases["divorce_base"]))
        personality_editor = QLineEdit(self._format_base_value(self.fee_bases["personality_base"]))
        for editor in [divorce_editor, personality_editor]:
            editor.setStyleSheet("QLineEdit { font-size: 15pt; }")
            editor.setMinimumWidth(140)

        form_layout.addWidget(QLabel("离婚无财产"), 0, 0)
        form_layout.addWidget(divorce_editor, 0, 1)
        form_layout.addWidget(QLabel("元"), 0, 2)
        form_layout.addWidget(QLabel("人格权"), 1, 0)
        form_layout.addWidget(personality_editor, 1, 1)
        form_layout.addWidget(QLabel("元"), 1, 2)
        dialog_layout.addLayout(form_layout)

        message = QLabel("默认值：离婚无财产 200 元，人格权 100 元。保存后关闭程序仍会记忆。")
        message.setStyleSheet("QLabel { font-size: 12pt; color: gray; }")
        message.setWordWrap(True)
        dialog_layout.addWidget(message)

        error_label = QLabel("")
        error_label.setStyleSheet("QLabel { font-size: 12pt; color: #b00020; }")
        dialog_layout.addWidget(error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        dialog_layout.addWidget(buttons)

        def save_and_close():
            divorce_text = divorce_editor.text().strip()
            personality_text = personality_editor.text().strip()
            if not divorce_text or not personality_text:
                error_label.setText("基数不能为空")
                return

            try:
                divorce_base = self._parse_amount(divorce_text)
                personality_base = self._parse_amount(personality_text)
            except ValueError:
                error_label.setText("基数请输入数字")
                return

            if divorce_base < 0 or personality_base < 0:
                error_label.setText("基数不能小于 0")
                return

            self.fee_bases["divorce_base"] = divorce_base
            self.fee_bases["personality_base"] = personality_base
            save_fee_bases(self.fee_bases)
            self.has_fee_config = True
            self.calc_fees()
            dialog.accept()

        buttons.accepted.connect(save_and_close)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()

    def calc_fees(self):
        amount_text = self.input_amount.text().strip()
        try:
            amount = self._parse_amount(amount_text)
            is_empty = False
            # 更新中文大写显示到诉讼费标签
            self.fee_amount_chinese.setText(f"（{convert_to_chinese_number(amount)}）")
        except ValueError:
            amount = 0
            is_empty = True
            if amount_text:
                self.fee_amount_chinese.setText("（输入有误）")
            else:
                self.fee_amount_chinese.setText("（中文大写）")

        # 获取选中的案件类型并计算对应的受理费
        case_type = self.combo_case_type.currentText()
        calc_func = self.dispatch[case_type]
        accept = calc_func(amount, is_empty)
        
        # 计算保全费和执行费
        preservation = calc.calc_preservation_fee(amount)
        execution = calc.calc_execution_fee(amount)

        self.lbl_accept.setText(self._format_money(accept))
        self.lbl_accept_half.setText(self._format_money(accept / 2))
        self.lbl_preservation.setText(self._format_money(preservation))
        self.lbl_execution.setText(self._format_money(execution))

    # -------------------------------
    # Tab 2: 日期计算
    # -------------------------------
    def _build_date_calc_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(24)

        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(14)

        notice_date_label = QLabel("起始日：")
        notice_date_label.setStyleSheet("QLabel { font-size: 15pt; }")
        self.notice_date = QDateEdit()
        self.notice_date.setLocale(QLocale(QLocale.Chinese))
        self.notice_date.setDate(QDate.currentDate())
        self.notice_date.setCalendarPopup(True)
        self.notice_date.setDisplayFormat("yyyy年M月d日")
        self.notice_date.setStyleSheet("QDateEdit { font-size: 16pt; }")
        settings_layout.addWidget(notice_date_label)
        settings_layout.addWidget(self.notice_date)

        days_label = QLabel("间隔总天数：")
        days_label.setStyleSheet("QLabel { font-size: 15pt; }")
        self.total_days = QLineEdit()
        self.total_days.setStyleSheet("QLineEdit { font-size: 16pt; }")
        self.total_days.setPlaceholderText("0")
        settings_layout.addWidget(days_label)
        settings_layout.addWidget(self.total_days)

        notice_hint = QLabel("（从第二日起计）")
        notice_hint.setStyleSheet("QLabel { font-size: 13pt; color: gray; }")
        settings_layout.addWidget(notice_hint)

        result_line = QFrame()
        result_line.setFrameShape(QFrame.HLine)
        result_line.setFrameShadow(QFrame.Sunken)
        settings_layout.addWidget(result_line)

        result_title = QLabel("日期结果")
        result_title.setStyleSheet("QLabel { font-size: 18pt; font-weight: bold; }")
        settings_layout.addWidget(result_title)

        result_grid = QGridLayout()
        result_grid.setContentsMargins(0, 0, 0, 0)
        result_grid.setHorizontalSpacing(8)
        result_grid.setVerticalSpacing(10)

        self.lbl_count_start = CopyableLabel("-")
        self.lbl_original_date = CopyableLabel("-")
        self.result_label = CopyableLabel("-")
        result_items = [
            ("起算日", self.lbl_count_start),
            ("原到期", self.lbl_original_date),
            ("最终日期", self.result_label),
        ]
        for row, (name, value_label) in enumerate(result_items):
            name_label = QLabel(name)
            name_label.setStyleSheet("QLabel { font-size: 13pt; color: #555555; }")
            value_label.setStyleSheet("QLabel { font-size: 15pt; font-weight: bold; }")
            value_label.setMinimumWidth(150)
            value_label.setWordWrap(False)
            result_grid.addWidget(name_label, row, 0)
            result_grid.addWidget(value_label, row, 1)

        result_grid.setColumnStretch(0, 0)
        result_grid.setColumnStretch(1, 1)
        settings_layout.addLayout(result_grid)

        self.lbl_date_note = QLabel("")
        self.lbl_date_note.setStyleSheet("QLabel { font-size: 13pt; color: gray; }")
        self.lbl_date_note.setWordWrap(True)
        settings_layout.addWidget(self.lbl_date_note)
        settings_layout.addStretch(1)

        calendar_panel = QWidget()
        calendar_layout = QVBoxLayout(calendar_panel)
        calendar_layout.setContentsMargins(0, 0, 0, 0)
        calendar_layout.setSpacing(8)

        self.calendar = QCalendarWidget()
        self.calendar.setMinimumHeight(300)
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
        calendar_layout.addWidget(self.calendar)

        legend = QLabel("绿色：最终日期    黄色：原到期日遇周末")
        legend.setAlignment(Qt.AlignCenter)
        legend.setStyleSheet("QLabel { font-size: 12pt; color: gray; }")
        calendar_layout.addWidget(legend)

        layout.addWidget(settings_panel, 3)
        layout.addWidget(calendar_panel, 5)
        
        # 连接信号
        self.notice_date.dateChanged.connect(self.update_calendar)
        self.total_days.textChanged.connect(self.update_calendar)
        self.update_calendar()
        
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
                    self.lbl_date_note.setText("间隔天数需在 0 到 365 之间")
                    return
            except ValueError:
                self.lbl_date_note.setText("间隔天数请输入整数")
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
            
            count_start_date = start_date + timedelta(days=1)
            self.lbl_count_start.setText(count_start_date.strftime("%Y年%m月%d日"))
            self.lbl_original_date.setText(original_date.strftime("%Y年%m月%d日"))
            if original_date != final_date:
                self.result_label.setText(final_date.strftime("%Y年%m月%d日"))
                self.lbl_date_note.setText("原到期日为周末，已顺延至下一个周一")
            else:
                self.result_label.setText(final_date.strftime("%Y年%m月%d日"))
                self.lbl_date_note.setText("原到期日为工作日，无需顺延")
                
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
        
        type_label = QLabel("自然年天数基准：")
        type_label.setStyleSheet("QLabel { font-size: 16pt; }")
        type_layout.addWidget(type_label)
        
        type_layout.addSpacing(10)
        
        self.calc_type_group = QButtonGroup(self)
        self.days360_type = QRadioButton("360天")
        self.days365_type = QRadioButton("365天")
        self.days365_type.setChecked(True)
        
        for btn in [self.days360_type, self.days365_type]:
            btn.setStyleSheet("QRadioButton { font-size: 16pt; }")
            self.calc_type_group.addButton(btn)
            type_layout.addWidget(btn)
            if btn == self.days360_type:
                type_layout.addSpacing(40)
    
        type_layout.addStretch()
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
        self.result_amount = CopyableLabel("金额：0.00 元", money_copy_text)
        self.result_period = CopyableLabel("逾期：0年0月0天")
        self.result_rate = CopyableLabel("约定利率：0.0%")
        self.result_interest = CopyableLabel("计算结果：0.00 元", money_copy_text)
        self.result_total = CopyableLabel("总计：0.00 元", money_copy_text)
        self.result_chinese = CopyableLabel("（零元整）")
        
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
    # Tab 4: 关于
    # -------------------------------
    def _build_reserve_tab(self) -> QWidget:
        """构建关于标签页"""
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # 添加顶部弹性空间
        layout.addStretch(1)
        
        # 标题
        title_label = QLabel("关于")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("QLabel { font-size: 24pt; font-weight: bold; margin-bottom: 20px; }")
        layout.addWidget(title_label)
        
        # 添加标题后的间距
        layout.addSpacing(20)
        
        # 免责内容
        content_text = """司法速算器 v1.3 BY. HSLzf

本软件为本人工作之余开发，难免会有BUG与疏漏。

请自行校验数据，算错概不负责。

问题建议请通过项目 Issue 反馈

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
