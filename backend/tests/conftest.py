# Test configuration and fixtures

import pytest
import sys
from pathlib import Path

# Add backend src to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
