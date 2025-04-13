import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import time
import json
import signal
import sys
from src.utils.validation import validate_parameters
from src.utils.argument_parser import parse_arguments
from src.services.benchmark_service import BenchmarkService
from src.constants import (VOLTAGE_INCREMENT, FREQUENCY_INCREMENT, BENCHMARK_TIME,
    SAMPLE_INTERVAL, MAX_ALLOWED_VOLTAGE, MAX_ALLOWED_FREQUENCY, MIN_ALLOWED_VOLTAGE,
    MIN_ALLOWED_FREQUENCY, GREEN, YELLOW, RED, RESET, SMALL_CORE_COUNT, ASIC_COUNT,
    DEFAULT_VOLTAGE, DEFAULT_FREQUENCY, SYSTEM_RESET_DONE, HANDLING_INTERRUPT)

if __name__ == "__main__":
    # Replace the configuration section
    args = parse_arguments()
    bitaxe_ip = f"http://{args.bitaxe_ip}"
    initial_voltage = args.voltage
    initial_frequency = args.frequency

    # Validate core voltages
    validate_parameters(
        initial_voltage=initial_voltage,
        initial_frequency=initial_frequency,
        benchmark_time=BENCHMARK_TIME,
        sample_interval=SAMPLE_INTERVAL
    )

    # Results storage
    results = []

    def fetch_default_settings():
        global DEFAULT_VOLTAGE, DEFAULT_FREQUENCY, SMALL_CORE_COUNT, ASIC_COUNT
        try:
            response = requests.get(f"{bitaxe_ip}/api/system/info", timeout=10)
            response.raise_for_status()
            system_info = response.json()
            DEFAULT_VOLTAGE = system_info.get("coreVoltage", MIN_ALLOWED_VOLTAGE)  # Fallback to 1150 if not found
            DEFAULT_FREQUENCY = system_info.get("frequency", MIN_ALLOWED_FREQUENCY)  # Fallback to 525 if not found
            SMALL_CORE_COUNT = system_info.get("smallCoreCount", 0)
            ASIC_COUNT = system_info.get("asicCount", 0)
            print(GREEN + f"Current settings determined:\n"
                        f"  Core Voltage: {DEFAULT_VOLTAGE}mV\n"
                        f"  Frequency: {DEFAULT_FREQUENCY}MHz\n"
                        f"  ASIC Configuration: {SMALL_CORE_COUNT * ASIC_COUNT} total cores" + RESET)
        except RequestException as e:
            print(RED + f"Error fetching default system settings: {e}. Using fallback defaults." + RESET)
            DEFAULT_VOLTAGE = MIN_ALLOWED_VOLTAGE
            DEFAULT_FREQUENCY = MIN_ALLOWED_FREQUENCY
            SMALL_CORE_COUNT = 0
            ASIC_COUNT = 0

    def handle_sigint(signum, frame):
        global SYSTEM_RESET_DONE, HANDLING_INTERRUPT

        # If we're already handling an interrupt or have completed reset, ignore this signal
        if HANDLING_INTERRUPT or SYSTEM_RESET_DONE:
            return

        HANDLING_INTERRUPT = True
        print(RED + "Benchmarking interrupted by user." + RESET)

        try:
            if results:
                reset_to_best_setting()
                save_results()
                print(GREEN + "Bitaxe reset to best or default settings and results saved." + RESET)
            else:
                print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
                set_system_settings(DEFAULT_VOLTAGE, DEFAULT_FREQUENCY)
        finally:
            SYSTEM_RESET_DONE = True
            HANDLING_INTERRUPT = False
            sys.exit(0)

    # Register the signal handler
    signal.signal(signal.SIGINT, handle_sigint)

    def get_system_info():
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.get(f"{bitaxe_ip}/api/system/info", timeout=10)
                response.raise_for_status()  # Raise an exception for HTTP errors
                return response.json()
            except Timeout:
                print(YELLOW + f"Timeout while fetching system info. Attempt {attempt + 1} of {retries}." + RESET)
            except ConnectionError:
                print(RED + f"Connection error while fetching system info. Attempt {attempt + 1} of {retries}." + RESET)
            except RequestException as e:
                print(RED + f"Error fetching system info: {e}" + RESET)
                break
            time.sleep(5)  # Wait before retrying
        return None

    def set_system_settings(core_voltage, frequency):
        settings = {
            "coreVoltage": core_voltage,
            "frequency": frequency
        }
        try:
            response = requests.patch(f"{bitaxe_ip}/api/system", json=settings, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors
            print(YELLOW + f"Applying settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz" + RESET)
            time.sleep(2)
            restart_system()
        except RequestException as e:
            print(RED + f"Error setting system settings: {e}" + RESET)

    def restart_system():
        try:
            # Check if we're being called from handle_sigint
            is_interrupt = HANDLING_INTERRUPT

            # Restart here as some bitaxes get unstable with bad settings
            # If not an interrupt, wait 90s for system stabilization as some bitaxes are slow to ramp up
            if not is_interrupt:
                print(YELLOW + "Applying new settings and waiting 90s for system stabilization..." + RESET)
                response = requests.post(f"{bitaxe_ip}/api/system/restart", timeout=10)
                response.raise_for_status()  # Raise an exception for HTTP errors
                time.sleep(90)  # Allow 90s time for the system to restart and start hashing
            else:
                print(YELLOW + "Applying final settings..." + RESET)
                response = requests.post(f"{bitaxe_ip}/api/system/restart", timeout=10)
                response.raise_for_status()  # Raise an exception for HTTP errors
        except RequestException as e:
            print(RED + f"Error restarting the system: {e}" + RESET)


    def save_results():
        try:
            # Extract IP from bitaxe_ip global variable and remove 'http://'
            ip_address = bitaxe_ip.replace('http://', '')
            filename = f"bitaxe_benchmark_results_{ip_address}.json"
            with open(filename, "w") as f:
                json.dump(results, f, indent=4)
            print(GREEN + f"Results saved to {filename}" + RESET)
            print()  # Add empty line

        except IOError as e:
            print(RED + f"Error saving results to file: {e}" + RESET)

    def reset_to_best_setting():
        if not results:
            print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
            set_system_settings(DEFAULT_VOLTAGE, DEFAULT_FREQUENCY)
        else:
            best_result = sorted(results, key=lambda x: x["averageHashRate"], reverse=True)[0]
            best_voltage = best_result["coreVoltage"]
            best_frequency = best_result["frequency"]

            print(GREEN + f"Applying the best settings from benchmarking:\n"
                        f"  Core Voltage: {best_voltage}mV\n"
                        f"  Frequency: {best_frequency}MHz" + RESET)
            set_system_settings(best_voltage, best_frequency)

        restart_system()

    # Add this new function to handle cleanup
    def cleanup_and_exit(reason=None):
        global SYSTEM_RESET_DONE
        if SYSTEM_RESET_DONE:
            return

        try:
            if results:
                reset_to_best_setting()
                save_results()
                print(GREEN + "Bitaxe reset to best settings and results saved." + RESET)
            else:
                print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
                set_system_settings(DEFAULT_VOLTAGE, DEFAULT_FREQUENCY)
        finally:
            SYSTEM_RESET_DONE = True
            if reason:
                print(RED + f"Benchmarking stopped: {reason}" + RESET)
            print(GREEN + "Benchmarking completed." + RESET)
            sys.exit(0)

    # Main benchmarking process
    try:
        fetch_default_settings()

        # Add disclaimer
        print(RED + "\nDISCLAIMER:" + RESET)
        print("This tool will stress test your Bitaxe by running it at various voltages and frequencies.")
        print("While safeguards are in place, running hardware outside of standard parameters carries inherent risks.")
        print("Use this tool at your own risk. The author(s) are not responsible for any damage to your hardware.")
        print("\nNOTE: Ambient temperature significantly affects these results. The optimal settings found may not")
        print("work well if room temperature changes substantially. Re-run the benchmark if conditions change.\n")

        benchmark = BenchmarkService(get_system_info)
        current_voltage = initial_voltage
        current_frequency = initial_frequency

        while current_voltage <= MAX_ALLOWED_VOLTAGE and current_frequency <= MAX_ALLOWED_FREQUENCY:
            set_system_settings(current_voltage, current_frequency)
            avg_hashrate, avg_temp, efficiency_jth, hashrate_ok, avg_vr_temp, error_reason = benchmark.benchmark_iteration(core_voltage=current_voltage, frequency=current_frequency)

            if avg_hashrate is not None and avg_temp is not None and efficiency_jth is not None:
                result = {
                    "coreVoltage": current_voltage,
                    "frequency": current_frequency,
                    "averageHashRate": avg_hashrate,
                    "averageTemperature": avg_temp,
                    "efficiencyJTH": efficiency_jth
                }

                # Only add VR temp if it exists
                if avg_vr_temp is not None:
                    result["averageVRTemp"] = avg_vr_temp

                results.append(result)

                if hashrate_ok:
                    # If hashrate is good, try increasing frequency
                    if current_frequency + FREQUENCY_INCREMENT <= MAX_ALLOWED_FREQUENCY:
                        current_frequency += FREQUENCY_INCREMENT
                    else:
                        break  # We've reached max frequency with good results
                else:
                    # If hashrate is not good, go back one frequency step and increase voltage
                    if current_voltage + VOLTAGE_INCREMENT <= MAX_ALLOWED_VOLTAGE:
                        current_voltage += VOLTAGE_INCREMENT
                        current_frequency -= FREQUENCY_INCREMENT  # Go back to one frequency step and retry
                        print(YELLOW + f"Hashrate too low compared to expected. Decreasing frequency to {current_frequency}MHz and increasing voltage to {current_voltage}mV" + RESET)
                    else:
                        break  # We've reached max voltage without good results
            else:
                # If we hit thermal limits or other issues, we've found the highest safe settings
                print(GREEN + "Reached thermal or stability limits. Stopping further testing." + RESET)
                break  # Stop testing higher values

            save_results()

    except Exception as e:
        print(RED + f"An unexpected error occurred: {e}" + RESET)
        if results:
            reset_to_best_setting()
            save_results()
        else:
            print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
            set_system_settings(DEFAULT_VOLTAGE, DEFAULT_FREQUENCY)
            restart_system()
    finally:
        if not SYSTEM_RESET_DONE:
            if results:
                reset_to_best_setting()
                save_results()
                print(GREEN + "Bitaxe reset to best or default settings and results saved." + RESET)
            else:
                print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
                set_system_settings(DEFAULT_VOLTAGE, DEFAULT_FREQUENCY)
                restart_system()
            SYSTEM_RESET_DONE = True

        # Print results summary only if we have results
        if results:
            # Sort results by averageHashRate in descending order and get the top 5
            top_5_results = sorted(results, key=lambda x: x["averageHashRate"], reverse=True)[:5]
            top_5_efficient_results = sorted(results, key=lambda x: x["efficiencyJTH"], reverse=False)[:5]

            # Create a dictionary containing all results and top performers
            final_data = {
                "all_results": results,
                "top_performers": [
                    {
                        "rank": i,
                        "coreVoltage": result["coreVoltage"],
                        "frequency": result["frequency"],
                        "averageHashRate": result["averageHashRate"],
                        "averageTemperature": result["averageTemperature"],
                        "efficiencyJTH": result["efficiencyJTH"],
                        **({"averageVRTemp": result["averageVRTemp"]} if "averageVRTemp" in result else {})
                    }
                    for i, result in enumerate(top_5_results, 1)
                ],
                "most_efficient": [
                    {
                        "rank": i,
                        "coreVoltage": result["coreVoltage"],
                        "frequency": result["frequency"],
                        "averageHashRate": result["averageHashRate"],
                        "averageTemperature": result["averageTemperature"],
                        "efficiencyJTH": result["efficiencyJTH"],
                        **({"averageVRTemp": result["averageVRTemp"]} if "averageVRTemp" in result else {})
                    }
                    for i, result in enumerate(top_5_efficient_results, 1)
                ]
            }

            # Save the final data to JSON
            ip_address = bitaxe_ip.replace('http://', '')
            filename = f"bitaxe_benchmark_results_{ip_address}.json"
            with open(filename, "w") as f:
                json.dump(final_data, f, indent=4)

            print(GREEN + "Benchmarking completed." + RESET)
            if top_5_results:
                print(GREEN + "\nTop 5 Highest Hashrate Settings:" + RESET)
                for i, result in enumerate(top_5_results, 1):
                    print(GREEN + f"\nRank {i}:" + RESET)
                    print(GREEN + f"  Core Voltage: {result['coreVoltage']}mV" + RESET)
                    print(GREEN + f"  Frequency: {result['frequency']}MHz" + RESET)
                    print(GREEN + f"  Average Hashrate: {result['averageHashRate']:.2f} GH/s" + RESET)
                    print(GREEN + f"  Average Temperature: {result['averageTemperature']:.2f}°C" + RESET)
                    print(GREEN + f"  Efficiency: {result['efficiencyJTH']:.2f} J/TH" + RESET)
                    if "averageVRTemp" in result:
                        print(GREEN + f"  Average VR Temperature: {result['averageVRTemp']:.2f}°C" + RESET)

                print(GREEN + "\nTop 5 Most Efficient Settings:" + RESET)
                for i, result in enumerate(top_5_efficient_results, 1):
                    print(GREEN + f"\nRank {i}:" + RESET)
                    print(GREEN + f"  Core Voltage: {result['coreVoltage']}mV" + RESET)
                    print(GREEN + f"  Frequency: {result['frequency']}MHz" + RESET)
                    print(GREEN + f"  Average Hashrate: {result['averageHashRate']:.2f} GH/s" + RESET)
                    print(GREEN + f"  Average Temperature: {result['averageTemperature']:.2f}°C" + RESET)
                    print(GREEN + f"  Efficiency: {result['efficiencyJTH']:.2f} J/TH" + RESET)
                    if "averageVRTemp" in result:
                        print(GREEN + f"  Average VR Temperature: {result['averageVRTemp']:.2f}°C" + RESET)
            else:
                print(RED + "No valid results were found during benchmarking." + RESET)
