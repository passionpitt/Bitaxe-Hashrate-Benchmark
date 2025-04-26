"""Results service
"""
import json
from src.constants import GREEN, RED, RESET

class ResultsService:
    """Results service class
    """
    def __init__(self, bitaxe_ip):
        """init
        """
        self.bitaxe_ip = bitaxe_ip

    def save_results(self, results):
        """Save benchmarking results to file
        """
        try:
            ip_address = self.bitaxe_ip.replace('http://', '')
            filename = f"bitaxe_benchmark_results_{ip_address}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self._format_results(results), f, indent=4)
            print(GREEN + f"Results saved to {filename}" + RESET)
        except IOError as e:
            print(RED + f"Error saving results to file: {e}" + RESET)

    def _format_results(self, results):
        """Format results for saving
        """
        top_5_results = sorted(results, key=lambda x: x["averageHashRate"], reverse=True)[:5]
        top_5_efficient = sorted(results, key=lambda x: x["efficiencyJTH"])[:5]

        return {
            "all_results": results,
            "top_performers": [
                {
                    "rank": i,
                    **dict(result.items())
                } for i, result in enumerate(top_5_results, 1)
            ],
            "most_efficient": [
                {
                    "rank": i,
                    **dict(result.items())
                } for i, result in enumerate(top_5_efficient, 1)
            ]
        }

    def print_results_summary(self, results):
        """Print summary of top results
        """
        if not results:
            print(RED + "No valid results were found during benchmarking." + RESET)
            return

        top_5_results = sorted(results, key=lambda x: x["averageHashRate"], reverse=True)[:5]
        top_5_efficient = sorted(results, key=lambda x: x["efficiencyJTH"])[:5]

        print(GREEN + "\nTop 5 Highest Hashrate Settings:" + RESET)
        for i, result in enumerate(top_5_results, 1):
            print(GREEN + f"\nRank {i}:\n"
                         f"  Core Voltage: {result['coreVoltage']}mV\n"
                         f"  Frequency: {result['frequency']}MHz\n"
                         f"  Average Hashrate: {result['averageHashRate']:.2f} GH/s\n"
                         f"  Average Temperature: {result['averageTemperature']:.2f}°C\n"
                         f"  Efficiency: {result['efficiencyJTH']:.2f} J/TH" +
                         (f"\n  Average VR Temperature: {result['averageVRTemp']:.2f}°C" if "averageVRTemp" in result else "") + RESET)

        print(GREEN + "\nTop 5 Most Efficient Settings:" + RESET)
        for i, result in enumerate(top_5_efficient, 1):
            print(GREEN + f"\nRank {i}:\n"
                         f"  Core Voltage: {result['coreVoltage']}mV\n"
                         f"  Frequency: {result['frequency']}MHz\n"
                         f"  Average Hashrate: {result['averageHashRate']:.2f} GH/s\n"
                         f"  Average Temperature: {result['averageTemperature']:.2f}°C\n"
                         f"  Efficiency: {result['efficiencyJTH']:.2f} J/TH" +
                         (f"\n  Average VR Temperature: {result['averageVRTemp']:.2f}°C" if "averageVRTemp" in result else "") + RESET)
