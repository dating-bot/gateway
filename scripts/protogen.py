# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "grpcio-tools==1.71.2",
#     "protobuf>=5.28.0,<6",
#     "mypy-protobuf==3.7.0",
#     "gitpython>=3.1.45",
#     "rich>=14.2.0",
#     "typer>=0.19.2",
#     "protoletariat==3.3.10",
#     "grpclib[protobuf]>=0.4.9",
#     "betterproto2>=0.9.1",
#     "betterproto2-compiler>=0.9.0",
# ]
# ///


import subprocess
from functools import wraps
from pathlib import Path
from tempfile import mkdtemp
from typing import Annotated, Literal

import typer
from git import Repo
from grpc_tools import protoc
from rich import print

app = typer.Typer()


def typer_exit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[red]ERR: {e}[/red]")
            raise typer.Exit(1) from e

    return wrapper


def preprate_output(output_directory: str) -> Path:
    dir = Path(output_directory)
    dir.mkdir(parents=True, exist_ok=True)

    if not dir.is_dir():
        raise RuntimeError(f"output directory {dir} is not a directory")

    return dir


def prepare_protos(proto_files: list[str]) -> list[Path]:
    if not proto_files:
        raise ValueError("no proto files provided")

    proto_file_paths = [Path(proto_file) for proto_file in proto_files]

    for path in proto_file_paths:
        if path.is_dir():
            raise ValueError(f"proto file {path} is a directory")

        if not path.exists():
            raise FileNotFoundError(f"proto file {path} does not exist")

    return proto_file_paths


def prepate_includes(include_paths: list[str]) -> list[Path]:
    include_file_paths = [Path(include_path) for include_path in include_paths]

    for path in include_file_paths:
        if not path.exists():
            raise FileNotFoundError(f"include path {path} does not exist")

    return include_file_paths


def get_betterprot2_args(
    what: Literal["client", "server", "both"],
    output: str,
    protos: list[str],
    include: list[str],
    opts: str | None = None,
) -> list[list[str]]:
    common = [
        "protoc",
        f"--proto_path={protoc._get_resource_file_name('grpc_tools', '_proto')}",
        *[f"--proto_path={item}" for item in include],
        f"--python_betterproto2_out={output}",
    ]

    if opts is not None:
        return [[*common, f"--python_betterproto2_opt={opts}", *protos]]

    if what == "client":
        return [[*common, "--python_betterproto2_opt=client_generation=async", *protos]]
    if what == "server":
        return [[*common, "--python_betterproto2_opt=server_generation=async", *protos]]

    if what == "both":
        return [
            [*common, "--python_betterproto2_opt=client_generation=async", *protos],
            [*common, "--python_betterproto2_opt=server_generation=async", *protos],
        ]

    raise RuntimeError(f"generation type {what} is not supported")


def get_grpcio_args(
    what: Literal["client", "server", "both"],
    output: str,
    protos: list[str],
    include: list[str],
    opts: str | None = None,
) -> list[list[str]]:
    _ = what  # grpcio always generates both

    args = [
        "protoc",
        f"--proto_path={protoc._get_resource_file_name('grpc_tools', '_proto')}",
        *[f"--proto_path={item}" for item in include],
        f"--python_out={output}",
        f"--grpc_python_out={output}",
        f"--mypy_out={output}",
        *protos,
    ]

    return [args]


def get_grpclib_args(
    what: Literal["client", "server", "both"],
    output: str,
    protos: list[str],
    include: list[str],
    opts: str | None = None,
) -> list[list[str]]:
    _ = what  # grpclib always generates both

    args = [
        "protoc",
        f"--proto_path={protoc._get_resource_file_name('grpc_tools', '_proto')}",
        *[f"--proto_path={item}" for item in include],
        f"--python_out={output}",
        f"--grpclib_python_out={output}",
        f"--mypy_out={output}",
        *protos,
    ]

    return [args]


def fix_grpcio_init_files(
    output_directory: Path,
    include: list[str],
    protos: list[str],
):
    subprocess.run(
        [
            "protol",
            "--create-package",
            "--in-place",
            "--python-out",
            output_directory.as_posix(),
            "protoc",
            "--protoc-path",
            "python3 -m grpc_tools.protoc",
            f"--proto-path={protoc._get_resource_file_name('grpc_tools', '_proto')}",
            *[f"--proto-path={item}" for item in include],
            *protos,
        ],
        check=False,
    )


@typer_exit
def generate(
    what: Annotated[Literal["client", "server", "both"], typer.Option(help="Тип генерируемого кода")],
    path: Annotated[list[str], typer.Option(help="Пути до proto файлов внутри репозитория или текущей папки")],
    outd: Annotated[str, typer.Option(help="Путь до директории для сгенерированных файлов")],
    opts: Annotated[str | None, typer.Option(help="Опции для генерации")] = None,
    repo: Annotated[str | None, typer.Option(help="Репозиторий из которого нужно сгенерировать файлы")] = None,
    hash: Annotated[str | None, typer.Option(help="Хэш коммита, с которого взять файл")] = None,
    incl: Annotated[list[str] | None, typer.Option(help="Список путей для включения в компиляцию")] = None,
    cmpl: Annotated[
        Literal["betterproto2", "grpcio", "grpclib"], typer.Option(help="Компилятор для генерации")
    ] = "grpcio",
):
    if incl is None:
        incl = []

    output_directory = preprate_output(outd)

    if hash is not None and repo is None:
        raise RuntimeError("hash provided without repo")

    if repo is not None:
        temporary_directory = Path(mkdtemp()).absolute()
        repository = Repo.clone_from(repo, to_path=temporary_directory)
        repository.git.checkout(hash)

        path = [(temporary_directory / p).as_posix() for p in path]
        incl = [(temporary_directory / i).as_posix() for i in incl]

    proto_files = prepare_protos(path)
    includes = prepate_includes(incl)

    args = []
    if cmpl == "betterproto2":
        args = get_betterprot2_args(
            what,
            output_directory.as_posix(),
            [p.as_posix() for p in proto_files],
            [i.as_posix() for i in includes],
            opts,
        )
    elif cmpl == "grpcio":
        args = get_grpcio_args(
            what,
            output_directory.as_posix(),
            [p.as_posix() for p in proto_files],
            [i.as_posix() for i in includes],
            opts,
        )
    elif cmpl == "grpclib":
        args = get_grpclib_args(
            what,
            output_directory.as_posix(),
            [p.as_posix() for p in proto_files],
            [i.as_posix() for i in includes],
            opts,
        )
    else:
        raise ValueError(f"Unknown compiler: {cmpl}")

    for arg_set in args:
        failed = protoc.main(arg_set)
        if failed:
            raise RuntimeError(f"protoc failed with args: {' '.join(arg_set)}")

    if cmpl == "grpcio" or cmpl == "grpclib":
        fix_grpcio_init_files(output_directory, [i.as_posix() for i in includes], [p.as_posix() for p in proto_files])


if __name__ == "__main__":
    typer.run(generate)
