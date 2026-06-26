"""Run the Tamil Nadu RERA report API server."""

import argparse
import logging
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start TN RERA Search API Server")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the API server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the API server on")
    args = parser.parse_args()

    uvicorn.run("api.server:app", host=args.host, port=args.port, reload=False)
