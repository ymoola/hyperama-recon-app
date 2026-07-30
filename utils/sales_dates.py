import pandas as pd


LONG_DATE_FORMAT = "dddd, mmmm d, yyyy"


def normalize_monthly_dates(date_values: pd.Series) -> pd.Series:
    """Correct likely day/month swaps using the report's dominant month."""
    dates = pd.to_datetime(date_values, errors="raise")
    month_counts = dates.dt.month.value_counts()

    if month_counts.empty or month_counts.iloc[0] <= len(dates) / 2:
        return dates

    dominant_month = int(month_counts.index[0])

    def correct_swapped_date(value):
        if value.month != dominant_month and value.day == dominant_month:
            try:
                return value.replace(month=dominant_month, day=value.month)
            except ValueError:
                return value
        return value

    return dates.apply(correct_swapped_date)


def format_long_dates(worksheet, first_data_row: int = 3) -> None:
    """Apply Excel's full long-date display to the worksheet's Date column."""
    for row_num in range(first_data_row, worksheet.max_row + 1):
        worksheet.cell(row=row_num, column=1).number_format = LONG_DATE_FORMAT
