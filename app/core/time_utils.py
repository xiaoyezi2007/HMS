from datetime import datetime, date
from zoneinfo import ZoneInfo

# Beijing time helper utilities
_TZ = ZoneInfo("Asia/Shanghai")

def now_bj() -> datetime:
    """Return current time in Beijing as naive datetime (for MySQL DATETIME)."""
    return datetime.now(_TZ).replace(tzinfo=None)


def today_bj() -> date:
    """Return current date in Beijing."""
    return datetime.now(_TZ).date()
