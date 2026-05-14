import random

from locust import HttpUser, between, events, task

AVAILABLE_SCENARIOS = [
    "normal",
    "cpu",
    "unstable",
    "latency",
]


@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument(
        "--scenario",
        type=str,
        env_var="LOCUST_SCENARIO",
        default="normal",
        choices=AVAILABLE_SCENARIOS,
        help="Traffic scenario",
    )


class MonitoringUser(HttpUser):
    wait_time = between(0.3, 1.0)

    def on_start(self):
        parsed = getattr(self.environment, "parsed_options", None)

        if parsed and hasattr(parsed, "scenario"):
            self.scenario = parsed.scenario
        else:
            self.scenario = "normal"

    @task
    def run_scenario(self):
        if self.scenario == "cpu":
            self.cpu_scenario()

        elif self.scenario == "unstable":
            self.unstable_scenario()

        elif self.scenario == "latency":
            self.latency_scenario()

        else:
            self.normal_scenario()

    def normal_scenario(self):
        endpoint = random.choices(
            population=[
                "health",
                "db",
                "report",
                "cpu",
                "unstable",
            ],
            weights=[30, 35, 15, 10, 10],
            k=1,
        )[0]

        if endpoint == "health":
            self.client.get("/health", name="/health")

        elif endpoint == "db":
            self.client.get(
                "/db-like",
                params={
                    "key": random.choice(
                        [
                            "customers",
                            "orders",
                            "inventory",
                        ]
                    ),
                    "rows": random.randint(10, 80),
                },
                name="/db-like",
            )

        elif endpoint == "report":
            self.client.get(
                "/report",
                params={
                    "batch_size": random.randint(200, 1000),
                    "io_delay_ms": random.randint(80, 250),
                },
                name="/report",
            )

        elif endpoint == "cpu":
            self.client.get(
                "/cpu",
                params={
                    "seconds": round(random.uniform(0.2, 0.7), 2),
                },
                name="/cpu",
            )

        elif endpoint == "unstable":
            self.client.get(
                "/unstable",
                params={
                    "work_units": random.randint(10000, 30000),
                },
                name="/unstable",
            )

    def cpu_scenario(self):
        self.client.get(
            "/cpu",
            params={
                "seconds": round(random.uniform(0.8, 1.5), 2),
            },
            name="/cpu",
        )

    def unstable_scenario(self):
        self.client.get(
            "/unstable",
            params={
                "work_units": random.randint(20000, 60000),
            },
            name="/unstable",
        )

    def latency_scenario(self):
        self.client.get(
            "/db-like",
            params={
                "key": f"latency-{random.randint(1, 999999)}",
                "rows": random.randint(50, 150),
                "force_miss": "true",
            },
            name="/db-like-latency",
        )