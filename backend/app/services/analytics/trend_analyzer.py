from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple


class TrendAnalyzer:
    @staticmethod
    def fill_missing_dates(trend_data: List[Tuple[str, float]], days: int = 30) -> List[Dict[str, Any]]:
        """Takes a raw list of date tuples and fills in missing dates with value 0.0."""
        data_map = {date_str: val for date_str, val in trend_data}
        result = []

        now = datetime.now(timezone.utc)
        for i in range(days - 1, -1, -1):
            date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            val = data_map.get(date_str, 0.0)
            result.append({"date_bucket": date_str, "value": float(val)})

        return result

    @staticmethod
    def calculate_moving_average(daily_data: List[Dict[str, Any]], window_size: int = 7) -> List[Dict[str, Any]]:
        """Compute window-size rolling moving averages across daily metric logs."""
        result = []
        for idx, item in enumerate(daily_data):
            start = max(0, idx - window_size + 1)
            subset = daily_data[start : idx + 1]
            avg = sum(d["value"] for d in subset) / len(subset) if subset else 0.0
            result.append({"date_bucket": item["date_bucket"], "value": round(avg, 4)})
        return result

    @staticmethod
    def aggregate_weekly_trends(daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Roll up daily data into 7-day week summary buckets."""
        weekly_summary = []
        for i in range(0, len(daily_data), 7):
            chunk = daily_data[i : i + 7]
            if not chunk:
                break
            start_date = chunk[0]["date_bucket"]
            end_date = chunk[-1]["date_bucket"]
            total = sum(d["value"] for d in chunk)
            weekly_summary.append({"week_range": f"{start_date} to {end_date}", "value": total})
        return weekly_summary


trend_analyzer = TrendAnalyzer()
