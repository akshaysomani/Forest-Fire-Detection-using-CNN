# Dashboard Analytics Engine Guide

This document describes the calculations, mathematical models, and trend mapping engines used to drive the analytical views.

---

## 1. Classification Verification Accuracy

To compile accuracy indicators, the application compares CNN model outputs against manual verification logs compiled by Forest Officers:

- **True Positives (TP)**: Model predicted `fire` and human verified `fire` (is_verified_fire = True).
- **True Negatives (TN)**: Model predicted `non-fire` and human verified `non-fire` (is_verified_fire = False).
- **False Positives (FP)**: Model predicted `fire` and human verified `non-fire` (is_verified_fire = False).
- **False Negatives (FN)**: Model predicted `non-fire` and human verified `fire` (is_verified_fire = True).

The engine runs a consolidated SQL projection query calculating:

$$\text{Accuracy} = \frac{\text{TP} + \text{TN}}{\text{TP} + \text{TN} + \text{FP} + \text{FN}}$$

*Note: If no verifications are logged yet, the API defaults to displaying `0.945` (94.5%) as a placeholder based on pre-deployment validation metrics.*

---

## 2. Trend Bucket Interpolation

When querying historical growth curves over a 30-day window, dates with no database uploads return no rows from the database. 

The `TrendAnalyzer` class maps the query output and loops through every calendar date within the 30-day window. If a date is missing, it dynamically inserts the date with a count of `0`. This guarantees clean, unbroken chart visualizations on frontend graphing libraries.

```
Raw Query Output:        [(2026-06-10, 5), (2026-06-12, 3)]
Interpolated Output:     [(2026-06-10, 5), (2026-06-11, 0), (2026-06-12, 3)]
```

---

## 3. Pre-computation and Optimizations

- **Date Grouping**: Database queries group counts using SQLite/PostgreSQL date conversion functions.
- **Index Support**: All aggregations are fully indexed on `prediction_label`, `is_verified_fire`, and `created_at`.
- **Response Caching**: Complex statistical curves are cached to prevent redundant, expensive aggregation runs on subsequent dashboard requests.
