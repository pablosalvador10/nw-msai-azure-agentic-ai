"""Which checks run in which week."""

from harness.checks import week05, week06, week07, week08, week10
from harness.checks.core import CORE

WEEKS = {
    5: week05.CHECKS,
    6: week06.CHECKS,
    7: week07.CHECKS,
    8: week08.CHECKS,
    10: week10.CHECKS,
}

__all__ = ["CORE", "WEEKS"]
