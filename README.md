# Prometheus + Grafana Observability Demo

> [Project Architecture Image Placeholder]

A full-stack observability demo built with FastAPI, Prometheus, Grafana, Alertmanager, cAdvisor, Node Exporter, and
Locust.

This project is designed for workshops, university presentations, and local demonstrations to showcase modern monitoring
and observability concepts in distributed systems and backend applications.

The demo simulates real-world application behaviors such as latency spikes, CPU-intensive workloads, unstable endpoints,
cache hit/miss patterns, concurrent traffic, and reporting workloads. These behaviors can then be monitored through
metrics, dashboards, and alerting pipelines.

The stack provides an end-to-end observability environment where you can:

- Monitor application and infrastructure metrics
- Visualize system behavior with Grafana dashboards
- Analyze request latency and p95 response times
- Trigger and inspect Prometheus alerts
- Generate realistic traffic using Locust
- Observe container-level resource usage

# Table of Contents

- [Stack](#stack)
- [Features](#features)
	- [Demo API Endpoints](#demo-api-endpoints)
	- [Metrics](#metrics)
	- [Alerts](#alerts)
- [Getting Started](#getting-started)
	- [Prerequisites](#prerequisites)
	- [Quick Start](#quick-start)
- [Services](#services)
- [Grafana](#grafana)
- [Usage](#usage)
	- [Useful Commands](#useful-commands)
	- [Locust Load Testing](#locust-load-testing)

# Stack

- FastAPI
- Prometheus
- Grafana
- Alertmanager
- Node Exporter
- cAdvisor
- Locust

# Features

## Demo API Endpoints

| Endpoint    | Description                                                                         |
|-------------|-------------------------------------------------------------------------------------|
| `/health`   | Lightweight health check endpoint used for uptime verification and monitoring       |
| `/db-like`  | Simulates database-style queries with cache hit/miss behavior and variable latency  |
| `/cpu`      | CPU-intensive endpoint used to generate high processor usage for monitoring demos   |
| `/report`   | Simulates heavy reporting workloads with configurable batch size and I/O delay      |
| `/unstable` | Intentionally unstable endpoint that can produce intermittent 5xx errors under load |
| `/metrics`  | Prometheus metrics endpoint exposing application telemetry                          |

## Metrics

The application exposes metrics for:

- Request count by endpoint, method, and status code
- Request latency histograms
- p95 latency calculations
- Cache hit/miss counters
- Error rates for unstable endpoints
- Concurrent requests
- CPU-heavy requests in progress
- Container and host resource usage

## Alerts

Included Prometheus alert rules:

- High unstable endpoint error rate
- High p95 latency on the DB-like endpoint
- Container CPU usage alerts
- cAdvisor availability alerts

# Getting Started

## Prerequisites

- Docker
- Docker Compose

## Quick Start

```bash
docker compose up --build
```

# Services

| Service       | URL                   |
|---------------|-----------------------|
| FastAPI App   | http://localhost:8000 |
| Prometheus    | http://localhost:9090 |
| Alertmanager  | http://localhost:9093 |
| Grafana       | http://localhost:3000 |
| Locust        | http://localhost:8089 |
| Node Exporter | http://localhost:9100 |
| cAdvisor      | http://localhost:8080 |
| MailHog       | http://localhost:8025 |

# Grafana

A demo dashboard is automatically provisioned during startup.

Default Grafana URL:

```text
http://localhost:3000
```

# Usage

## Useful Commands

### Start Project

```bash
docker compose up --build
```

### Stop Project

```bash
docker compose stop
```

## Locust Load Testing

Locust is included to generate different traffic patterns and demonstrate monitoring scenarios such as high CPU usage,
unstable endpoints, latency spikes, and concurrent traffic.

### Open Locust UI

After starting the stack, open:

```text
http://localhost:8089
```

### Run Locust

Start the Locust worker from inside the application container:

```bash
docker compose exec app bash -c "uv run locust -f locustfile.py --host http://localhost:8000"
```

### Select a Scenario

The active traffic scenario is selected directly from the Locust web UI.

Available demo scenarios include:

- Normal traffic
- CPU-intensive workload
- Unstable endpoint stress
- Latency-focused traffic

This allows you to demonstrate how different traffic patterns affect system behavior and observability data in real
time.

## Credits

This project includes ideas and configurations inspired
by [DevOps_Certification](https://github.com/AhmadRafiee/DevOps_Certification), adapted for educational and
demonstration purposes.
