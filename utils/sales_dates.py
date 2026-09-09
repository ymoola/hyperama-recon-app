from datetime import date, timedelta

import pandas as pd


LONG_DATE_FORMAT = "dddd, mmmm d, yyyy"


def normalize_monthly_dates(date_values: pd.Series, reference_date=None) -> pd.Series:
    """Correct likely day/month swaps using batch and reporting-month context."""
    dates = pd.to_datetime(date_values, errors="raise")
    month_counts = dates.dt.to_period("M").value_counts()

    if month_counts.empty:
        return dates

    if month_counts.iloc[0] > len(dates) / 2:
        target_period = month_counts.index[0]
    elif len(dates) >= 3:
        reference_date = reference_date or date.today()
        previous_month = reference_date.replace(day=1) - timedelta(days=1)
        target_period = pd.Period(previous_month, freq="M")
    else:
        return dates

    def correct_swapped_date(value):
        if (
            value.to_period("M") != target_period
            and value.year == target_period.year
            and value.day == target_period.month
        ):
            try:
                return value.replace(month=target_period.month, day=value.month)
            except ValueError:
                return value
        return value

    return dates.apply(correct_swapped_date)


def format_long_dates(worksheet, first_data_row: int = 3) -> None:
    """Apply Excel's full long-date display to the worksheet's Date column."""
    for row_num in range(first_data_row, worksheet.max_row + 1):
        worksheet.cell(row=row_num, column=1).number_format = LONG_DATE_FORMAT
