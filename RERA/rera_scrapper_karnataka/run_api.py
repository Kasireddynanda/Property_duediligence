"""API Server runner for Karnataka RERA."""

from __future__ import annotations

import argparse
import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Karnataka RERA API server.")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host interface to bind to. Default: 0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port to bind to. Default: 8002",
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
