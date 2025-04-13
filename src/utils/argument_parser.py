"""Argument Parser
"""
import argparse
import sys
from typing import Any

class ArgumentParserWithHelpOnNoArgs(argparse.ArgumentParser):
    """Custom ArgumentParser that shows help when no args are passed"""
    def parse_args(self, args=None, namespace=None) -> Any:
        if args is None and len(sys.argv) == 1:
            self.print_help()
            sys.exit(1)
        return super().parse_args(args, namespace)

def parse_arguments() -> argparse.Namespace:
    """Parse arguments"""
    parser = ArgumentParserWithHelpOnNoArgs(
        description='Bitaxe Hashrate Benchmark Tool'
    )

    parser.add_argument(
        'bitaxe_ip',
        nargs='?',
        help='IP address of the Bitaxe (e.g., 192.168.2.26)'
    )
    parser.add_argument(
        '-v', '--voltage',
        type=int,
        default=1150,
        help='Initial voltage in mV (default: 1150)'
    )
    parser.add_argument(
        '-f', '--frequency',
        type=int,
        default=525,
        help='Initial frequency in MHz (default: 525)'
    )

    return parser.parse_args()
