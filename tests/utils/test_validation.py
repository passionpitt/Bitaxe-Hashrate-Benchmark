import pytest
from src.utils.validation import validate_parameters
from src.config.constants import (
    RED, RESET, MAX_ALLOWED_FREQUENCY, MAX_ALLOWED_VOLTAGE,
    MIN_ALLOWED_FREQUENCY, MIN_ALLOWED_VOLTAGE
)

def test_validate_parameters_valid():
    validate_parameters(
        initial_voltage=1150,
        initial_frequency=525,
        benchmark_time=70,
        sample_interval=10
    )

def test_validate_parameters_voltage_too_high():
    with pytest.raises(ValueError) as exc_info:
        validate_parameters(
            initial_voltage=MAX_ALLOWED_VOLTAGE + 1,
            initial_frequency=525,
            benchmark_time=70,
            sample_interval=10
        )
    assert str(exc_info.value) == (
        f"{RED}Error: Initial voltage exceeds the maximum allowed value of "
        f"{MAX_ALLOWED_VOLTAGE} mV.{RESET}"
    )

def test_validate_parameters_voltage_too_low():
    with pytest.raises(ValueError) as exc_info:
        validate_parameters(
            initial_voltage=MIN_ALLOWED_VOLTAGE - 1,
            initial_frequency=525,
            benchmark_time=70,
            sample_interval=10
        )
    assert str(exc_info.value) == (
        f"{RED}Error: Initial voltage is below the minimum allowed value of "
        f"{MIN_ALLOWED_VOLTAGE} mV.{RESET}"
    )

def test_validate_parameters_frequency_too_high():
    with pytest.raises(ValueError) as exc_info:
        validate_parameters(
            initial_voltage=1150,
            initial_frequency=MAX_ALLOWED_FREQUENCY + 1,
            benchmark_time=70,
            sample_interval=10
        )
    assert str(exc_info.value) == (
        f"{RED}Error: Initial frequency exceeds the maximum allowed value of "
        f"{MAX_ALLOWED_FREQUENCY} MHz.{RESET}"
    )

def test_validate_parameters_frequency_too_low():
    with pytest.raises(ValueError) as exc_info:
        validate_parameters(
            initial_voltage=1150,
            initial_frequency=MIN_ALLOWED_FREQUENCY - 1,
            benchmark_time=70,
            sample_interval=10
        )
    assert str(exc_info.value) == (
        f"{RED}Error: Initial frequency is below the minimum allowed value of "
        f"{MIN_ALLOWED_FREQUENCY} MHz.{RESET}"
    )

def test_validate_parameters_insufficient_samples():
    with pytest.raises(ValueError) as exc_info:
        validate_parameters(
            initial_voltage=1150,
            initial_frequency=525,
            benchmark_time=60,
            sample_interval=10
        )
    assert str(exc_info.value) == (
        f"{RED}Error: Benchmark time is too short. Increase the benchmark time or decrease "
        f"the sample interval. At least 7 samples are required.{RESET}"
    )
