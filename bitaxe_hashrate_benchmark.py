import signal
import sys
import traceback
from src.utils.validation import validate_parameters
from src.utils.argument_parser import parse_arguments
from src.services.benchmark_service import BenchmarkService
from src.services.system_service import SystemService
from src.services.results_service import ResultsService
from src.config.constants import (
    VOLTAGE_INCREMENT, FREQUENCY_INCREMENT, BENCHMARK_TIME,
    SAMPLE_INTERVAL, MAX_ALLOWED_VOLTAGE, MAX_ALLOWED_FREQUENCY,
    GREEN, YELLOW, RED, RESET, SYSTEM_RESET_DONE, HANDLING_INTERRUPT
)

class BitaxeBenchmark:
    def __init__(self):
        print(YELLOW + "Initializing BitaxeBenchmark..." + RESET, flush=True)
        self.args = parse_arguments()
        print(YELLOW + f"Parsed arguments: ip={self.args.bitaxe_ip}, voltage={self.args.voltage}, frequency={self.args.frequency}" + RESET, flush=True)
        self.bitaxe_ip = f"http://{self.args.bitaxe_ip}"
        self.initial_voltage = self.args.voltage
        self.initial_frequency = self.args.frequency
        self.results = []
        self.system_reset_done = SYSTEM_RESET_DONE
        self.handling_interrupt = HANDLING_INTERRUPT
        self.system_service = SystemService(self.bitaxe_ip)
        self.results_service = ResultsService(self.bitaxe_ip)

    def setup(self):
        """Initialize the benchmark process."""
        print(YELLOW + "Starting setup..." + RESET, flush=True)
        try:
            print(YELLOW + "Validating parameters..." + RESET, flush=True)
            validate_parameters(
                initial_voltage=self.initial_voltage,
                initial_frequency=self.initial_frequency,
                benchmark_time=BENCHMARK_TIME,
                sample_interval=SAMPLE_INTERVAL
            )
            print(YELLOW + "Parameters validated successfully." + RESET, flush=True)
            print(YELLOW + "Fetching default settings..." + RESET, flush=True)
            self.system_service.fetch_default_settings()
            print(YELLOW + "Registering signal handler..." + RESET, flush=True)
            signal.signal(signal.SIGINT, self._handle_sigint)
            print(YELLOW + "Setup completed." + RESET, flush=True)
        except Exception as e:
            print(RED + f"Error in setup: {e}" + RESET, flush=True)
            traceback.print_exc()
            raise

    def _handle_sigint(self, signum, frame):
        """Handle interrupt signal."""
        if self.handling_interrupt or self.system_reset_done:
            return

        self.handling_interrupt = True
        print(RED + "Benchmarking interrupted by user." + RESET, flush=True)

        try:
            if self.results:
                self._reset_to_best_setting()
                self.results_service.save_results(self.results)
                print(GREEN + "Bitaxe reset to best or default settings and results saved." + RESET, flush=True)
            else:
                print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET, flush=True)
                self.system_service.set_system_settings(
                    self.system_service.default_voltage,
                    self.system_service.default_frequency
                )
        finally:
            self.system_reset_done = True
            self.handling_interrupt = False
            sys.exit(0)

    def _reset_to_best_setting(self):
        """Reset to best or default settings."""
        print(YELLOW + "Resetting to best or default settings..." + RESET, flush=True)
        if not self.results:
            print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET, flush=True)
            self.system_service.set_system_settings(
                self.system_service.default_voltage,
                self.system_service.default_frequency
            )
        else:
            best_result = max(self.results, key=lambda x: x["averageHashRate"])
            print(GREEN + f"Applying the best settings from benchmarking:\n"
                         f"  Core Voltage: {best_result['coreVoltage']}mV\n"
                         f"  Frequency: {best_result['frequency']}MHz" + RESET, flush=True)
            self.system_service.set_system_settings(
                best_result["coreVoltage"],
                best_result["frequency"]
            )

    def run(self):
        """Run the benchmarking process."""
        print(YELLOW + "Starting benchmarking process..." + RESET, flush=True)
        try:
            self.setup()
            print(RED + "\nDISCLAIMER:" + RESET + "\nThis tool will stress test your Bitaxe. "
                  "Running hardware outside standard parameters carries risks. "
                  "Use at your own risk. Results may vary with ambient temperature.\n", flush=True)

            print(YELLOW + "Initializing BenchmarkService..." + RESET, flush=True)
            benchmark = BenchmarkService(
                self.system_service.get_system_info,
                self.system_service.small_core_count,
                self.system_service.asic_count
            )
            current_voltage = self.initial_voltage
            current_frequency = self.initial_frequency

            print(YELLOW + f"Starting benchmark loop with voltage={current_voltage}mV, frequency={current_frequency}MHz" + RESET, flush=True)
            while current_voltage <= MAX_ALLOWED_VOLTAGE and current_frequency <= MAX_ALLOWED_FREQUENCY:
                print(YELLOW + f"Setting system settings: voltage={current_voltage}mV, frequency={current_frequency}MHz" + RESET, flush=True)
                self.system_service.set_system_settings(current_voltage, current_frequency)
                print(YELLOW + "Running benchmark iteration..." + RESET, flush=True)
                result = benchmark.benchmark_iteration(current_voltage, current_frequency)

                print(YELLOW + f"Benchmark result: {result}" + RESET, flush=True)
                if all(v is not None for v in [result[0], result[1], result[2]]):
                    result_dict = {
                        "coreVoltage": current_voltage,
                        "frequency": current_frequency,
                        "averageHashRate": result[0],
                        "averageTemperature": result[1],
                        "efficiencyJTH": result[2]
                    }
                    if result[4] is not None:
                        result_dict["averageVRTemp"] = result[4]

                    self.results.append(result_dict)

                    if result[3]:  # hashrate_ok
                        if current_frequency + FREQUENCY_INCREMENT <= MAX_ALLOWED_FREQUENCY:
                            current_frequency += FREQUENCY_INCREMENT
                            print(YELLOW + f"Increasing frequency to {current_frequency}MHz" + RESET, flush=True)
                        else:
                            print(YELLOW + "Reached max frequency. Stopping." + RESET, flush=True)
                            break
                    else:
                        if current_voltage + VOLTAGE_INCREMENT <= MAX_ALLOWED_VOLTAGE:
                            current_voltage += VOLTAGE_INCREMENT
                            current_frequency -= FREQUENCY_INCREMENT
                            print(YELLOW + f"Hashrate too low. Decreasing frequency to {current_frequency}MHz "
                                  f"and increasing voltage to {current_voltage}mV" + RESET, flush=True)
                        else:
                            print(YELLOW + "Reached max voltage. Stopping." + RESET, flush=True)
                            break
                else:
                    print(GREEN + "Reached thermal or stability limits. Stopping further testing." + RESET, flush=True)
                    break

                print(YELLOW + "Saving results..." + RESET, flush=True)
                self.results_service.save_results(self.results)

        except Exception as e:
            print(RED + f"An unexpected error occurred: {e}" + RESET, flush=True)
            traceback.print_exc()
        finally:
            if not self.system_reset_done:
                print(YELLOW + "Finalizing: Resetting to best or default settings..." + RESET, flush=True)
                self._reset_to_best_setting()
                print(YELLOW + "Finalizing: Saving results..." + RESET, flush=True)
                self.results_service.save_results(self.results)
                self.system_reset_done = True
            print(YELLOW + "Finalizing: Printing results summary..." + RESET, flush=True)
            self.results_service.print_results_summary(self.results)
            print(GREEN + "Benchmarking completed." + RESET, flush=True)

if __name__ == "__main__":
    print(YELLOW + "Starting main script..." + RESET, flush=True)
    benchmark = BitaxeBenchmark()
    benchmark.run()
