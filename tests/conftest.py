"""pytest configuration shared across the test tree."""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPTS = FIXTURES / "scripts"
IMAGES = FIXTURES / "images"
