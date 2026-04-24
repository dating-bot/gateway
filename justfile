set dotenv-load := true
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

manage := "uv run"

default:
    @just --choose

generate-gateway-api:
    buf lint
    buf format --write
    just generate-gateway-api-{{ os() }}

alias generate-gateway-api-macos := generate-gateway-api-linux

generate-gateway-api-linux:
    rm -rf gateway_api
    mkdir -p gateway_api
    docker run --rm -v ./gateway_api:/gateway_api:rw -v ./api:/api:ro -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2 \
            protol --in-place --create-package --python-out gateway_api \
            protoc --protoc-path="python3 -m grpc_tools.protoc" \
            -p /api \
            --python_out=/gateway_api --grpclib_python_out=/gateway_api --mypy_out=/gateway_api \
            gateway_api/v1/gateway.proto
    if [ -d gateway_api/gateway_api/v1 ]; then \
        rm -rf gateway_api/v1; \
        mv gateway_api/gateway_api/v1 gateway_api/v1; \
        rm -rf gateway_api/gateway_api; \
    fi

generate-gateway-api-windows:
    Remove-Item -Recurse -Force .\\gateway_api
    mkdir gateway_api
    docker run --rm -v .\\gateway_api:/gateway_api:rw -v .\\api:/api:ro -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2 \
            protol --in-place --create-package --python-out gateway_api \
            protoc --protoc-path="python3 -m grpc_tools.protoc" \
            -p /api \
            --python_out=/gateway_api --grpclib_python_out=/gateway_api --mypy_out=/gateway_api \
            gateway_api/v1/gateway.proto
    powershell -NoProfile -Command "if (Test-Path 'gateway_api/gateway_api/v1') { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue 'gateway_api/v1'; Move-Item 'gateway_api/gateway_api/v1' 'gateway_api/v1'; Remove-Item -Recurse -Force 'gateway_api/gateway_api' }"

# Клиент profile-service: proto из ../profile_service/api, вывод в external_clients (как в pechkin — Docker + protol + protoc)
generate-profile-service-client:
    (cd ../profile_service && buf lint && buf format --write)
    just generate-profile-service-client-{{ os() }}

alias generate-profile-service-client-macos := generate-profile-service-client-linux

generate-profile-service-client-linux:
    rm -rf external_clients/profile_api
    mkdir -p external_clients
    docker run --rm \
        -v ./external_clients:/external_clients:rw \
        -v ../profile_service/api:/api:ro \
        -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out external_clients \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=/api --python_out=/external_clients --grpclib_python_out=/external_clients --mypy_out=/external_clients \
                profile_api/v1/profile.proto

generate-profile-service-client-windows:
    Remove-Item -Recurse -Force .\\external_clients\\profile_api -ErrorAction SilentlyContinue
    mkdir -Force .\\external_clients | Out-Null
    docker run --rm \
        -v .\external_clients:/external_clients:rw \
        -v ..\profile_service\api:/api:ro \
        -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out external_clients \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=/api --python_out=/external_clients --grpclib_python_out=/external_clients --mypy_out=/external_clients \
                profile_api/v1/profile.proto

generate-match-service-client:
    (cd ../match_service && buf lint && buf format --write)
    just generate-match-service-client-{{ os() }}

alias generate-match-service-client-macos := generate-match-service-client-linux

generate-match-service-client-linux:
    rm -rf external_clients/match_api
    mkdir -p external_clients
    docker run --rm \
        -v ./external_clients:/external_clients:rw \
        -v ../match_service/api:/api:ro \
        -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out external_clients \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=/api --python_out=/external_clients --grpclib_python_out=/external_clients --mypy_out=/external_clients \
                match_api/v1/match.proto

generate-match-service-client-windows:
    Remove-Item -Recurse -Force .\external_clients\match_api -ErrorAction SilentlyContinue
    mkdir -Force .\external_clients | Out-Null
    docker run --rm \
        -v .\external_clients:/external_clients:rw \
        -v ..\match_service\api:/api:ro \
        -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out external_clients \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=/api --python_out=/external_clients --grpclib_python_out=/external_clients --mypy_out=/external_clients \
                match_api/v1/match.proto

generate-ranking-service-client:
    (cd ../ranking_service && buf lint && buf format --write)
    just generate-ranking-service-client-{{ os() }}

alias generate-ranking-service-client-macos := generate-ranking-service-client-linux

generate-ranking-service-client-linux:
    rm -rf external_clients/ranking_api
    mkdir -p external_clients
    docker run --rm \
        -v ./external_clients:/external_clients:rw \
        -v ../ranking_service/api:/api:ro \
        -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out external_clients \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=/api --python_out=/external_clients --grpclib_python_out=/external_clients --mypy_out=/external_clients \
                ranking_api/v1/ranking.proto

generate-ranking-service-client-windows:
    Remove-Item -Recurse -Force .\external_clients\ranking_api -ErrorAction SilentlyContinue
    mkdir -Force .\external_clients | Out-Null
    docker run --rm \
        -v .\external_clients:/external_clients:rw \
        -v ..\ranking_service\api:/api:ro \
        -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out external_clients \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=/api --python_out=/external_clients --grpclib_python_out=/external_clients --mypy_out=/external_clients \
                ranking_api/v1/ranking.proto

lint:
    {{ manage }} ruff format .
    {{ manage }} ruff check --fix .
    {{ manage }} mypy . --install-types --non-interactive --ignore-missing-imports --disable-error-code var-annotated --disable-error-code import-untyped --disable-error-code type-abstract
    {{ manage }} basedpyright .

run-tests:
    {{ manage }} pytest --failed-first --verbose --no-header
