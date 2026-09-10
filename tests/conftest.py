import os
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))
os.environ.setdefault("ELAN_HOME", str(WORKSPACE / ".tools" / "elan"))

from mathesis.config import load_config  # noqa: E402
from mathesis.lean_env import fingerprint_environment  # noqa: E402


@pytest.fixture(scope="session")
def config():
    return load_config(WORKSPACE / "configs" / "default.yaml")


@pytest.fixture(scope="session")
def environment(config):
    return fingerprint_environment(
        package_dir=WORKSPACE / config.lean.package_dir,
        elan_home=WORKSPACE / config.lean.elan_home,
        toolchain=config.lean.toolchain,
    )


@pytest.fixture(scope="session")
def validator(config, environment, tmp_path_factory):
    from mathesis.validation import ProofValidator

    scratch = tmp_path_factory.mktemp("scratch")
    return ProofValidator(config, environment, scratch_dir=scratch)
