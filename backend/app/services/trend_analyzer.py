from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Dict, Any


class TrendAnalyzer:
    @staticmethod
    def fill_missing_dates(trend_data: List[Tuple[str, int]], days: int = 30) -> List[Dict[str, Any]]:
        """
        Takes raw list of date tuples and fills in any missing dates in the rolling window
        with a count of 0 to ensure frontend chart continuity.
        """
        # Map existing records for quick lookup
        data_map = {date_str: count for date_str, count in trend_data}
        result = []

        now = datetime.now(timezone.utc)
        for i in range(days - 1, -1, -1):
            date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            count = data_map.get(date_str, 0)
            result.append({"date_bucket": date_str, "count": count})

        return result

    @staticmethod
    def aggregate_weekly_trends(daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rolls up a list of daily data objects into 7-day week summaries."""
        weekly_summary = []
        for i in range(0, len(daily_data), 7):
            chunk = daily_data[i : i + 7]
            if not chunk:
                break
            start_date = chunk[0]["date_bucket"]
            end_date = chunk[-1]["date_bucket"]
            total = sum(d["count"] for d in chunk)
            weekly_summary.append({"week_range": f"{start_date} to {end_date}", "count": total})
        return weekly_summary

    @staticmethod
    def aggregate_monthly_trends(daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rolls up daily data into month-level buckets based on the YYYY-MM key."""
        monthly_map: Dict[str, int] = {}
        for d in daily_data:
            month_key = d["date_bucket"][:7]  # Extract 'YYYY-MM'
            monthly_map[month_key] = monthly_map.get(month_key, 0) + d["count"]

        return [{"month": m, "count": c} for m, c in sorted(monthly_map.items())]


trend_analyzer = TrendAnalyzer()
