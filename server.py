#!/usr/bin/env python3
"""
NeuroLink Wear — Health & Safety Monitoring Dashboard.

Run:
    python server.py            # http://localhost:8000
    python server.py --port 8080

The database is created and seeded with demo data automatically on first boot.
Demo logins:
    admin@neurolink.health     / admin123      (Admin)
    caregiver@neurolink.health / caregiver123  (Caregiver)
"""
import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="NeuroLink Wear dashboard server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    sys.exit(main())
