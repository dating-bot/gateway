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
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out gateway_api \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=api --python_out=. --grpclib_python_out=. --mypy_out=. \
                gateway_api/v1/gateway.proto

generate-gateway-api-windows:
    Remove-Item -Recurse -Force .\\gateway_api
    mkdir gateway_api
    docker run --rm -v .\\gateway_api:/gateway_api:rw -v .\\api:/api:ro -w / ghcr.io/astral-sh/uv:python3.13-bookworm-slim \
        uv run --with 'protoletariat==3.3.10,grpclib[protobuf]==0.4.9,mypy-protobuf==3.7.0,grpcio_tools==1.71.2' \
            protol --in-place --create-package --python-out gateway_api \
            protoc --protoc-path="python3 -m grpc_tools.protoc" --proto-path=api --python_out=. --grpclib_python_out=. --mypy_out=. \
                gateway_api/v1/gateway.proto

generate-external-clients:
    just generate-external-clients-{{ os() }}

alias generate-external-clients-macos := generate-external-clients-linux

generate-external-clients-linux:
    rm -rf external_clients/profile_api
    mkdir -p external_clients
    uv run scripts/protogen.py \
        --what client \
        --path ../profile_service/api/profile_api/v1/profile.proto \
        --incl ../profile_service/api \
        --cmpl grpclib \
        --outd external_clients

generate-external-clients-windows:
    Remove-Item -Recurse -Force .\\external_clients\\profile_api -ErrorAction SilentlyContinue
    mkdir -Force external_clients
    uv run scripts/protogen.py \
        --what client \
        --path ..\\profile_service\\api\\profile_api\\v1\\profile.proto \
        --incl ..\\profile_service\\api \
        --cmpl grpclib \
        --outd external_clients

lint:
    {{ manage }} ruff format .
    {{ manage }} ruff check --fix .
    {{ manage }} mypy . --install-types --non-interactive --ignore-missing-imports --disable-error-code var-annotated --disable-error-code import-untyped --disable-error-code type-abstract
    {{ manage }} basedpyright .

run-tests:
    {{ manage }} pytest --failed-first --verbose --no-header

infra:
    docker compose up -d valkey
