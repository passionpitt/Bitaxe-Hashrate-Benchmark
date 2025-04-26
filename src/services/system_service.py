"""System Service
"""
import time
import requests
from requests.exceptions import RequestException
from src.constants import (
    MIN_ALLOWED_VOLTAGE, MIN_ALLOWED_FREQUENCY, GREEN, YELLOW, RED, RESET
)

class SystemService:
    """System service class
    """
    def __init__(self, bitaxe_ip):
        """Init
        """
        self.bitaxe_ip = bitaxe_ip
        self.default_voltage = MIN_ALLOWED_VOLTAGE
        self.default_frequency = MIN_ALLOWED_FREQUENCY
        self.small_core_count = 0
        self.asic_count = 0

    def fetch_default_settings(self):
        """Fetch default system settings from Bitaxe.
        """
        try:
            response = requests.get(f"{self.bitaxe_ip}/api/system/info", timeout=10)
            response.raise_for_status()
            system_info = response.json()

            # Ensure fallback values are always integers
            self.default_voltage = int(system_info.get("coreVoltage", MIN_ALLOWED_VOLTAGE))
            self.default_frequency = int(system_info.get("frequency", MIN_ALLOWED_FREQUENCY))
            self.small_core_count = int(system_info.get("smallCoreCount", 0) or 0)
            self.asic_count = int(system_info.get("asicCount", 0) or 0)

            # Check if values are valid before multiplication
            total_cores = self.small_core_count * self.asic_count if self.small_core_count is not None and self.asic_count is not None else 0
            print(GREEN + f"Current settings determined:\n"
                         f"  Core Voltage: {self.default_voltage}mV\n"
                         f"  Frequency: {self.default_frequency}MHz\n"
                         f"  ASIC Configuration: {total_cores} total cores" + RESET)
        except RequestException as e:
            print(RED + f"Error fetching default system settings: {e}. Using fallback defaults." + RESET)
            # Explicitly set fallback values in case of failure
            self.default_voltage = MIN_ALLOWED_VOLTAGE
            self.default_frequency = MIN_ALLOWED_FREQUENCY
            self.small_core_count = 0
            self.asic_count = 0
        except ValueError as e:
            print(RED + f"Invalid data in system settings: {e}. Using fallback defaults." + RESET)
            self.default_voltage = MIN_ALLOWED_VOLTAGE
            self.default_frequency = MIN_ALLOWED_FREQUENCY
            self.small_core_count = 0
            self.asic_count = 0

    def get_system_info(self):
        """Fetch system information with retries.
        """
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.get(f"{self.bitaxe_ip}/api/system/info", timeout=10)
                response.raise_for_status()
                return response.json()
            except RequestException as e:
                print(YELLOW + f"Error fetching system info (attempt {attempt + 1}/{retries}): {e}" + RESET)
                time.sleep(5)
        return None

    def set_system_settings(self, core_voltage, frequency):
        """Apply system settings
        """
        settings = {"coreVoltage": core_voltage, "frequency": frequency}
        try:
            response = requests.patch(f"{self.bitaxe_ip}/api/system", json=settings, timeout=10)
            response.raise_for_status()
            print(YELLOW + f"Applying settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz" + RESET)
            time.sleep(2)
            self._restart_system()
        except RequestException as e:
            print(RED + f"Error setting system settings: {e}" + RESET)

    def _restart_system(self):
        """Restart the system
        """
        try:
            response = requests.post(f"{self.bitaxe_ip}/api/system/restart", timeout=10)
            response.raise_for_status()
            print(YELLOW + "Applying new settings and waiting 90s for system stabilization..." + RESET)
            time.sleep(90)
        except RequestException as e:
            print(RED + f"Error restarting the system: {e}" + RESET)
