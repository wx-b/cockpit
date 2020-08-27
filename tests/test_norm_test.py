"""Execute debugging script for norm test.

Note: Changing the path of this file can lead to its failure.
"""

import os

from tests.utils import REPO_ROOT_DIR, run_command


def test_norm_test_math_rearrangements():
    """Run tracking of norm test and perform sanity checks during computation.

    Note: Running directly with ``pytest`` messes up ``argparse`` from DeepOBS.
    """
    target = os.path.join(REPO_ROOT_DIR, "exp/debug/track_norm_test.py")
    run_command(["python", target])
