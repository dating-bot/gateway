from typing import cast, override

import structlog
from grpclib.const import Status
from grpclib.health.check import ServiceCheck
from grpclib.health.service import OVERALL, Health
from grpclib.health.v1.health_pb2 import HealthCheckRequest, HealthCheckResponse
from grpclib.server import Stream

health_log = structlog.stdlib.get_logger("gateway.health")


async def _health_check() -> bool:
    health_log.info("Health check executed")
    return True


class LoggingHealth(Health):
    @override
    async def Check(self, stream: Stream[HealthCheckRequest, HealthCheckResponse]) -> None:
        request = await stream.recv_message()
        if request is None:
            return

        service_name = request.service or "OVERALL"
        health_log.info("Health check request received", service=service_name)

        try:
            checks = self._checks.get(request.service)
            if checks is None:
                await stream.send_trailing_metadata(status=Status.NOT_FOUND)
                health_log.warning("Health check service not found", service=service_name)
                return

            status = HealthCheckResponse.ServingStatus.SERVING
            for check in checks:
                try:
                    result: bool | None = cast("bool | None", await check()) if callable(check) else True
                    if result is False:
                        status = HealthCheckResponse.ServingStatus.NOT_SERVING
                        break
                    if result is None:
                        status = HealthCheckResponse.ServingStatus.UNKNOWN
                except Exception as e:
                    health_log.warning("Health check failed", service=service_name, check_error=str(e))
                    status = HealthCheckResponse.ServingStatus.NOT_SERVING
                    break

            response = HealthCheckResponse(status=status)
            await stream.send_message(response)
            health_log.info("Health check completed successfully", service=service_name, status=status)
        except Exception as e:
            health_log.exception("Health check failed", service=service_name, error=e)
            raise


def create_health_service() -> LoggingHealth:
    health_check = ServiceCheck(_health_check, check_ttl=30.0, check_timeout=5.0)
    return LoggingHealth({OVERALL: [health_check]})
