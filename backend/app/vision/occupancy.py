"""Occupancy classification module.

Provides an abstract interface for parking slot occupancy prediction
along with a computer-vision feature-based classifier implementation.
"""

from abc import ABC, abstractmethod
from typing import Tuple
import cv2
import numpy as np
from pydantic import BaseModel, Field


class OccupancyPrediction(BaseModel):
    """Result of an occupancy prediction for a single ROI."""

    occupied: bool = Field(..., description="Whether the ROI is classified as occupied.")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence score between 0.0 and 1.0."
    )


class OccupancyClassifier(ABC):
    """Abstract base class for parking slot occupancy classifiers."""

    @abstractmethod
    def predict(self, roi: np.ndarray) -> OccupancyPrediction:
        """Classify cropped slot ROI image array as occupied or free.
        
        Args:
            roi: BGR numpy image array cropped to slot boundary.

        Returns:
            OccupancyPrediction containing boolean occupied flag and confidence score.
        """
        pass


class ComputerVisionOccupancyClassifier(OccupancyClassifier):
    """Computer vision feature classifier utilizing edge density, texture variance, and color contrast.
    
    Computes visual features (Canny edge density, Laplacian variance, grayscale intensity std-dev)
    to determine whether a parking slot contains a vehicle.
    """

    def __init__(
        self,
        edge_threshold: float = 0.08,
        laplacian_threshold: float = 120.0,
        combined_threshold: float = 0.40,
    ) -> None:
        self.edge_threshold = edge_threshold
        self.laplacian_threshold = laplacian_threshold
        self.combined_threshold = combined_threshold

    def predict(self, roi: np.ndarray) -> OccupancyPrediction:
        """Predict slot occupancy using computer vision feature extraction."""
        if roi is None or roi.size == 0 or roi.shape[0] < 5 or roi.shape[1] < 5:
            return OccupancyPrediction(occupied=False, confidence=0.50)

        # 1. Convert to grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi

        # 2. Compute Canny edge ratio (edge pixels / total pixels)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        edge_ratio = np.count_nonzero(edges) / float(edges.size)

        # 3. Compute Laplacian variance (measure of texture detail and sharpness)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # 4. Compute grayscale intensity standard deviation
        gray_std = float(np.std(gray))

        # 5. Normalize features into [0, 1] range
        norm_edge = min(1.0, edge_ratio / (self.edge_threshold * 2.0))
        norm_lap = min(1.0, laplacian_var / (self.laplacian_threshold * 2.0))
        norm_std = min(1.0, gray_std / 60.0)

        # 6. Weighted feature combination score
        occupancy_score = (norm_edge * 0.45) + (norm_lap * 0.35) + (norm_std * 0.20)
        occupancy_score = float(np.clip(occupancy_score, 0.0, 1.0))

        occupied = occupancy_score >= self.combined_threshold

        # Compute confidence score based on distance from threshold
        dist = abs(occupancy_score - self.combined_threshold)
        confidence = float(np.clip(0.60 + (dist * 0.85), 0.60, 0.98))

        return OccupancyPrediction(
            occupied=occupied,
            confidence=round(confidence, 2),
        )


class MockOccupancyClassifier(OccupancyClassifier):
    """Mock classifier for deterministic testing."""

    def __init__(self, default_occupied: bool = False, confidence: float = 0.90) -> None:
        self.default_occupied = default_occupied
        self.confidence = confidence

    def predict(self, roi: np.ndarray) -> OccupancyPrediction:
        return OccupancyPrediction(
            occupied=self.default_occupied,
            confidence=self.confidence,
        )
