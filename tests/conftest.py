"""pytest configuration shared across the test tree."""
import pytest
from pathlib import Path
from PIL import Image

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPTS = FIXTURES / "scripts"
IMAGES = FIXTURES / "images"


@pytest.fixture(scope="session", autouse=True)
def _generate_reference_images():
    """Create reference PNG fixtures for diff_frames tests."""
    IMAGES.mkdir(parents=True, exist_ok=True)

    a = IMAGES / "reference_a.png"
    b = IMAGES / "reference_b.png"
    c = IMAGES / "reference_c_16x16.png"

    if not a.exists():
        Image.new("RGB", (32, 32), (255, 0, 0)).save(a)

    if not b.exists():
        img_b = Image.new("RGB", (32, 32), (255, 0, 0))
        pixels = img_b.load()
        pixels[10, 10] = (0, 255, 0)
        img_b.save(b)

    if not c.exists():
        Image.new("RGB", (16, 16), (255, 0, 0)).save(c)

    yield
