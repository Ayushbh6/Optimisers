"""Shared physical movement calculation for scalar and full-data replay."""
import numpy as np


def stock_movements(opening: np.ndarray, arrivals: np.ndarray, targets: np.ndarray, returns: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Arrivals precede purchases; external returns enter only at day-end."""
    shelf = opening + arrivals
    fulfilled = np.minimum(shelf, targets)
    return fulfilled, shelf - fulfilled + returns, shelf > fulfilled
