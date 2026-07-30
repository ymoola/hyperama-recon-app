import tempfile
import unittest
from datetime import datetime

import pandas as pd
from openpyxl import Workbook, load_workbook

from utils.sales_dates import format_long_dates, normalize_monthly_dates


class SalesDateTests(unittest.TestCase):
    def test_corrects_day_month_swaps_in_monthly_batch(self):
        dates = pd.Series([
            "2026-02-07",
            "2026-07-03",
            "2026-07-04",
            "2026-07-05",
            "2026-09-07",
        ])

        normalized = normalize_monthly_dates(dates)

        self.assertEqual(normalized.dt.strftime("%Y-%m-%d").tolist(), [
            "2026-07-02",
            "2026-07-03",
            "2026-07-04",
            "2026-07-05",
            "2026-07-09",
        ])

    def test_excel_uses_real_long_date_cells(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Monthly Report"
        worksheet.append([""])
        worksheet.append(["Date"])
        worksheet.append([datetime(2026, 7, 13)])
        format_long_dates(worksheet)

        with tempfile.NamedTemporaryFile(suffix=".xlsx") as output:
            workbook.save(output.name)
            reopened = load_workbook(output.name)
            cell = reopened["Monthly Report"]["A3"]

        self.assertIsInstance(cell.value, datetime)
        self.assertEqual(cell.value.date().isoformat(), "2026-07-13")
        self.assertEqual(cell.number_format, "dddd, mmmm d, yyyy")


if __name__ == "__main__":
    unittest.main()
