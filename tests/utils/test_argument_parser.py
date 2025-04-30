import pytest
import sys
from unittest.mock import patch
from src.utils.argument_parser import ArgumentParserWithHelpOnNoArgs, parse_arguments

def test_parser_help_on_no_args(capsys):
    parser = ArgumentParserWithHelpOnNoArgs(description="Test parser")
    with patch.object(sys, 'argv', ['bitaxe_hashrate_benchmark.py']):
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Test parser" in captured.out

def test_parse_arguments_defaults():
    with patch.object(sys, 'argv', ['bitaxe_hashrate_benchmark.py']):
        with pytest.raises(SystemExit):
            parse_arguments()

def test_parse_arguments_with_ip():
    with patch.object(sys, 'argv', ['bitaxe_hashrate_benchmark.py', '192.168.2.26']):
        args = parse_arguments()
        assert args.bitaxe_ip == '192.168.2.26'
        assert args.voltage == 1150
        assert args.frequency == 525

def test_parse_arguments_with_all_args():
    with patch.object(sys, 'argv', ['bitaxe_hashrate_benchmark.py', '192.168.2.26', '-v', '1200', '-f', '600']):
        args = parse_arguments()
        assert args.bitaxe_ip == '192.168.2.26'
        assert args.voltage == 1200
        assert args.frequency == 600

def test_parse_arguments_invalid_voltage():
    with patch.object(sys, 'argv', ['bitaxe_hashrate_benchmark.py', '192.168.2.26', '-v', 'invalid']):
        with pytest.raises(SystemExit):
            parse_arguments()
