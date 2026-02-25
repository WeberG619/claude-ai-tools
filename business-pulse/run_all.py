#!/usr/bin/env python3
"""
Run all business pulse checks at once.
Called by heartbeat.py or manually.
Generates: pulse.json, patterns.json, anticipations.json
"""

from heartbeat import generate_pulse
from patterns import generate_patterns
from anticipate import generate_anticipations
from datetime import datetime
import json


def run_all():
    print(f"Business Pulse — Full Run — {datetime.now():%Y-%m-%d %H:%M}")
    print("=" * 50)

    print("\n[1/3] Heartbeat checks...")
    pulse = generate_pulse()
    print(f"  → {pulse.get('summary', {}).get('total_alerts', 0)} alerts")

    print("\n[2/3] Pattern analysis...")
    patterns = generate_patterns()
    print(f"  → Revenue trend: {patterns.get('revenue_trend', {}).get('trend', 'unknown')}")
    print(f"  → Client risk: {patterns.get('client_concentration', {}).get('risk', 'unknown')}")

    print("\n[3/3] Anticipation engine...")
    anticipations = generate_anticipations()
    print(f"  → {anticipations.get('total_predictions', 0)} predictions")
    cf = anticipations.get("cash_flow", {})
    if cf.get("message"):
        print(f"  → {cf['message']}")

    print("\n" + "=" * 50)
    print("All pulse files updated.")
    print(f"  pulse.json         — {pulse.get('summary', {}).get('total_alerts', 0)} alerts")
    print(f"  patterns.json      — historical analysis")
    print(f"  anticipations.json — {anticipations.get('total_predictions', 0)} predictions")


if __name__ == "__main__":
    run_all()
