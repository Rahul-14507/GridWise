"""Priority scoring module.

Combines individual normalized urgency factors into a single composite priority score in range [0.0, 1.0].
Formula:
    priority = (w_soc * soc_urgency) + (w_dep * departure_urgency) + (w_def * energy_deficit) + (w_wait * waiting_score)
"""


class PriorityScorer:
    """Calculates composite priority scores for Electric Vehicles based on configurable weights."""

    @staticmethod
    def calculate_priority(
        soc_urgency: float,
        departure_urgency: float,
        energy_deficit_score: float,
        waiting_score: float,
        w_soc: float = 0.35,
        w_departure: float = 0.40,
        w_deficit: float = 0.15,
        w_waiting: float = 0.10,
    ) -> float:
        """Compute the weighted composite priority score.

        Args:
            soc_urgency: Normalized SoC urgency component [0.0, 1.0].
            departure_urgency: Normalized departure urgency component [0.0, 1.0].
            energy_deficit_score: Normalized energy deficit score [0.0, 1.0].
            waiting_score: Normalized waiting fairness score [0.0, 1.0].
            w_soc: Weight for SoC urgency (default 0.35).
            w_departure: Weight for departure urgency (default 0.40).
            w_deficit: Weight for energy deficit score (default 0.15).
            w_waiting: Weight for waiting fairness score (default 0.10).

        Returns:
            Composite priority score float in range [0.0, 1.0].
        """
        if w_soc < 0.0 or w_departure < 0.0 or w_deficit < 0.0 or w_waiting < 0.0:
            raise ValueError("Priority weights must all be non-negative")

        total_weight = w_soc + w_departure + w_deficit + w_waiting
        if not (0.999 <= total_weight <= 1.001):
            raise ValueError(f"Priority weights must sum to 1.0 (got {total_weight:.4f})")

        score = (
            (w_soc * soc_urgency)
            + (w_departure * departure_urgency)
            + (w_deficit * energy_deficit_score)
            + (w_waiting * waiting_score)
        )

        return round(max(0.0, min(1.0, score)), 4)
