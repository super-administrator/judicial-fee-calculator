"""
calc.py
诉讼费用计算模块（依据 2007《诉讼费用交纳办法》及你提供的“新办法”口径）
- 财产案件受理费：分段累计
- 执行费：分段累计（≤1万 50元；10万-50万 1.5%；50万-500万 1%；500万-1000万 0.5%；>1000万 0.1%）
- 保全费：分段累计，最高不超过5000元
- 非财产/行政/知产等：按规则取值
"""

from typing import Tuple, List, Literal 
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
def is_weekend(d: date) -> bool:
    """判断是否为周末"""
    return d.weekday() >= 5

def get_next_monday(d: date) -> date:
    """获取下一个周一"""
    days_ahead = 7 - d.weekday()
    return d + timedelta(days=days_ahead)

def calculate_court_date(notice_date: date, notice_days: int, 
                        reply_days: int, court_day: int) -> Tuple[List[date], date]:
    """
    计算开庭日期和关键日期列表
    返回: (关键日期列表, 最终开庭日期)
    """
    # 计算关键日期
    notice_end = notice_date + timedelta(days=notice_days)  # 公告期结束
    reply_end = notice_end + timedelta(days=reply_days)     # 答辩期结束
    court_date = reply_end + timedelta(days=court_day)      # 预计开庭日
    
    # 如果开庭日是周末，顺延到下周一
    if is_weekend(court_date):
        final_court_date = get_next_monday(court_date)
    else:
        final_court_date = court_date
        
    # 返回所有关键日期和最终开庭日期
    key_dates = [
        notice_date,    # 公告日
        notice_end,     # 公告期结束日
        reply_end,      # 答辩期结束日
        court_date,     # 原开庭日
        final_court_date # 最终开庭日
    ]
    
    return key_dates, final_court_date
