import pytest
import signal
from unittest.mock import Mock, patch, call
from src.services.bitaxe_benchmark_service import BitaxeBenchmark
from src.config.constants import (BENCHMARK_TIME, SAMPLE_INTERVAL, VOLTAGE_INCREMENT, FREQUENCY_INCREMENT, MAX_ALLOWED_VOLTAGE, MAX_ALLOWED_FREQUENCY, YELLOW, GREEN, RESET)

@pytest.fixture
def bitaxe_benchmark():
    with patch("src.services.bitaxe_benchmark_service.parse_arguments") as mock_parse_args, \
         patch("src.services.bitaxe_benchmark_service.SystemService") as mock_system_service, \
         patch("src.services.bitaxe_benchmark_service.ResultsService") as mock_results_service:
        mock_args = Mock(
            bitaxe_ip="192.168.2.26",
            voltage=1150,
            frequency=525
        )
        mock_parse_args.return_value = mock_args

        mock_system_service_instance = Mock()
        mock_system_service_instance.default_voltage = 1100
        mock_system_service_instance.default_frequency = 500
        mock_system_service_instance.small_core_count = 128
        mock_system_service_instance.asic_count = 1
        mock_system_service_instance.get_system_info.return_value = {"info": "mocked"}
        mock_system_service.return_value = mock_system_service_instance

        mock_results_service_instance = Mock()
        mock_results_service.return_value = mock_results_service_instance

        benchmark = BitaxeBenchmark()
        yield benchmark

def test_init(capsys, bitaxe_benchmark):
    assert bitaxe_benchmark.bitaxe_ip == "http://192.168.2.26"
    assert bitaxe_benchmark.initial_voltage == 1150
    assert bitaxe_benchmark.initial_frequency == 525
    assert bitaxe_benchmark.results == []
    assert bitaxe_benchmark.system_reset_done is False
    assert bitaxe_benchmark.handling_interrupt is False
    assert bitaxe_benchmark.system_service is not None
    assert bitaxe_benchmark.results_service is not None

    captured = capsys.readouterr()
    assert "Initializing BitaxeBenchmark..." in captured.out
    assert "Parsed arguments: ip=192.168.2.26, voltage=1150, frequency=525" in captured.out

def test_setup_success(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.validate_parameters") as mock_validate, \
         patch("signal.signal") as mock_signal:
        bitaxe_benchmark.setup()

        mock_validate.assert_called_once_with(
            initial_voltage=1150,
            initial_frequency=525,
            benchmark_time=BENCHMARK_TIME,
            sample_interval=SAMPLE_INTERVAL
        )
        bitaxe_benchmark.system_service.fetch_default_settings.assert_called_once()
        mock_signal.assert_called_once_with(signal.SIGINT, bitaxe_benchmark._handle_sigint)

        captured = capsys.readouterr()
        assert "Starting setup..." in captured.out
        assert "Validating parameters..." in captured.out
        assert "Parameters validated successfully." in captured.out
        assert "Fetching default settings..." in captured.out
        assert "Registering signal handler..." in captured.out
        assert "Setup completed." in captured.out

def test_setup_validation_failure(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.validate_parameters") as mock_validate:
        mock_validate.side_effect = ValueError("Validation error")
        with pytest.raises(ValueError, match="Validation error"):
            bitaxe_benchmark.setup()

        captured = capsys.readouterr()
        assert "Starting setup..." in captured.out
        assert "Validating parameters..." in captured.out
        assert "Error in setup: Validation error" in captured.out

def test_handle_sigint_no_results(capsys, bitaxe_benchmark):
    with patch("sys.exit") as mock_exit:
        bitaxe_benchmark._handle_sigint(signal.SIGINT, None)

        bitaxe_benchmark.system_service.set_system_settings.assert_called_once_with(
            bitaxe_benchmark.system_service.default_voltage,
            bitaxe_benchmark.system_service.default_frequency
        )
        bitaxe_benchmark.results_service.save_results.assert_not_called()
        mock_exit.assert_called_once_with(0)

        captured = capsys.readouterr()
        assert "Benchmarking interrupted by user." in captured.out
        assert "No valid benchmarking results found. Applying predefined default settings." in captured.out
        assert "Bitaxe reset to best or default settings and results saved." not in captured.out

def test_handle_sigint_with_results(capsys, bitaxe_benchmark):
    bitaxe_benchmark.results = [
        {"coreVoltage": 1150, "frequency": 525, "averageHashRate": 100}
    ]
    with patch("sys.exit") as mock_exit:
        bitaxe_benchmark._handle_sigint(signal.SIGINT, None)

        bitaxe_benchmark.system_service.set_system_settings.assert_called_once_with(1150, 525)
        bitaxe_benchmark.results_service.save_results.assert_called_once_with(bitaxe_benchmark.results)
        mock_exit.assert_called_once_with(0)

        captured = capsys.readouterr()
        assert "Benchmarking interrupted by user." in captured.out
        assert "Applying the best settings from benchmarking:" in captured.out
        assert "Core Voltage: 1150mV" in captured.out
        assert "Frequency: 525MHz" in captured.out
        assert "Bitaxe reset to best or default settings and results saved." in captured.out

def test_reset_to_best_setting_no_results(capsys, bitaxe_benchmark):
    bitaxe_benchmark._reset_to_best_setting()

    bitaxe_benchmark.system_service.set_system_settings.assert_called_once_with(
        bitaxe_benchmark.system_service.default_voltage,
        bitaxe_benchmark.system_service.default_frequency
    )
    captured = capsys.readouterr()
    assert "Resetting to best or default settings..." in captured.out
    assert "No valid benchmarking results found. Applying predefined default settings." in captured.out

def test_reset_to_best_setting_with_results(capsys, bitaxe_benchmark):
    bitaxe_benchmark.results = [
        {"coreVoltage": 1150, "frequency": 525, "averageHashRate": 100},
        {"coreVoltage": 1200, "frequency": 550, "averageHashRate": 120}
    ]
    bitaxe_benchmark._reset_to_best_setting()

    bitaxe_benchmark.system_service.set_system_settings.assert_called_once_with(1200, 550)
    captured = capsys.readouterr()
    assert "Resetting to best or default settings..." in captured.out
    assert "Applying the best settings from benchmarking:" in captured.out
    assert "Core Voltage: 1200mV" in captured.out
    assert "Frequency: 550MHz" in captured.out

def test_run_invalid_result(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.BenchmarkService") as mock_benchmark_service, \
         patch.object(bitaxe_benchmark, "setup") as mock_setup, \
         patch.object(bitaxe_benchmark, "_reset_to_best_setting") as mock_reset:

        mock_benchmark_instance = Mock()
        mock_benchmark_instance.benchmark_iteration.return_value = (
            None,  # averageHashRate
            None,  # averageTemperature
            None,  # efficiencyJTH
            False, # hashrate_ok
            None   # averageVRTemp
        )
        mock_benchmark_service.return_value = mock_benchmark_instance

        bitaxe_benchmark.run()

        mock_setup.assert_called_once()
        mock_benchmark_service.assert_called_once_with(
            bitaxe_benchmark.system_service.get_system_info,
            bitaxe_benchmark.system_service.small_core_count,
            bitaxe_benchmark.system_service.asic_count
        )
        bitaxe_benchmark.system_service.set_system_settings.assert_called_once_with(1150, 525)
        mock_benchmark_instance.benchmark_iteration.assert_called_once_with(1150, 525)
        mock_reset.assert_called_once()
        bitaxe_benchmark.results_service.save_results.assert_called()
        bitaxe_benchmark.results_service.print_results_summary.assert_called_once_with(bitaxe_benchmark.results)

        captured = capsys.readouterr()
        assert "Starting benchmarking process..." in captured.out
        assert "DISCLAIMER:" in captured.out
        assert "Initializing BenchmarkService..." in captured.out
        assert "Starting benchmark loop with voltage=1150mV, frequency=525MHz" in captured.out
        assert "Reached thermal or stability limits. Stopping further testing." in captured.out
        assert "Finalizing: Resetting to best or default settings..." in captured.out
        assert "Finalizing: Saving results..." in captured.out
        assert "Benchmarking completed." in captured.out

def test_run_valid_result_hashrate_ok(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.BenchmarkService") as mock_benchmark_service, \
         patch.object(bitaxe_benchmark, "setup") as mock_setup, \
         patch.object(bitaxe_benchmark, "_reset_to_best_setting") as mock_reset:

        mock_benchmark_instance = Mock()
        mock_benchmark_instance.benchmark_iteration.side_effect = [
            (100, 50, 0.5, True, 45),
            (None, None, None, False, None)
        ]
        mock_benchmark_service.return_value = mock_benchmark_instance

        bitaxe_benchmark.run()

        mock_setup.assert_called_once()
        mock_benchmark_service.assert_called_once_with(
            bitaxe_benchmark.system_service.get_system_info,
            bitaxe_benchmark.system_service.small_core_count,
            bitaxe_benchmark.system_service.asic_count
        )
        bitaxe_benchmark.system_service.set_system_settings.assert_has_calls([
            call(1150, 525),
            call(1150, 525 + FREQUENCY_INCREMENT)
        ])
        mock_benchmark_instance.benchmark_iteration.assert_has_calls([
            call(1150, 525),
            call(1150, 525 + FREQUENCY_INCREMENT)
        ])
        mock_reset.assert_called_once()
        bitaxe_benchmark.results_service.save_results.assert_called()
        bitaxe_benchmark.results_service.print_results_summary.assert_called_once_with(bitaxe_benchmark.results)

        captured = capsys.readouterr()
        assert "Starting benchmarking process..." in captured.out
        assert "DISCLAIMER:" in captured.out
        assert "Initializing BenchmarkService..." in captured.out
        assert "Starting benchmark loop with voltage=1150mV, frequency=525MHz" in captured.out
        assert f"Increasing frequency to {525 + FREQUENCY_INCREMENT}MHz" in captured.out
        assert "Reached thermal or stability limits. Stopping further testing." in captured.out
        assert "Saving results..." in captured.out
        assert "Benchmarking completed." in captured.out
        assert len(bitaxe_benchmark.results) == 1
        assert bitaxe_benchmark.results[0]["coreVoltage"] == 1150
        assert bitaxe_benchmark.results[0]["frequency"] == 525
        assert bitaxe_benchmark.results[0]["averageHashRate"] == 100
        assert bitaxe_benchmark.results[0]["averageTemperature"] == 50
        assert bitaxe_benchmark.results[0]["efficiencyJTH"] == 0.5
        assert bitaxe_benchmark.results[0]["averageVRTemp"] == 45

def test_run_valid_result_hashrate_not_ok(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.BenchmarkService") as mock_benchmark_service, \
         patch.object(bitaxe_benchmark, "setup") as mock_setup, \
         patch.object(bitaxe_benchmark, "_reset_to_best_setting") as mock_reset:

        mock_benchmark_instance = Mock()
        mock_benchmark_instance.benchmark_iteration.side_effect = [
            (100, 50, 0.5, False, 45),
            (None, None, None, False, None)
        ]
        mock_benchmark_service.return_value = mock_benchmark_instance

        bitaxe_benchmark.run()

        mock_setup.assert_called_once()
        mock_benchmark_service.assert_called_once_with(
            bitaxe_benchmark.system_service.get_system_info,
            bitaxe_benchmark.system_service.small_core_count,
            bitaxe_benchmark.system_service.asic_count
        )
        bitaxe_benchmark.system_service.set_system_settings.assert_has_calls([
            call(1150, 525),
            call(1150 + VOLTAGE_INCREMENT, 525 - FREQUENCY_INCREMENT)
        ])
        mock_benchmark_instance.benchmark_iteration.assert_has_calls([
            call(1150, 525),
            call(1150 + VOLTAGE_INCREMENT, 525 - FREQUENCY_INCREMENT)
        ])
        mock_reset.assert_called_once()
        bitaxe_benchmark.results_service.save_results.assert_called()
        bitaxe_benchmark.results_service.print_results_summary.assert_called_once_with(bitaxe_benchmark.results)

        captured = capsys.readouterr()
        assert "Starting benchmarking process..." in captured.out
        assert "DISCLAIMER:" in captured.out
        assert "Initializing BenchmarkService..." in captured.out
        assert "Starting benchmark loop with voltage=1150mV, frequency=525MHz" in captured.out
        assert f"Hashrate too low. Decreasing frequency to {525 - FREQUENCY_INCREMENT}MHz and increasing voltage to {1150 + VOLTAGE_INCREMENT}mV" in captured.out
        assert "Reached thermal or stability limits. Stopping further testing." in captured.out
        assert "Saving results..." in captured.out
        assert "Benchmarking completed." in captured.out
        assert len(bitaxe_benchmark.results) == 1
        assert bitaxe_benchmark.results[0]["coreVoltage"] == 1150
        assert bitaxe_benchmark.results[0]["frequency"] == 525
        assert bitaxe_benchmark.results[0]["averageHashRate"] == 100
        assert bitaxe_benchmark.results[0]["averageTemperature"] == 50
        assert bitaxe_benchmark.results[0]["efficiencyJTH"] == 0.5
        assert bitaxe_benchmark.results[0]["averageVRTemp"] == 45

def test_run_max_frequency(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.BenchmarkService") as mock_benchmark_service, \
         patch.object(bitaxe_benchmark, "setup") as mock_setup, \
         patch.object(bitaxe_benchmark, "_reset_to_best_setting") as mock_reset:
        # Mock BenchmarkService
        mock_benchmark_instance = Mock()
        mock_benchmark_instance.benchmark_iteration.return_value = (
            100, 50, 0.5, True, 45
        )
        mock_benchmark_service.return_value = mock_benchmark_instance

        bitaxe_benchmark.initial_frequency = MAX_ALLOWED_FREQUENCY
        bitaxe_benchmark.args.frequency = MAX_ALLOWED_FREQUENCY

        bitaxe_benchmark.run()

        mock_setup.assert_called_once()
        mock_benchmark_service.assert_called_once_with(
            bitaxe_benchmark.system_service.get_system_info,
            bitaxe_benchmark.system_service.small_core_count,
            bitaxe_benchmark.system_service.asic_count
        )
        bitaxe_benchmark.system_service.set_system_settings.assert_called_with(1150, MAX_ALLOWED_FREQUENCY)
        mock_benchmark_instance.benchmark_iteration.assert_called_with(1150, MAX_ALLOWED_FREQUENCY)
        mock_reset.assert_called_once()
        bitaxe_benchmark.results_service.save_results.assert_called()
        bitaxe_benchmark.results_service.print_results_summary.assert_called_once_with(bitaxe_benchmark.results)

        captured = capsys.readouterr()
        assert "Starting benchmarking process..." in captured.out
        assert "DISCLAIMER:" in captured.out
        assert "Initializing BenchmarkService..." in captured.out
        assert f"Starting benchmark loop with voltage=1150mV, frequency={MAX_ALLOWED_FREQUENCY}MHz" in captured.out
        assert "Reached max frequency. Stopping." in captured.out
        assert "Saving results..." in captured.out
        assert "Benchmarking completed." in captured.out
        assert len(bitaxe_benchmark.results) == 1

def test_run_max_voltage(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.BenchmarkService") as mock_benchmark_service, \
         patch.object(bitaxe_benchmark, "setup") as mock_setup, \
         patch.object(bitaxe_benchmark, "_reset_to_best_setting") as mock_reset:

        mock_benchmark_instance = Mock()
        mock_benchmark_instance.benchmark_iteration.return_value = (
            100, 50, 0.5, False, 45
        )
        mock_benchmark_service.return_value = mock_benchmark_instance

        bitaxe_benchmark.initial_voltage = MAX_ALLOWED_VOLTAGE
        bitaxe_benchmark.args.voltage = MAX_ALLOWED_VOLTAGE

        bitaxe_benchmark.run()

        mock_setup.assert_called_once()
        mock_benchmark_service.assert_called_once_with(
            bitaxe_benchmark.system_service.get_system_info,
            bitaxe_benchmark.system_service.small_core_count,
            bitaxe_benchmark.system_service.asic_count
        )
        bitaxe_benchmark.system_service.set_system_settings.assert_called_with(MAX_ALLOWED_VOLTAGE, 525)
        mock_benchmark_instance.benchmark_iteration.assert_called_with(MAX_ALLOWED_VOLTAGE, 525)
        mock_reset.assert_called_once()
        bitaxe_benchmark.results_service.save_results.assert_called()
        bitaxe_benchmark.results_service.print_results_summary.assert_called_once_with(bitaxe_benchmark.results)

        captured = capsys.readouterr()
        assert "Starting benchmarking process..." in captured.out
        assert "DISCLAIMER:" in captured.out
        assert "Initializing BenchmarkService..." in captured.out
        assert f"Starting benchmark loop with voltage={MAX_ALLOWED_VOLTAGE}mV, frequency=525MHz" in captured.out
        assert "Reached max voltage. Stopping." in captured.out
        assert "Saving results..." in captured.out
        assert "Benchmarking completed." in captured.out
        assert len(bitaxe_benchmark.results) == 1

def test_run_with_exception(capsys, bitaxe_benchmark):
    with patch("src.services.bitaxe_benchmark_service.BenchmarkService") as mock_benchmark_service, \
         patch.object(bitaxe_benchmark, "setup") as mock_setup:
        mock_benchmark_service.side_effect = Exception("Benchmark error")

        bitaxe_benchmark.run()

        mock_setup.assert_called_once()
        bitaxe_benchmark.results_service.save_results.assert_called()
        bitaxe_benchmark.results_service.print_results_summary.assert_called_once_with(bitaxe_benchmark.results)

        captured = capsys.readouterr()
        assert "Starting benchmarking process..." in captured.out
        assert "An unexpected error occurred: Benchmark error" in captured.out
        assert "Finalizing: Resetting to best or default settings..." in captured.out
        assert "Finalizing: Saving results..." in captured.out
        assert "Benchmarking completed." in captured.out
