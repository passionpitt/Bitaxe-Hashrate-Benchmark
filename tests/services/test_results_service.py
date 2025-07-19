import pytest
from unittest.mock import patch, mock_open
from src.services.results_service import ResultsService
from src.config.constants import GREEN, RED, RESET
import json

@pytest.fixture
def results_service():
    return ResultsService(bitaxe_ip="http://192.168.1.100")

@pytest.fixture
def sample_results():
    return [
        {
            "coreVoltage": 1200,
            "frequency": 500,
            "averageHashRate": 1000.0,
            "averageTemperature": 60.0,
            "efficiencyJTH": 50.0,
            "averageVRTemp": 50.0
        },
        {
            "coreVoltage": 1100,
            "frequency": 450,
            "averageHashRate": 900.0,
            "averageTemperature": 55.0,
            "efficiencyJTH": 45.0,
            "averageVRTemp": 48.0
        },
        {
            "coreVoltage": 1000,
            "frequency": 400,
            "averageHashRate": 800.0,
            "averageTemperature": 50.0,
            "efficiencyJTH": 40.0
        }
    ]

def test_init(results_service):
    assert results_service.bitaxe_ip == "http://192.168.1.100"

def test_save_results_success(results_service, sample_results):
    with patch("builtins.open", mock_open()) as mocked_file:
        with patch("json.dump") as mocked_json_dump:
            results_service.save_results(sample_results)
            mocked_file.assert_called_once_with(
                "bitaxe_benchmark_results_192.168.1.100.json", "w", encoding="utf-8"
            )
            mocked_json_dump.assert_called_once()
            mocked_file().write.assert_not_called()
            with patch("builtins.print") as mocked_print:
                results_service.save_results(sample_results)
                mocked_print.assert_called_with(
                    GREEN + "Results saved to bitaxe_benchmark_results_192.168.1.100.json" + RESET
                )

def test_save_results_io_error(results_service, sample_results):
    with patch("builtins.open", side_effect=IOError("File error")):
        with patch("builtins.print") as mocked_print:
            results_service.save_results(sample_results)
            mocked_print.assert_called_with(
                RED + "Error saving results to file: File error" + RESET
            )

def test_format_results_with_vr_temp(sample_results):
    service = ResultsService("http://192.168.1.100")
    formatted = service._format_results(sample_results)
    assert formatted["all_results"] == sample_results
    assert len(formatted["top_performers"]) == 3
    assert formatted["top_performers"][0]["rank"] == 1
    assert formatted["top_performers"][0]["averageHashRate"] == pytest.approx(1000.0)
    assert formatted["top_performers"][2]["averageHashRate"] == pytest.approx(800.0)
    assert len(formatted["most_efficient"]) == 3
    assert formatted["most_efficient"][0]["rank"] == 1
    assert formatted["most_efficient"][0]["efficiencyJTH"] == pytest.approx(40.0)
    assert formatted["most_efficient"][2]["efficiencyJTH"] == pytest.approx(50.0)

def test_format_results_fewer_than_five():
    service = ResultsService("http://192.168.1.100")
    single_result = [{
        "coreVoltage": 1200,
        "frequency": 500,
        "averageHashRate": 1000.0,
        "averageTemperature": 60.0,
        "efficiencyJTH": 50.0
    }]
    formatted = service._format_results(single_result)
    assert len(formatted["top_performers"]) == 1
    assert formatted["top_performers"][0]["rank"] == 1
    assert len(formatted["most_efficient"]) == 1
    assert formatted["most_efficient"][0]["rank"] == 1

def test_print_results_summary_empty(results_service):
    with patch("builtins.print") as mocked_print:
        results_service.print_results_summary([])
        mocked_print.assert_called_with(
            RED + "No valid results were found during benchmarking." + RESET
        )

def test_print_results_summary_with_results(results_service, sample_results, capsys):
    results_service.print_results_summary(sample_results)
    captured = capsys.readouterr()
    output = captured.out
    assert "Top 5 Highest Hashrate Settings:" in output
    assert "Rank 1:" in output
    assert "Core Voltage: 1200mV" in output
    assert "Frequency: 500MHz" in output
    assert "Average Hashrate: 1000.00 GH/s" in output
    assert "Average Temperature: 60.00°C" in output
    assert "Efficiency: 50.00 J/TH" in output
    assert "Average VR Temperature: 50.00°C" in output
    assert "Rank 3:" in output
    assert "Core Voltage: 1000mV" in output
    assert "Top 5 Most Efficient Settings:" in output
    assert "Efficiency: 40.00 J/TH" in output

def test_print_results_summary_no_vr_temp(results_service, capsys):
    results = [{
        "coreVoltage": 1200,
        "frequency": 500,
        "averageHashRate": 1000.0,
        "averageTemperature": 60.0,
        "efficiencyJTH": 50.0
    }]
    results_service.print_results_summary(results)
    captured = capsys.readouterr()
    output = captured.out
    assert "Average VR Temperature" not in output
    assert "Core Voltage: 1200mV" in output
    assert "Efficiency: 50.00 J/TH" in output
