"""
interest_calc.py
利息计算模块
"""

from datetime import date, timedelta
from typing import Tuple, Literal
import calendar

RateType = Literal["day", "month", "year"]

def convert_to_chinese_number(num: float) -> str:
    """将数字金额转换为中文大写人民币格式"""
    units = ["", "拾", "佰", "仟"]
    big_units = ["", "万", "亿", "兆"]
    nums = "零壹贰叁肆伍陆柒捌玖"

    if num < 0:
        return "负" + convert_to_chinese_number(-num)

    int_part = int(num)
    decimal_part = round((num - int_part) * 100)

    if int_part == 0:
        result = "零"
    else:
        result = ""
        group = 0
        zero_flag = False

        while int_part > 0:
            part = int_part % 10000
            if part == 0:
                if not zero_flag and result:
                    result = "零" + result
                zero_flag = True
            else:
                part_str = ""
                for i in range(4):
                    digit = part % 10
                    if digit != 0:
                        part_str = nums[digit] + units[i] + part_str
                        zero_flag = False
                    elif not part_str.startswith("零") and part_str:
                        part_str = "零" + part_str
                    part //= 10
                result = part_str + big_units[group] + result
            int_part //= 10000
            group += 1

    result += "元"

    if decimal_part == 0:
        result += "整"
    else:
        jiao = decimal_part // 10
        fen = decimal_part % 10
        if jiao:
            result += nums[jiao] + "角"
        if fen:
            result += nums[fen] + "分"

    return result

def calculate_days_between(start_date: date, end_date: date) -> Tuple[int, int, int]:
    """
    精确计算两个日期之间的年月日差值
    考虑实际的月份天数，不再按30天简化处理
    """
    if start_date > end_date:
        return (0, 0, 0)
    
    # 从起始日期开始计算
    current_date = start_date
    years = 0
    months = 0
    days = 0
    
    # 先计算完整的年数
    while True:
        # 尝试添加一年
        try:
            next_year_date = current_date.replace(year=current_date.year + 1)
        except ValueError:
            # 处理闰年2月29日的情况
            next_year_date = current_date.replace(year=current_date.year + 1, day=28)
        
        if next_year_date <= end_date:
            years += 1
            current_date = next_year_date
        else:
            break
    
    # 再计算完整的月数
    while True:
        # 尝试添加一个月
        if current_date.month == 12:
            next_month = 1
            next_year = current_date.year + 1
        else:
            next_month = current_date.month + 1
            next_year = current_date.year
        
        # 处理月末日期的情况
        max_day_in_next_month = calendar.monthrange(next_year, next_month)[1]
        next_day = min(current_date.day, max_day_in_next_month)
        
        try:
            next_month_date = current_date.replace(year=next_year, month=next_month, day=next_day)
        except ValueError:
            break
        
        if next_month_date <= end_date:
            months += 1
            current_date = next_month_date
        else:
            break
    
    # 最后计算剩余天数
    days = (end_date - current_date).days
    
    return (years, months, days)

def calculate_interest(amount: float, rate: float, rate_type: RateType,
                      start_date: date, end_date: date, days_base: int = 365) -> float:
    """
    计算利息
    Args:
        amount: 金额
        rate: 利率（百分比）
        rate_type: 利率类型（日/月/年）
        start_date: 起算日
        end_date: 截止日
        days_base: 基准天数（360或365）
    Returns:
        利息金额
    """
    if start_date > end_date or amount <= 0 or rate <= 0:
        return 0.0
    
    # 将利率转换为年利率
    annual_rate = rate
    if rate_type == "day":
        annual_rate = rate * days_base
    elif rate_type == "month":
        annual_rate = rate * 12
    
    # 计算实际天数
    days = (end_date - start_date).days
    
    # 计算利息（简单利息）
    interest = amount * (annual_rate / 100) * (days / days_base)
    
    return round(interest, 2)

# 已移除 calculate_days_between_alternative 函数以避免混淆
# 只保留一个正确的实现