from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def tokyo_today():
    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


def monday(day):
    return day - timedelta(days=day.weekday())
