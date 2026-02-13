"""Backward-compatible entry point. Delegates to backend.engine."""
import argparse
from backend.engine import cmd_start

if __name__ == "__main__":
    args = argparse.Namespace(
        redis_host=None,
        fix_config="backend/config/quickfix.cfg",
        no_market_data=False,
        verbose=False,
    )
    cmd_start(args)
