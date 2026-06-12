class MetricsCalculator:
    @staticmethod
    def calculate_growth_percentage(current_val: float, previous_val: float) -> float:
        """
        Calculates the percentage rate of growth from a previous period to a current period.
        Handles zero-values gracefully.
        """
        if previous_val == 0.0:
            return 100.0 if current_val > 0.0 else 0.0
        
        diff = current_val - previous_val
        growth = (diff / previous_val) * 100
        return round(float(growth), 2)

    @staticmethod
    def calculate_accuracy(
        tp: int, tn: int, fp: int, fn: int
    ) -> float:
        """Computes basic model classification accuracy from confusion matrix parameters."""
        total = tp + tn + fp + fn
        if total == 0:
            return 0.0
        return round(float(tp + tn) / float(total), 4)


metrics_calculator = MetricsCalculator()
