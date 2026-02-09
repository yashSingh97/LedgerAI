from typing import Optional
from datetime import datetime, timedelta


WEEKDAY_INDEX = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
    "SUNDAY": 6,
}


def resolve_date_expression(date_expression: Optional[str]) -> str:
    """
    Resolves a controlled date_expression token into an ISO-8601 date (YYYY-MM-DD).
    
    This is ONLY for add_transaction operations (not query_transactions).

    Allowed date_expression values:
    - NULL or None → resolves to today
    - TODAY | YESTERDAY
    - LAST_MONDAY ... LAST_SUNDAY
    - THIS_MONDAY ... THIS_SUNDAY
    - LAST_WEEK | THIS_WEEK
    - LAST_MONTH | THIS_MONTH
    - LAST_YEAR | THIS_YEAR
    - ISO date string YYYY-MM-DD (if user explicitly provided it)

    Returns:
        str: Resolved date in YYYY-MM-DD format

    Raises:
        ValueError: If an unsupported token is provided
    """

    today = datetime.now().date()

    # 1️⃣ No date provided → default to today
    if date_expression in (None, "", "NULL"):
        return today.isoformat()

    # 2️⃣ Explicit ISO date → pass through (validate format)
    if isinstance(date_expression, str):
        try:
            datetime.strptime(date_expression, "%Y-%m-%d")
            return date_expression
        except ValueError:
            pass  # Not ISO, continue to token parsing

    token = date_expression.upper().strip()

    # 3️⃣ Simple relative days
    if token == "TODAY":
        return today.isoformat()

    if token == "YESTERDAY":
        return (today - timedelta(days=1)).isoformat()

    # 4️⃣ Week-based tokens
    if token == "LAST_WEEK":
        # Middle of last week (Monday to Sunday)
        # Use Wednesday of last week as representative date
        start_of_this_week = today - timedelta(days=today.weekday())  # This Monday
        middle_of_last_week = start_of_this_week - timedelta(days=4)  # Last Wednesday
        return middle_of_last_week.isoformat()

    if token == "THIS_WEEK":
        # Middle of this week (Monday to today)
        # Use Wednesday of this week, or today if before Wednesday
        start_of_this_week = today - timedelta(days=today.weekday())  # This Monday
        wednesday = start_of_this_week + timedelta(days=2)
        return min(wednesday, today).isoformat()

    # 5️⃣ Month-based tokens
    if token == "LAST_MONTH":
        # 15th of last month (middle of month as representative date)
        first_of_this_month = today.replace(day=1)
        last_month = first_of_this_month - timedelta(days=1)
        return last_month.replace(day=15).isoformat()

    if token == "THIS_MONTH":
        # 15th of this month, or today if before 15th
        middle_of_month = today.replace(day=15)
        return min(middle_of_month, today).isoformat()

    # 6️⃣ Year-based tokens
    if token == "LAST_YEAR":
        # July 1st of last year (middle of year)
        return today.replace(year=today.year - 1, month=7, day=1).isoformat()

    if token == "THIS_YEAR":
        # July 1st of this year, or today if before July
        middle_of_year = today.replace(month=7, day=1)
        return min(middle_of_year, today).isoformat()

    # 7️⃣ Specific weekday tokens: LAST_MONDAY, THIS_TUESDAY, etc.
    if "_" in token:
        parts = token.split("_", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid date_expression format: {date_expression}")

        direction, day = parts

        if day not in WEEKDAY_INDEX:
            raise ValueError(f"Invalid weekday in date_expression: {day}")

        if direction not in ("LAST", "THIS"):
            raise ValueError(f"Invalid date_expression direction: {direction} (must be LAST or THIS)")

        target_weekday = WEEKDAY_INDEX[day]
        today_weekday = today.weekday()

        if direction == "LAST":
            # Go back to the most recent occurrence of this weekday
            # If today is the weekday, go back 7 days
            delta_days = (today_weekday - target_weekday) % 7 or 7
            return (today - timedelta(days=delta_days)).isoformat()

        if direction == "THIS":
            # Most recent occurrence within this week (Monday to today)
            start_of_week = today - timedelta(days=today_weekday)  # This Monday
            target_date = start_of_week + timedelta(days=target_weekday)
            
            # If target day hasn't occurred yet this week, it's invalid for add_transaction
            if target_date > today:
                raise ValueError(
                    f"Cannot add transaction for {day} of this week - that day hasn't occurred yet. "
                    f"Use LAST_{day} instead."
                )
            
            return target_date.isoformat()

    # 8️⃣ Anything else is invalid
    raise ValueError(f"Unrecognized date_expression: {date_expression}")