import sys
from pathlib import Path

# Сгенерированный gRPC-клиент profile-service лежит в external_clients/profile_api
_ec = Path(__file__).resolve().parent.parent / "external_clients"
if _ec.is_dir():
    sys.path.insert(0, str(_ec))
