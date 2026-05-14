import asyncio
import hashlib
import os
import random
import time
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

APP_STARTED_AT = time.time()
CACHE_TTL_SECONDS = 20

app = FastAPI(title="Monitoring Demo API", version="1.0.0")

REQUESTS_TOTAL = Counter(
    "http_requests",
    "Total HTTP requests",
    ["endpoint", "method", "status"],
)
REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint", "method"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
CACHE_OPERATIONS = Counter(
    "db_cache_operations",
    "Cache operations for the DB-like endpoint",
    ["result"],
)
UNSTABLE_ERRORS = Counter(
    "unstable_endpoint_errors",
    "Unstable endpoint failures",
    ["reason"],
)
CONCURRENT_REQUESTS = Gauge(
    "concurrent_requests",
    "Overall concurrent HTTP requests",
)
CPU_HEAVY_REQUESTS_IN_PROGRESS = Gauge(
    "cpu_heavy_requests_in_progress",
    "CPU-heavy requests currently in progress",
)

CACHE_LOCK = asyncio.Lock()


@dataclass
class CacheEntry:
    value: dict[str, Any]
    expires_at: float


CACHE: dict[str, CacheEntry] = {}


def endpoint_label(path: str) -> str:
    normalized = path.rstrip("/") or "/"
    mapping = {
        "/": "root",
        "/health": "health",
        "/db-like": "db_like",
        "/cpu": "cpu",
        "/report": "report",
        "/unstable": "unstable",
        "/metrics": "metrics",
    }
    return mapping.get(normalized, "other")


def current_concurrency() -> float:
    return float(CONCURRENT_REQUESTS._value.get())


@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    endpoint = endpoint_label(request.url.path)
    method = request.method
    status_code = "500"

    CONCURRENT_REQUESTS.inc()
    started = time.perf_counter()
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    except Exception:
        status_code = "500"
        raise
    finally:
        elapsed = time.perf_counter() - started
        REQUEST_DURATION_SECONDS.labels(endpoint=endpoint, method=method).observe(elapsed)
        REQUESTS_TOTAL.labels(endpoint=endpoint, method=method, status=status_code).inc()
        CONCURRENT_REQUESTS.dec()


@app.get("/", response_class=HTMLResponse)
async def root():
    uptime = round(time.time() - APP_STARTED_AT, 2)
    return f"""
    <html>
      <head><title>Monitoring Demo API</title></head>
      <body>
        <h1>Monitoring Demo API</h1>
        <p>Uptime: {uptime}s</p>
        <ul>
          <li><a href="/health">/health</a></li>
          <li><a href="/db-like?key=customers&rows=25">/db-like</a></li>
          <li><a href="/cpu?seconds=0.6">/cpu</a></li>
          <li><a href="/report">/report</a></li>
          <li><a href="/unstable">/unstable</a></li>
          <li><a href="/metrics">/metrics</a></li>
        </ul>
      </body>
    </html>
    """


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - APP_STARTED_AT, 2),
    }


@app.get("/db-like")
async def db_like(
        key: str = Query("customers:active"),
        rows: int = Query(25, ge=1, le=200),
        force_miss: bool = Query(False),
):
    cache_key = f"{key}:{rows}"
    now = time.time()

    async with CACHE_LOCK:
        cached = CACHE.get(cache_key)
        hit = cached is not None and cached.expires_at > now and not force_miss
        cached_value = cached.value if hit and cached is not None else None

    if hit and cached_value is not None:
        CACHE_OPERATIONS.labels(result="hit").inc()
        await asyncio.sleep(random.uniform(0.008, 0.03))
        payload = cached_value
        cache_state = "hit"
    else:
        CACHE_OPERATIONS.labels(result="miss").inc()
        await asyncio.sleep(random.uniform(0.18, 0.55))
        records = [
            {
                "id": i + 1,
                "amount": round(random.uniform(10.0, 500.0), 2),
                "bucket": random.choice(["bronze", "silver", "gold"]),
            }
            for i in range(rows)
        ]
        payload = {
            "key": key,
            "rows": rows,
            "records": records,
            "summary": {
                "count": len(records),
                "total_amount": round(sum(item["amount"] for item in records), 2),
                "avg_amount": round(sum(item["amount"] for item in records) / len(records), 2),
            },
        }
        async with CACHE_LOCK:
            CACHE[cache_key] = CacheEntry(value=payload, expires_at=time.time() + CACHE_TTL_SECONDS)
        cache_state = "miss"

    return {
        "cache_state": cache_state,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "key": key,
        "rows": rows,
        "summary": payload["summary"],
    }


def burn_cpu(seconds: float) -> dict[str, Any]:
    deadline = time.perf_counter() + seconds
    value = 0
    iterations = 0
    checksum = b""
    while time.perf_counter() < deadline:
        value = (value * 33 + iterations + 17) % 2_147_483_647
        checksum = hashlib.sha256(f"{value}:{iterations}".encode()).digest()
        iterations += 1
    return {
        "iterations": iterations,
        "checksum": checksum.hex()[:16],
    }


@app.get("/cpu")
async def cpu(seconds: float = Query(0.6, ge=0.1, le=4.0)):
    CPU_HEAVY_REQUESTS_IN_PROGRESS.inc()
    try:
        result = await asyncio.to_thread(burn_cpu, seconds)
        return {
            "seconds": seconds,
            **result,
        }
    finally:
        CPU_HEAVY_REQUESTS_IN_PROGRESS.dec()


@app.get("/report")
async def report(
        batch_size: int = Query(250, ge=20, le=5000),
        io_delay_ms: int = Query(120, ge=10, le=1000),
):
    await asyncio.sleep(io_delay_ms / 1000 + random.uniform(0.05, 0.15))

    categories = ["payments", "users", "orders", "inventory", "alerts"]
    totals: dict[str, float] = {k: 0.0 for k in categories}
    counts: dict[str, int] = {k: 0 for k in categories}

    for _ in range(batch_size):
        category = random.choice(categories)
        amount = round(random.uniform(1.0, 250.0), 2)
        totals[category] += amount
        counts[category] += 1

    top = sorted(
        (
            {
                "category": category,
                "count": counts[category],
                "total_amount": round(totals[category], 2),
            }
            for category in categories
        ),
        key=lambda item: item["total_amount"],
        reverse=True,
    )

    return {
        "batch_size": batch_size,
        "io_delay_ms": io_delay_ms,
        "top_categories": top[:3],
        "grand_total": round(sum(totals.values()), 2),
    }


@app.get("/unstable")
async def unstable(
        work_units: int = Query(15000, ge=1000, le=200000),
):
    concurrency = max(1.0, current_concurrency())
    pressure = min(0.80, concurrency / 15.0)
    random_component = random.uniform(0.0, 0.10)
    error_probability = min(0.95, 0.03 + pressure + random_component)

    await asyncio.sleep(random.uniform(0.01, 0.08))

    if random.random() < error_probability:
        UNSTABLE_ERRORS.labels(reason="load_induced").inc()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "overloaded",
                "concurrency": round(concurrency, 2),
                "error_probability": round(error_probability, 3),
            },
        )

    digest = 0
    for i in range(work_units):
        digest = (digest * 131 + i) % 1_000_000_007

    return {
        "status": "ok",
        "concurrency": round(concurrency, 2),
        "error_probability": round(error_probability, 3),
        "digest": digest,
    }


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
