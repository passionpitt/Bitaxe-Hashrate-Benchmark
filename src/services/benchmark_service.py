"""
BenchmarkService: Handles benchmarking of Bitaxe mining devices based on system stats.
"""

import time
from src.constants import (
    GREEN, RED, RESET,
    MAX_TEMP, MAX_VR_TEMP,
    MIN_INPUT_VOLTAGE, MAX_INPUT_VOLTAGE,
    MAX_POWER, BENCHMARK_TIME, SAMPLE_INTERVAL,
    SMALL_CORE_COUNT, ASIC_COUNT
)

class BenchmarkService:
    """
    Provides methods to run performance benchmarks on Bitaxe devices.
    """
    def __init__(self, get_system_info):
        """
        Initialize with system info callable.

        :param get_system_info: Callable that returns system info from the Bitaxe device.
        """
        self.get_system_info = get_system_info
        self.total_samples = BENCHMARK_TIME // SAMPLE_INTERVAL
        self.expected_hashrate = lambda freq: freq * (
            (SMALL_CORE_COUNT * ASIC_COUNT) / 1000
        )

    def run_benchmark(self, core_voltage, frequency):
        """
        Public method to run a benchmark iteration.

        :param core_voltage: Core voltage in mV.
        :param frequency: Frequency in MHz.
        """
        return self.benchmark_iteration(core_voltage, frequency)

    def benchmark_iteration(self, core_voltage, frequency):
        """
        Runs a full benchmark iteration for the given voltage and frequency.

        :param core_voltage: Core voltage in mV.
        :param frequency: Frequency in MHz.
        :return: Tuple of benchmark results or exit values on failure.
        """
        self._log_start(core_voltage, frequency)
        samples = self._collect_samples(core_voltage, frequency)

        if samples is None:
            return self._exit("NO_DATA", "Benchmark data collection failed.")

        expected = self.expected_hashrate(frequency)
        return self._calculate_results(samples, expected)

    def _log_start(self, core_voltage, frequency):
        """
        Logs the start of the benchmark.

        :param core_voltage: Core voltage in mV.
        :param frequency: Frequency in MHz.
        """
        current_time = time.strftime("%H:%M:%S")
        print(
            f"{GREEN}[{current_time}] Starting benchmark for Core Voltage: "
            f"{core_voltage}mV, Frequency: {frequency}MHz{RESET}"
        )

    def _collect_samples(self, core_voltage, frequency):
        """
        Collects data samples over time.

        :param core_voltage: Core voltage in mV.
        :param frequency: Frequency in MHz.
        :return: Dictionary of samples or None if collection fails.
        """
        samples = {'hash_rates': [], 'temps': [], 'powers': [], 'vr_temps': []}

        for sample in range(self.total_samples):
            info = self.get_system_info()
            if info is None:
                self._exit("SYSTEM_INFO_FAILURE", "System info unavailable.")
                return None

            valid, _ = self._validate(info)
            if not valid:
                return None

            if not self._process(info, samples):
                return None

            self._log_sample_progress(sample, core_voltage, frequency, info)

            if sample < self.total_samples - 1:
                time.sleep(SAMPLE_INTERVAL)

        return samples

    def _validate(self, info):
        """
        Validates the system info.

        :param info: Dictionary containing system information.
        :return: Tuple (valid: bool, result: tuple or None).
        """
        temp = info.get("temp")
        if temp is None:
            reason = "TEMP_MISSING"
            message = "Temperature not available."
        elif temp < 5:
            reason = "TEMP_TOO_LOW"
            message = "Temperature below 5°C."
        elif temp >= MAX_TEMP:
            reason = "TEMP_HIGH"
            message = f"Chip temperature ≥ {MAX_TEMP}°C!"
        else:
            vr_temp = info.get("vrTemp")
            if vr_temp is not None and vr_temp >= MAX_VR_TEMP:
                reason = "VR_TEMP_HIGH"
                message = f"VR temperature ≥ {MAX_VR_TEMP}°C!"
            else:
                voltage = info.get("voltage")
                if voltage < MIN_INPUT_VOLTAGE:
                    reason = "VOLTAGE_LOW"
                    message = f"Voltage < {MIN_INPUT_VOLTAGE}mV."
                elif voltage > MAX_INPUT_VOLTAGE:
                    reason = "VOLTAGE_HIGH"
                    message = f"Voltage > {MAX_INPUT_VOLTAGE}mV."
                else:
                    return True, (temp, vr_temp, voltage)
        self._exit(reason, message)
        return False, None

    def _process(self, info, samples):
        """
        Processes system info and appends to samples.

        :param info: Dictionary containing system information.
        :param samples: Dictionary to store sample data.
        :return: Boolean indicating success.
        """
        hash_rate = info.get("hashRate")
        power = info.get("power")
        if hash_rate is None or power is None or power > MAX_POWER:
            return False

        samples['hash_rates'].append(hash_rate)
        samples['temps'].append(info["temp"])
        samples['powers'].append(power)
        vr = info.get("vrTemp")
        if vr is not None:
            samples['vr_temps'].append(vr)
        return True

    def _log_sample_progress(self, sample, core_voltage, frequency, info):
        """
        Logs the progress of each sample.

        :param sample: Current sample number.
        :param core_voltage: Core voltage in mV.
        :param frequency: Frequency in MHz.
        :param info: Dictionary containing system information.
        """
        percent = ((sample + 1) / self.total_samples) * 100
        parts = [
            f"[{sample + 1:2d}/{self.total_samples:2d}] {percent:5.1f}%",
            f"CV: {core_voltage}mV", f"F: {frequency}MHz",
            f"H: {int(info['hashRate'])} GH/s", f"IV: {int(info['voltage'])}mV",
            f"T: {int(info['temp'])}°C"
        ]
        if 'vrTemp' in info:
            parts.append(f"VR: {int(info['vrTemp'])}°C")
        print(" | ".join(parts) + RESET)

    def _calculate_results(self, samples, expected):
        """
        Calculates the final results from collected samples.

        :param samples: Dictionary containing lists of sample data.
        :param expected: Expected hashrate in GH/s.
        :return: Tuple of calculated results or exit values on failure.
        """
        hash_rates = samples['hash_rates']
        temps = samples['temps']
        powers = samples['powers']
        vr_temps = samples['vr_temps']

        if not (hash_rates and temps and powers):
            return self._exit("NO_DATA_COLLECTED", "No valid benchmark data.")

        avg_hash = sum(sorted(hash_rates)[3:-3]) / max(1, len(hash_rates) - 6)
        avg_temp = sum(sorted(temps)[6:]) / max(1, len(temps) - 6)
        avg_power = sum(powers) / len(powers)

        avg_vr = None
        if vr_temps:
            trimmed = sorted(vr_temps)[6:]
            avg_vr = sum(trimmed) / len(trimmed) if trimmed else None

        if avg_hash <= 0:
            return self._exit("ZERO_HASH", "Zero hashrate detected.")

        efficiency = avg_power / (avg_hash / 1000)
        within_tolerance = avg_hash >= expected * 0.94

        print(f"{GREEN}Average Hashrate: {avg_hash:.2f} GH/s "
              f"(Expected: {expected:.2f}){RESET}")
        print(f"{GREEN}Average Temp: {avg_temp:.2f}°C{RESET}")
        if avg_vr is not None:
            print(f"{GREEN}Average VR Temp: {avg_vr:.2f}°C{RESET}")
        print(f"{GREEN}Efficiency: {efficiency:.2f} J/TH{RESET}")

        return avg_hash, avg_temp, efficiency, within_tolerance, avg_vr, None

    def _exit(self, reason, message, color=RED):
        """
        Handles exit conditions with a reason and message.

        :param reason: String identifier for the exit condition.
        :param message: Message to display.
        :param color: Color code for the output (default RED).
        :return: Tuple indicating failure.
        """
        print(color + message + RESET)
        return None, None, None, False, None, reason
