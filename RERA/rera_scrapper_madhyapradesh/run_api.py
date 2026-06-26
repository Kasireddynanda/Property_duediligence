"""API Server runner for Madhya Pradesh RERA."""

from __future__ import annotations

import argparse
import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Madhya Pradesh RERA API server.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host interface to bind to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8003,
        help="Port to bind to.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code change.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    uvicorn.run("api.server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
