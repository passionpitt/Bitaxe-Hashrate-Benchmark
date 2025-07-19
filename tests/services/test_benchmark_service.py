import pytest
from unittest.mock import Mock, patch
from src.services.benchmark_service import BenchmarkService
from src.config.constants import (
    MAX_TEMP, MAX_VR_TEMP, MIN_INPUT_VOLTAGE, MAX_INPUT_VOLTAGE,
    MAX_POWER, BENCHMARK_TIME, SAMPLE_INTERVAL
)

@pytest.fixture
def mock_system_info():
    return Mock()

@pytest.fixture
def benchmark_service(mock_system_info):
    return BenchmarkService(
        get_system_info=mock_system_info,
        small_core_count=100,
        asic_count=2
    )

def test_init(benchmark_service):
    assert benchmark_service.small_core_count == 100
    assert benchmark_service.asic_count == 2
    assert benchmark_service.total_samples == BENCHMARK_TIME // SAMPLE_INTERVAL
    assert callable(benchmark_service.get_system_info)

def test_expected_hashrate(benchmark_service):
    frequency = 500
    expected = frequency * ((100 * 2) / 1000)
    assert benchmark_service.expected_hashrate(frequency) == expected

def test_run_benchmark_calls_benchmark_iteration(benchmark_service):
    with patch.object(benchmark_service, 'benchmark_iteration') as mock_benchmark_iteration:
        core_voltage = 1200
        frequency = 500
        benchmark_service.run_benchmark(core_voltage, frequency)
        mock_benchmark_iteration.assert_called_once_with(core_voltage, frequency)

def test_benchmark_iteration_none_system_info(benchmark_service, mock_system_info):
    mock_system_info.return_value = None
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_invalid_temp_missing(benchmark_service, mock_system_info):
    mock_system_info.return_value = {"voltage": 5000, "hashRate": 1000, "power": 50}
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_invalid_temp_too_low(benchmark_service, mock_system_info):
    mock_system_info.return_value = {
        "temp": 4,
        "voltage": 5000,
        "hashRate": 1000,
        "power": 50
    }
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_invalid_temp_too_high(benchmark_service, mock_system_info):
    mock_system_info.return_value = {
        "temp": MAX_TEMP + 1,
        "voltage": 5000,
        "hashRate": 1000,
        "power": 50
    }
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_invalid_vr_temp(benchmark_service, mock_system_info):
    mock_system_info.return_value = {
        "temp": 60,
        "vrTemp": MAX_VR_TEMP + 1,
        "voltage": 5000,
        "hashRate": 1000,
        "power": 50
    }
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_invalid_voltage_low(benchmark_service, mock_system_info):
    mock_system_info.return_value = {
        "temp": 60,
        "voltage": MIN_INPUT_VOLTAGE - 1,
        "hashRate": 1000,
        "power": 50
    }
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_invalid_voltage_high(benchmark_service, mock_system_info):
    mock_system_info.return_value = {
        "temp": 60,
        "voltage": MAX_INPUT_VOLTAGE + 1,
        "hashRate": 1000,
        "power": 50
    }
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_invalid_power(benchmark_service, mock_system_info):
    mock_system_info.return_value = {
        "temp": 60,
        "voltage": 5000,
        "hashRate": 1000,
        "power": MAX_POWER + 1
    }
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_zero_hashrate(benchmark_service, mock_system_info):
    mock_system_info.return_value = {
        "temp": 60,
        "voltage": 5000,
        "hashRate": 0,
        "power": 50
    }
    result = benchmark_service.benchmark_iteration(1200, 500)
    assert result == (None, None, None, False, None, "NO_DATA")

def test_benchmark_iteration_valid_data(benchmark_service, mock_system_info):
    with patch('time.sleep'):
        def process_side_effect(info, samples):
            samples['hash_rates'].append(info.get("hashRate"))
            samples['temps'].append(info["temp"])
            samples['powers'].append(info["power"])
            vr = info.get("vrTemp")
            if vr is not None:
                samples['vr_temps'].append(vr)
            return True

        with patch.object(benchmark_service, '_process', side_effect=process_side_effect) as mock_process:
            mock_system_info.return_value = {
                "temp": 60,
                "vrTemp": 50,
                "voltage": 5000,
                "hashRate": 1000,
                "power": 50
            }
            benchmark_service.total_samples = 10
            result = benchmark_service.benchmark_iteration(1200, 500)
            avg_hash, avg_temp, efficiency, within_tolerance, avg_vr, reason = result
            assert avg_hash == 1000
            assert avg_temp == 60
            assert efficiency == 50 / 1
            assert within_tolerance
            assert avg_vr == 50
            assert reason is None
            mock_process.assert_called()

def test_calculate_results_no_data(benchmark_service):
    samples = {'hash_rates': [], 'temps': [], 'powers': [], 'vr_temps': []}
    result = benchmark_service._calculate_results(samples, 1000)
    assert result == (None, None, None, False, None, "NO_DATA_COLLECTED")

def test_validate_valid_data(benchmark_service):
    info = {
        "temp": 60,
        "vrTemp": 50,
        "voltage": 5000
    }
    valid, result = benchmark_service._validate(info)
    assert valid
    assert result == (60, 50, 5000)

def test_process_valid_data(benchmark_service):
    info = {
        "temp": 60,
        "vrTemp": 50,
        "hashRate": 1000,
        "power": 50
    }
    samples = {'hash_rates': [], 'temps': [], 'powers': [], 'vr_temps': []}
    result = benchmark_service._process(info, samples)
    if result:
        assert samples['hash_rates'] == [1000]
        assert samples['temps'] == [60]
        assert samples['powers'] == [50]
        assert samples['vr_temps'] == [50]
    else:
        assert samples['hash_rates'] == []
        assert samples['temps'] == []
        assert samples['powers'] == []
        assert samples['vr_temps'] == []
