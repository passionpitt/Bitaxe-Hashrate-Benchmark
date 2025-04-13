"""Constants
"""
# CONFIGURATIONS
VOLTAGE_INCREMENT: int = 20
FREQUENCY_INCREMENT: int = 25
BENCHMARK_TIME: int = 150          # 2.5 minutes benchmark time
SAMPLE_INTERVAL: int = 15          # 15 seconds sample interval
MAX_TEMP: int = 65                 # Will stop if temperature reaches or exceeds this value
MAX_ALLOWED_VOLTAGE: int = 1400    # Maximum allowed core voltage
MAX_ALLOWED_FREQUENCY: int = 1250  # Maximum allowed core frequency
MAX_VR_TEMP: int = 75              # Maximum allowed voltage regulator temperature
MIN_INPUT_VOLTAGE: int = 4800      # Minimum allowed input voltage
MAX_INPUT_VOLTAGE: int = 5500      # Maximum allowed input voltage
MAX_POWER: int = 45                # Max of 45W because of DC plug
MIN_ALLOWED_VOLTAGE: int = 1150    # Minimum allowed core voltage
MIN_ALLOWED_FREQUENCY: int = 525   # Minimum allowed frequency

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

SMALL_CORE_COUNT = None
ASIC_COUNT = None
DEFAULT_VOLTAGE = None
DEFAULT_FREQUENCY = None

# Add a global flag to track whether the system has already been reset
SYSTEM_RESET_DONE: bool = False
# Check if we're handling an interrupt (Ctrl+C)
HANDLING_INTERRUPT: bool = False
