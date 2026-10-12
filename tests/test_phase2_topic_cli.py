from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

def test_producer_cli_has_topic_option():
    p = subprocess.run([PYTHON, str(ROOT / "scripts/kafka/cmapss_producer.py"), "--help"], capture_output=True, text=True)
    assert p.returncode == 0
    assert "--topic" in p.stdout

def test_consumer_cli_has_topic_option():
    p = subprocess.run([PYTHON, str(ROOT / "scripts/kafka/cmapss_consumer.py"), "--help"], capture_output=True, text=True)
    assert p.returncode == 0
    assert "--topic" in p.stdout
