"""
calc.py
诉讼费用计算模块（依据 2007《诉讼费用交纳办法》及你提供的“新办法”口径）
- 财产案件受理费：分段累计
- 执行费：分段累计（≤1万 50元；10万-50万 1.5%；50万-500万 1%；500万-1000万 0.5%；>1000万 0.1%）
- 保全费：分段累计，最高不超过5000元
- 非财产/行政/知产等：按规则取值
"""

from typing import Literal 
from datetime import date, timedelta


# =========================
# 财产案件受理费（分段累计）
# =========================
def calc_property_case_fee(amount: float) -> float:
    if amount <= 0:
        return 0.0
    if amount <= 10_000:
        return 50.0
    elif amount <= 100_000:
        return amount * 0.025 - 200
    elif amount <= 200_000:
        return amount * 0.02 + 300
    elif amount <= 500_000:
        return amount * 0.015 + 1300
    elif amount <= 1_000_000:
        return amount * 0.01 + 3800
    elif amount <= 2_000_000:
        return amount * 0.009 + 4800
    elif amount <= 5_000_000:
        return amount * 0.008 + 6800
    elif amount <= 10_000_000:
        return amount * 0.007 + 11800
    elif amount <= 20_000_000:
        return amount * 0.006 + 21800
    else:
        return amount * 0.005 + 41800


# =========================
# 申请保全费（分段累计，≤1000 或无金额：30；≤10万：1%+20；>10万：0.5%+520；封顶5000）
# =========================
def calc_preservation_fee(amount: float) -> float:
    if amount <= 0 or amount <= 1_000:
        return 30.0
    elif amount <= 100_000:
        return amount * 0.01 + 20
    else:
        return min(amount * 0.005 + 520, 5000)


# =========================
# 执行费（分段累计）
#  无执行金额：50–500（此处按 50 处理；如需区间可在UI做可选框）
# =========================
def calc_execution_fee(amount: float) -> float:
    if amount <= 0:
        return 50.0
    if amount <= 10_000:
        return 50.0
    fee = 50.0
    # 超过1万至50万部分：1.5%
    fee += max(0.0, min(amount, 500_000) - 10_000) * 0.015
    # 超过50万至500万部分：1%
    if amount > 500_000:
        fee += (min(amount, 5_000_000) - 500_000) * 0.01
    # 超过500万至1000万部分：0.5%
    if amount > 5_000_000:
        fee += (min(amount, 10_000_000) - 5_000_000) * 0.005
    # 超过1000万部分：0.1%
    if amount > 10_000_000:
        fee += (amount - 10_000_000) * 0.001
    return fee


# =========================
# 非财产/行政/人格权/离婚 等
# =========================
NonPropertyType = Literal[
    "离婚无财产案件",
    "人格权侵权案件",
    "其他非财产案件",
    "劳动人事争议",
    "行政-商标/专利/海事海商",
    "行政-其他",
]

def calc_non_property_case(case_type: NonPropertyType, amount: float = 0.0) -> float:
    if case_type == "离婚无财产案件（基数200）":
        # 基本 150；涉财部分超20万按 0.5%
        if amount <= 200_000:
            return 200.0
        return 200.0 + (amount - 200_000) * 0.005

    if case_type == "人格权侵权案件（基数100）":
        # 基本 300；>5万至10万部分按1%；>10万部分按0.5%
        if amount <= 50_000:
            return 100.0
        elif amount <= 100_000:
            return 100.0 + (amount - 50_000) * 0.01
        else:
            return 100.0 + 500.0 + (amount - 100_000) * 0.005

    if case_type == "其他非财产案件":
        return 70.0

    if case_type == "劳动人事争议":
        return 10.0

    if case_type == "行政-商标/专利/海事海商":
        return 100.0

    if case_type == "行政-其他":
        return 50.0

    return 0.0


# =========================
# 申请类（公示催告/撤裁/破产/支付令 等）
# =========================
ApplicationType = Literal[
    "公示催告",
    "撤销仲裁裁决/认定仲裁效力",
    "破产",
    "支付令",
]

def calc_application_fee(app_type: ApplicationType, amount: float = 0.0) -> float:
    if app_type == "公示催告":
        return 100.0
    if app_type == "撤销仲裁裁决/认定仲裁效力":
        return 400.0
    if app_type == "破产":
        # 破产：按财产案件受理费标准的 1/2，最高 30万
        return min(calc_property_case_fee(amount) / 2.0, 300_000.0)
    if app_type == "支付令":
        return calc_property_case_fee(amount) / 3.0
    return 0.0

# =========================
# 日期计算
# =========================
DEFAULT_DAYS = {
    "公告开庭日": 30,
    "上诉期间": 15,
    "涉外判决": 60,  # 默认 15 天上诉期 + 1 天起算
    "自定义": 0,
}


def add_days(start: date, days: int) -> date:
    return start + timedelta(days=days)