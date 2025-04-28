import pytest
from unittest.mock import patch, Mock, call
from src.services.system_service import SystemService
from src.config.constants import (
    MIN_ALLOWED_VOLTAGE, MIN_ALLOWED_FREQUENCY, GREEN, YELLOW, RED, RESET
)
from requests.exceptions import RequestException

@pytest.fixture
def system_service():
    return SystemService(bitaxe_ip="http://192.168.1.100")

@pytest.fixture
def mock_requests_get():
    with patch("requests.get") as mocked_get:
        yield mocked_get

@pytest.fixture
def mock_requests_patch():
    with patch("requests.patch") as mocked_patch:
        yield mocked_patch

@pytest.fixture
def mock_requests_post():
    with patch("requests.post") as mocked_post:
        yield mocked_post

def test_init(system_service):
    assert system_service.bitaxe_ip == "http://192.168.1.100"
    assert system_service.default_voltage == MIN_ALLOWED_VOLTAGE
    assert system_service.default_frequency == MIN_ALLOWED_FREQUENCY
    assert system_service.small_core_count == 0
    assert system_service.asic_count == 0

def test_fetch_default_settings_success(system_service, mock_requests_get):
    mock_response = Mock()
    mock_response.json.return_value = {
        "coreVoltage": 1200,
        "frequency": 500,
        "smallCoreCount": 100,
        "asicCount": 2
    }
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    with patch("builtins.print") as mocked_print:
        system_service.fetch_default_settings()
        mock_requests_get.assert_called_once_with(
            "http://192.168.1.100/api/system/info", timeout=10
        )
        assert system_service.default_voltage == 1200
        assert system_service.default_frequency == 500
        assert system_service.small_core_count == 100
        assert system_service.asic_count == 2
        mocked_print.assert_called_with(
            GREEN + "Current settings determined:\n"
                    f"  Core Voltage: 1200mV\n"
                    f"  Frequency: 500MHz\n"
                    f"  ASIC Configuration: 200 total cores" + RESET
        )

def test_fetch_default_settings_request_exception(system_service, mock_requests_get):
    mock_requests_get.side_effect = RequestException("Connection error")
    with patch("builtins.print") as mocked_print:
        system_service.fetch_default_settings()
        mock_requests_get.assert_called_once_with(
            "http://192.168.1.100/api/system/info", timeout=10
        )
        assert system_service.default_voltage == MIN_ALLOWED_VOLTAGE
        assert system_service.default_frequency == MIN_ALLOWED_FREQUENCY
        assert system_service.small_core_count == 0
        assert system_service.asic_count == 0
        mocked_print.assert_called_with(
            RED + "Error fetching default system settings: Connection error. Using fallback defaults." + RESET
        )

def test_fetch_default_settings_value_error(system_service, mock_requests_get):
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    with patch("builtins.print") as mocked_print:
        system_service.fetch_default_settings()
        mock_requests_get.assert_called_once_with(
            "http://192.168.1.100/api/system/info", timeout=10
        )
        assert system_service.default_voltage == MIN_ALLOWED_VOLTAGE
        assert system_service.default_frequency == MIN_ALLOWED_FREQUENCY
        assert system_service.small_core_count == 0
        assert system_service.asic_count == 0
        mocked_print.assert_called_with(
            RED + "Invalid data in system settings: Invalid JSON. Using fallback defaults." + RESET
        )

def test_get_system_info_success(system_service, mock_requests_get):
    mock_response = Mock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    result = system_service.get_system_info()
    mock_requests_get.assert_called_once_with(
        "http://192.168.1.100/api/system/info", timeout=10
    )
    assert result == {"status": "ok"}

def test_get_system_info_retries_and_fails(system_service, mock_requests_get):
    mock_requests_get.side_effect = RequestException("Connection error")
    with patch("builtins.print") as mocked_print:
        with patch("time.sleep") as mocked_sleep:
            result = system_service.get_system_info()
            assert mock_requests_get.call_count == 3
            mock_requests_get.assert_called_with(
                "http://192.168.1.100/api/system/info", timeout=10
            )
            assert mocked_sleep.call_count == 3
            mocked_sleep.assert_called_with(5)
            assert result is None
            expected_calls = [
                (YELLOW + f"Error fetching system info (attempt {i}/{3}): Connection error" + RESET,)
                for i in [1, 2, 3]
            ]
            mocked_print.assert_has_calls([call(*c) for c in expected_calls])

def test_set_system_settings_success(system_service, mock_requests_patch, mock_requests_post):
    mock_patch_response = Mock()
    mock_patch_response.raise_for_status.return_value = None
    mock_requests_patch.return_value = mock_patch_response

    mock_post_response = Mock()
    mock_post_response.raise_for_status.return_value = None
    mock_requests_post.return_value = mock_post_response

    with patch("builtins.print") as mocked_print:
        with patch("time.sleep") as mocked_sleep:
            system_service.set_system_settings(1200, 500)
            mock_requests_patch.assert_called_once_with(
                "http://192.168.1.100/api/system",
                json={"coreVoltage": 1200, "frequency": 500},
                timeout=10
            )
            mock_requests_post.assert_called_once_with(
                "http://192.168.1.100/api/system/restart", timeout=10
            )
            mocked_sleep.assert_has_calls([call(2), call(90)])
            mocked_print.assert_has_calls([
                call(YELLOW + "Applying settings: Voltage = 1200mV, Frequency = 500MHz" + RESET),
                call(YELLOW + "Applying new settings and waiting 90s for system stabilization..." + RESET)
            ])

def test_set_system_settings_request_exception(system_service, mock_requests_patch):
    mock_requests_patch.side_effect = RequestException("Connection error")
    with patch("builtins.print") as mocked_print:
        system_service.set_system_settings(1200, 500)
        mock_requests_patch.assert_called_once_with(
            "http://192.168.1.100/api/system",
            json={"coreVoltage": 1200, "frequency": 500},
            timeout=10
        )
        mocked_print.assert_called_with(
            RED + "Error setting system settings: Connection error" + RESET
        )

def test_restart_system_success(system_service, mock_requests_post):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_requests_post.return_value = mock_response

    with patch("builtins.print") as mocked_print:
        with patch("time.sleep") as mocked_sleep:
            system_service._restart_system()
            mock_requests_post.assert_called_once_with(
                "http://192.168.1.100/api/system/restart", timeout=10
            )
            mocked_sleep.assert_called_once_with(90)
            mocked_print.assert_called_with(
                YELLOW + "Applying new settings and waiting 90s for system stabilization..." + RESET
            )

def test_restart_system_request_exception(system_service, mock_requests_post):
    mock_requests_post.side_effect = RequestException("Connection error")
    with patch("builtins.print") as mocked_print:
        system_service._restart_system()
        mock_requests_post.assert_called_once_with(
            "http://192.168.1.100/api/system/restart", timeout=10
        )
        mocked_print.assert_called_with(
            RED + "Error restarting the system: Connection error" + RESET
        )
