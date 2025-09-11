"""
date_calc.py
司法日期计算模块
"""

from datetime import date, timedelta
from typing import Tuple, List

def is_weekend(d: date) -> bool:
    """判断是否为周末"""
    return d.weekday() >= 5

def get_next_monday(d: date) -> date:
    """获取下一个周一"""
    days_ahead = 7 - d.weekday()
    return d + timedelta(days=days_ahead)

def calculate_court_date(start_date: date, total_days: int = 0) -> Tuple[date, date]:
    """
    计算开庭日期
    Args:
        start_date: 起始日期
        total_days: 总天数（从第二天开始计算）
    Returns:
        (原定开庭日, 最终开庭日)
    """
    if total_days < 0:
        return start_date, start_date
        
    # 从第二天开始计算
    current_date = start_date + timedelta(days=1)
    
    # 累加天数
    if total_days > 0:
        current_date += timedelta(days=total_days)
    
    # 检查是否为周末并处理顺延
    if is_weekend(current_date):
        final_date = get_next_monday(current_date)
        return current_date, final_date
    
    return current_date, current_date