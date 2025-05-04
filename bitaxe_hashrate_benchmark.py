from src.services.bitaxe_benchmark_service import BitaxeBenchmark
from src.config.constants import (YELLOW, RESET)

if __name__ == "__main__":
    print(YELLOW + "Starting main script..." + RESET, flush=True)
    benchmark = BitaxeBenchmark()
    benchmark.run()
