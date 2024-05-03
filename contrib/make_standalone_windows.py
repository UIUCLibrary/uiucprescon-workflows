import abc
import os
import shutil
import tomllib

import pathlib
import zipfile
import subprocess
import argparse
from typing import Optional, List, Union, Dict, Sequence
import pkginfo

LIBS_PATH_NAME = "Lib"


def get_embedded_python(
    embedded_python_archive: Union[str, os.PathLike[str]],
    path: Union[str, os.PathLike[str]],
) -> None:
    """Unzip embedded Python archive."""
    with zipfile.ZipFile(embedded_python_archive) as zipped_file:
        print(f"unzip {embedded_python_archive} to {path}")
        zipped_file.extractall(path=path)


def get_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "python_package",
        help="Install package that contains as a part of your standalone "
             "distribution. This is typically a whl or a tar.gz file."
    )
    parser.add_argument(
        "embedded_python_archive",
        help="This should be the zip archive to a Python embedded version "
             "for Windows, such as python-3.11.9-embed-amd64.zip. You can "
             "find these here https://www.python.org/downloads/. Make sure "
             "you use the version the is listed as \"Windows embeddable "
             "package\"."
    )
    parser.add_argument("--build_path", default="build")
    parser.add_argument("--output_path", default="dist")
    parser.add_argument(
        "-r", "--requirement",
        action="append", default=[],
        help="This is traditionally a requirements.txt file containing a list "
             "of dependencies"
    )
    parser.add_argument(
        "--cpack-variable",
        action="append", default=[],
        help="Explicitly set cpack config variables. This Can be used "
             "multiple times. For example: "
             '--cpack-variable CPACK_PACKAGE_NAME="Speedwagon (UIUC Prescon Edition)"'  # noqa: E501
    )
    parser.add_argument("--use-cpack")
    parser.add_argument("--verbose", action='store_true')
    return parser


def add_path_to_pth_file(
    package_root: Union[str, os.PathLike[str]],
    python_exec: Union[str, os.PathLike[str]],
    library_path: Union[str, os.PathLike[str]],
    pth_file: Union[str, os.PathLike[str]],
) -> None:
    if not os.path.exists(pth_file):
        raise FileNotFoundError(f"{pth_file} is missing")
    abs_full_path_to_libs = os.path.join(package_root, library_path)
    lib_import_path = os.path.relpath(
        abs_full_path_to_libs,
        start=os.path.dirname(python_exec)
    )
    with open(pth_file, "a") as f:
        f.write(f"\n{lib_import_path}\n")


def locate_pth_file(search_path: Union[str, os.PathLike]) -> os.PathLike[str]:
    for entry in os.scandir(str(search_path)):
        if not entry.name.startswith("python"):
            continue
        if not entry.name.endswith("._pth"):
            continue
        return pathlib.Path(entry.path)
    raise FileNotFoundError(f"._pth not found in {search_path}")


def build_embedded_standalone(
    embedded_python_archive: Union[str, os.PathLike[str]],
    python_package: Union[str, os.PathLike[str]],
    build_path: Union[str, os.PathLike[str]],
    additional_requirements_files: Optional[
        List[Union[str, os.PathLike[str]]]
    ] = None
) -> None:

    if os.path.exists(build_path):
        print(f"clearing {build_path}")
        shutil.rmtree(build_path)

    if not os.path.exists(python_package):
        raise FileNotFoundError(f"{python_package} not found")

    get_embedded_python(embedded_python_archive, build_path)
    python_exec = pathlib.Path(build_path) / "python.exe"
    if not python_exec.exists():
        raise FileNotFoundError("missing python executable")

    packages_path = pathlib.Path(build_path) / LIBS_PATH_NAME
    pth_file = locate_pth_file(build_path)

    # pip.main(["install", "pip", "-t", str(packages_path.absolute())])

    add_path_to_pth_file(package_root=build_path,
                         python_exec=os.path.abspath(python_exec),
                         library_path=packages_path.relative_to(build_path),
                         pth_file=pth_file)

    pip_command = [
        "--python", os.path.abspath(python_exec),
        "install", os.path.abspath(python_package),
        "--target", str(packages_path.absolute()),
    ]
    if additional_requirements_files is not None:
        for requirements_file in additional_requirements_files:
            pip_command += ["-r", str(requirements_file)]

    subprocess.run(["pip"] + pip_command, check=True)
    subprocess.run(f"{python_exec} -m speedwagon --version", check=True)


class AbsCPackConfigDataStrategy(abc.ABC):
    @abc.abstractmethod
    def generate_data(self) -> Dict[str, str]:
        pass


class DynamicCPackConfigData(AbsCPackConfigDataStrategy):

    def __str__(self):
        return str(self._cpack_metadata)

    def __init__(self, installed_path: str) -> None:
        self.installed_path = installed_path
        self._cpack_metadata: Dict[str, Union[None, str, Sequence[str]]] = {
            "CPACK_GENERATOR": "WIX",
            "CPACK_INSTALLED_DIRECTORIES": [
                os.path.normcase(
                    os.path.abspath(self.installed_path)
                ).replace("\\", "\\\\"), "."
            ],
            "CPACK_PACKAGE_NAME": None,
            "CPACK_PACKAGE_VENDOR": None,
            "CPACK_PACKAGE_VERSION": None,
            "CPACK_PACKAGE_VERSION_MAJOR": None,
            "CPACK_PACKAGE_VERSION_MINOR": None,
            "CPACK_PACKAGE_VERSION_PATCH": None,
            "CPACK_SYSTEM_NAME": None,
            "CPACK_PACKAGE_FILE_NAME":
                "${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION}-${CPACK_SYSTEM_NAME}",   # noqa: E501
            "CPACK_WIX_SIZEOF_VOID_P": None,
            "CPACK_WIX_ARCHITECTURE": None,
            "CPACK_PACKAGE_EXECUTABLES": ["speedwagon", "Speedwagon"]
        }

    def set_version(
        self,
        major: Union[str, int],
        minor: Union[str, int],
        patch: Union[str, int]
    ) -> None:
        self._cpack_metadata["CPACK_PACKAGE_VERSION"] =\
            f"{major}.{minor}.{patch}"

        self._cpack_metadata["CPACK_PACKAGE_VERSION_MAJOR"] = str(major)
        self._cpack_metadata["CPACK_PACKAGE_VERSION_MINOR"] = str(minor)
        self._cpack_metadata["CPACK_PACKAGE_VERSION_PATCH"] = str(patch)

    def __setitem__(self, key, value):
        self._cpack_metadata[key] = value

    def __getitem__(self, item: str) -> Union[None, str, Sequence[str]]:
        return self._cpack_metadata[item]

    @staticmethod
    def serialize_value(value: Union[str, Sequence[str]]) -> str:
        if isinstance(value, list):
            return " ".join([f'"{sub_value}"' for sub_value in value])
        return f'"{value}"'

    def generate_data(self) -> Dict[str, str]:
        return {
            key: self.serialize_value(value)
            for key, value in self._cpack_metadata.items()
            if value is not None
        }


class Prefilled(AbsCPackConfigDataStrategy):
    def __init__(self, installed_path: str) -> None:
        self.installed_path = installed_path
        self.cpack_metadata: Dict[str, Union[str, Sequence[str]]] = {
            "CPACK_GENERATOR": "WIX",
            "CPACK_PACKAGE_NAME": "Speedwagon - UIUC",
            "CPACK_INSTALLED_DIRECTORIES": [
                os.path.abspath(self.installed_path), "."
            ],
            "CPACK_PACKAGE_VENDOR": "UIUC",
            "CPACK_PACKAGE_VERSION": "0.0.2",
            "CPACK_PACKAGE_VERSION_MAJOR": "0",
            "CPACK_PACKAGE_VERSION_MINOR": "0",
            "CPACK_PACKAGE_VERSION_PATCH": "2",
            "CPACK_PACKAGE_FILE_NAME":
                "${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION}-${CPACK_SYSTEM_NAME}",  # noqa: E501
            "CPACK_RESOURCE_FILE_LICENSE": os.path.abspath("LICENSE.txt"),
            "CPACK_PACKAGE_DESCRIPTION": "something goes here",
            "CPACK_WIX_UPGRADE_GUID": "BD289D57-8F94-4F4D-9B6D-82A532F3514C",
            "CPACK_WIX_ROOT": "C:\\\\Program Files (x86)\\\\WiX Toolset v3.14",
            "CPACK_PACKAGE_INSTALL_DIRECTORY": "Speedwagon - UIUC",
            "CPACK_WIX_SIZEOF_VOID_P": "8",
            "CPACK_WIX_ARCHITECTURE": "x64",
            "CPACK_WIX_PRODUCT_GUID": "84BB7CAB-24DA-46EC-A855-B972384534DB",
            "CPACK_PACKAGE_EXECUTABLES": ["speedwagon", "Speedwagon"]
        }

    @staticmethod
    def serialize_value(value: Union[str, Sequence[str]]) -> str:
        if isinstance(value, list):
            return " ".join([f'"{sub_value}"' for sub_value in value])
        return f'"{value}"'

    def generate_data(self) -> Dict[str, str]:
        return {
            key: self.serialize_value(value)
            for key, value in self.cpack_metadata.items()
        }


def generate_cpack_config_file(
    config_file_name: str,
    config_data_generator: AbsCPackConfigDataStrategy
) -> None:

    with open(config_file_name, "w") as f:
        for k, cmake_value in config_data_generator.generate_data().items():
            f.write(f"set({k} {cmake_value})\n")


class AbsApplicationPackager(abc.ABC):
    def __init__(self, build_path: str, application_root: str) -> None:
        self.application_root = application_root
        self.build_path = build_path
    @abc.abstractmethod
    def package(self) -> str:
        pass


class CPackWixPackager(AbsApplicationPackager):
    def __init__(
        self,
        build_path: str,
        application_root: str,
        cpack_exec
    ) -> None:
        super().__init__(build_path, application_root)
        self.cpack_config_file = os.path.join(build_path, "CPackConfig.cmake")
        self.cpack_config_file_generator: AbsCPackConfigDataStrategy =\
            Prefilled(application_root)
        self.cpack_exec = cpack_exec
        self.verbose = False

    def package(self) -> str:
        generate_cpack_config_file(
            self.cpack_config_file,
            config_data_generator=self.cpack_config_file_generator
        )

        assert self.cpack_exec
        cpack_cmd = [
            self.cpack_exec,
            "--config", os.path.abspath(self.cpack_config_file),
                # "--trace-expand"
            ]
        if self.verbose:
            cpack_cmd.append("--verbose")

        subprocess.run(cpack_cmd, check=True, cwd=self.build_path)
        for entry in os.scandir(self.build_path):
            if not entry.is_file():
                continue
            if not entry.name.lower().endswith(".msi"):
                continue
            return entry.path
        raise FileNotFoundError("No .msi file located")


def build_installer(
    output_path: str,
    packager: AbsApplicationPackager
) -> None:
    generated_artifact = packager.package()
    assert os.path.exists(generated_artifact)
    output_artifact =\
        os.path.join(output_path, pathlib.Path(generated_artifact).name)

    if os.path.exists(output_artifact):
        os.remove(output_artifact)
    shutil.move(generated_artifact, output_path)


def create_application_bootstrap(output_path):
    with open(os.path.join(output_path, "speedwagon.vbs"), "w") as file:
        file.write("""
Set WshShell = WScript.CreateObject("WScript.Shell")
WshShell.Run "pythonw.exe -m speedwagon"
""")


def get_package_metadata(path):
    pkg_dist = pkginfo.Wheel(path)
    return {b: getattr(pkg_dist, b) for b in pkg_dist}


def get_pyproject_toml_metadata() -> Dict[
    str, Union[None, str, Sequence[str]]
]:
    pyproject_toml = os.path.join(os.getcwd(), "pyproject.toml")
    if not os.path.exists(pyproject_toml):
        return {}
    with open(pyproject_toml, "rb") as f:
        data = tomllib.load(f)
    tool_data = data.get('tool', {})
    if not tool_data:
        return {}
    windows_standalone_packager_metadata =\
        tool_data.get('windows_standalone_packager', {})

    if not windows_standalone_packager_metadata:
        return {}

    return windows_standalone_packager_metadata.get(
        'cpack_config_variables',
        {}
    )


def get_cli_metadata(
    args: argparse.Namespace
) -> Dict[str, Union[None, str, Sequence[str]]]:
    # print(args)
    values:  Dict[str, Union[None, str, Sequence[str]]] = {}
    for cpack_variable in args.cpack_variable:
        try:
            key, value = cpack_variable.split("=")
            values[key] = value
        except ValueError as e:
            raise ValueError(
                f"Invalid format: [{cpack_variable}]. "
                "Should be in format, Key=Value."
            ) from e
    return values


def make_license_file(output_file):
    pyproject_toml = os.path.join(os.getcwd(), "pyproject.toml")
    if not os.path.exists(pyproject_toml):
        raise FileNotFoundError("pyproject.toml not found")
    with open(pyproject_toml, "rb") as f:
        data = tomllib.load(f)
    project_metadata = data.get('project', {})
    license_metadata = project_metadata.get('license', {})
    if license_file := license_metadata.get("file"):
        with open(license_file, "r") as f:
            with open(output_file, "w", encoding="utf-8") as wf:
                wf.write(f.read())


def find_cpack_exec(cli_args: argparse.Namespace) -> str:
    """Locate required cpack command."""
    if cli_args.use_cpack:
        return cli_args.use_cpack
    try:
        import cmake
        cpack_exec = shutil.which("cpack", path=cmake.CMAKE_BIN_DIR)
    except ImportError:
        cpack_exec = shutil.which("cpack")

    if not cpack_exec:
        raise FileNotFoundError("cpack command not found.")

    return cpack_exec


def main() -> None:
    parser = get_arg_parser()
    args = parser.parse_args()

    print("Building a standalone Python application")

    standalone_build_path = os.path.join(
        args.build_path,
        "embedded_standalone"
    )

    build_embedded_standalone(
        embedded_python_archive=args.embedded_python_archive,
        python_package=args.python_package,
        build_path=standalone_build_path,
        additional_requirements_files=[
            os.path.abspath(requirements_file) for
            requirements_file in args.requirement
        ])

    license_file = os.path.join(
        standalone_build_path,
        "APPLICATION_LICENSE.txt"
    )

    make_license_file(license_file)

    print("Generating a bootstrap")

    create_application_bootstrap(standalone_build_path)

    print("Building installer")
    cpack_config_generator = DynamicCPackConfigData(standalone_build_path)
    cpack_config_generator['CPACK_RESOURCE_FILE_LICENSE'] =\
        os.path.normcase(
            os.path.abspath(license_file)
        ).replace("\\", "\\\\")

    if args.embedded_python_archive.endswith("amd64.zip"):
        cpack_config_generator["CPACK_SYSTEM_NAME"] = "win64"
        cpack_config_generator["CPACK_WIX_ARCHITECTURE"] = "x64"
        cpack_config_generator["CPACK_WIX_SIZEOF_VOID_P"] = "8"

    elif args.embedded_python_archive.endswith("win32.zip"):
        cpack_config_generator["CPACK_SYSTEM_NAME"] = "win32"
        cpack_config_generator["CPACK_WIX_SIZEOF_VOID_P"] = "4"
    else:
        raise ValueError("Unknown package type")


    # First, add metadata from Python Package
    python_package_metadata = get_package_metadata(args.python_package)
    for key, value in convert_cpack_metadata_from_python_metadata(
        python_package_metadata
    ).items():
        if value is not None:
            cpack_config_generator[key] = value
    assign_package_version_to_generator(
        cpack_config_generator,
        python_package_metadata
    )

    # Second, override any metadata assigned in the Project toml in
    # tool.windows_standalone_packager.cpack_config_variables section
    for key, value in get_pyproject_toml_metadata().items():
        if value is not None:
            cpack_config_generator[key] = value

    # Third, get any cli overrides that need to be modified to the metadata
    for key, value in get_cli_metadata(args).items():
        if value is not None:
            cpack_config_generator[key] = value

    packager = CPackWixPackager(
        build_path=args.build_path,
        application_root=standalone_build_path,
        cpack_exec=find_cpack_exec(args)
    )
    packager.verbose = args.verbose
    packager.cpack_config_file_generator = cpack_config_generator
    build_installer(output_path=args.output_path, packager=packager)


def convert_cpack_metadata_from_python_metadata(
    python_package_metadata: Dict[str, Union[None, str, Sequence[str]]]
):

    description = python_package_metadata.get('description')
    if description is None:
        description = python_package_metadata.get('summary')
    return {
        "CPACK_PACKAGE_NAME": python_package_metadata.get("name"),
        'CPACK_PACKAGE_VENDOR': python_package_metadata.get('author'),
        'CPACK_PACKAGE_DESCRIPTION': description,
        'CPACK_PACKAGE_DESCRIPTION_SUMMARY': python_package_metadata.get(
            'summary')}


def assign_package_version_to_generator(
    cpack_config_generator,
    metadata
) -> None:
    version = metadata['version'].split(".")
    cpack_config_generator.set_version(
        major=version[0],
        minor=version[1],
        patch=version[2]
    )
    version_suffix_types = {
        'a': 'alpha',
        'b': 'beta',
        'dev': 'development'
    }
    if any(suffix in version[-1] for suffix in version_suffix_types):
        for suffix_type in version_suffix_types:
            if suffix_type in version[-1]:
                cpack_config_generator[
                    "CPACK_PACKAGE_FILE_NAME"] = f"${{CPACK_PACKAGE_NAME}}-${{CPACK_PACKAGE_VERSION}}-{version_suffix_types[suffix_type]}-${{CPACK_SYSTEM_NAME}}"  # noqa: E501
                break


if __name__ == '__main__':
    main()
