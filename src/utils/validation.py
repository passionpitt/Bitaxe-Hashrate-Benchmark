"""Validation utilities for benchmark parameters."""

from src.constants import (
    RED, RESET, MAX_ALLOWED_FREQUENCY,
    MAX_ALLOWED_VOLTAGE, MIN_ALLOWED_FREQUENCY,
    MIN_ALLOWED_VOLTAGE
)

def validate_parameters(initial_voltage, initial_frequency, benchmark_time, sample_interval):
    """Validate argument parameters."""
    def error(message: str) -> None:
        raise ValueError(RED + f"Error: {message}" + RESET)

    # Voltage checks
    if initial_voltage > MAX_ALLOWED_VOLTAGE:
        error(
            f"Initial voltage exceeds the maximum allowed value of "
            f"{MAX_ALLOWED_VOLTAGE} mV."
        )

    if initial_voltage < MIN_ALLOWED_VOLTAGE:
        error(
            f"Initial voltage is below the minimum allowed value of "
            f"{MIN_ALLOWED_VOLTAGE} mV."
        )

    # Frequency checks
    if initial_frequency > MAX_ALLOWED_FREQUENCY:
        error(
            f"Initial frequency exceeds the maximum allowed value of "
            f"{MAX_ALLOWED_FREQUENCY} MHz."
        )
    if initial_frequency < MIN_ALLOWED_FREQUENCY:
        error(
            f"Initial frequency is below the minimum allowed value of "
            f"{MIN_ALLOWED_FREQUENCY} MHz."
        )

    # Sample count check
    if benchmark_time / sample_interval < 7:
        error(
            "Benchmark time is too short. Increase the benchmark time or decrease "
            "the sample interval. At least 7 samples are required."
        )
