"""Run the RERA report API server."""

import logging

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("rera.riskmaster").setLevel(logging.INFO)
logging.getLogger("rera.report").setLevel(logging.INFO)

if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=False)
