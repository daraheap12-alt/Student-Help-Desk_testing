from __future__ import annotations

import math
from typing import Any


def summarize_latency(latency_values: list[float]) -> dict[str, Any]:
    if not latency_values:
        return {
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "total_requests": 0,
        }

    ordered = sorted(latency_values)
    avg_latency_ms = sum(ordered) / len(ordered)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    p95_latency_ms = ordered[p95_index]

    return {
        "avg_latency_ms": round(avg_latency_ms, 2),
        "p95_latency_ms": round(p95_latency_ms, 2),
        "total_requests": len(ordered),
    }
