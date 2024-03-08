import email.message
import shutil
import subprocess
import argparse
import jinja2
import PyInstaller.__main__
import PyInstaller.building.makespec
import PyInstaller.building.build_main
import os
import cmake
import platform
from importlib import metadata

SPEC_FILE = "Speedwagon.spec"

TOP_LEVEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

WORKPATH = os.path.join(
    TOP_LEVEL_DIR, "build", "build_speedwagon", "macos_standalone"
)


def package(specs_file, dest):
    if not os.path.exists(
            os.path.join(WORKPATH, "hook-speedwagon_uiucprescon.tasks.py")
    ):
        create_hook_file(
            TOP_LEVEL_DIR,
            WORKPATH,
            hook_name="hook-speedwagon_uiucprescon.tasks.py"
        )

    PyInstaller.__main__.run([
        '--noconfirm',
        specs_file,
        "--distpath", dest,
        "--workpath", WORKPATH,
        "--clean"
    ])
    for entry in os.scandir(dest):
        if entry.name.endswith(".app"):
            return entry.path
    raise FileNotFoundError("app not found in destination after building")


def get_args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("package")
    parser.add_argument("--dist", default=os.path.join(TOP_LEVEL_DIR, "dist"))
    parser.add_argument("--app-name", default="Speedwagon UIUC Prescon.app")

    return parser


def main():
    args_parser = get_args_parser()
    args = args_parser.parse_args()
    speedwagon_metadata = metadata.metadata(args.package)

    app_build_path = os.path.join(TOP_LEVEL_DIR, "build", "MacOS App")

    package_file = package(
        specs_file=os.path.join(os.path.dirname(__file__), SPEC_FILE),
        dest=app_build_path
    )
    print("Writing CPackConfig.cmake")
    cpack_config_file = write_cpack_config_file(
        package_file,
        destination_path=WORKPATH,
        package_metadata=speedwagon_metadata,
        app_name=args.app_name
    )

    print(f"Running CPack with {cpack_config_file}")
    run_cpack(cpack_config_file,
              build_path=args.dist
              )


def only_workflows(entry: os.DirEntry["str"]):
    if not entry.is_file():
        return False
    if entry.name == "__init__.py":
        return False
    if not entry.name.endswith(".py"):
        return False
    return True


def get_workflow_modules(root: str, src: str):
    tree = os.scandir(os.path.join(root, src))
    subpackage = src.replace("/", ".")
    for s in filter(only_workflows, tree):
        a = os.path.splitext(s.name)[0]
        yield f"{subpackage}.{a}"


class HookGenerator:
    def __init__(self, filename):
        self.filename = filename
        self._hidden_imports = []

    def add_hidden_import(self, value):
        self._hidden_imports.append(value)

    def write(self):
        print(f"Writing to {self.filename}")
        with open(self.filename, "w", encoding="utf-8") as write_file:
            write_file.write('hiddenimports = [\n')
            for hidden_import in self._hidden_imports:
                write_file.write(f'    "{hidden_import}",\n')

            write_file.write(']\n')


def create_hook_file(
        package_path,
        output_path,
        hook_name="speedwagon_uiucprescon.tasks.py"
):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    hook_generator = \
        HookGenerator(os.path.join(output_path, hook_name))

    for x in get_workflow_modules(package_path,
                                  os.path.join("speedwagon_uiucprescon", "tasks")):
        hook_generator.add_hidden_import(x)
        print(f"Added to hiddenignore: {x}")
    hook_generator.write()


def get_default_cpack_data(app_name):
    return {
        "CPACK_INSTALLED_DIRECTORIES": {
            "output": f"/{app_name}"
        },
        "CPACK_PACKAGE_NAME": "Speedwagon",
        "CPACK_GENERATOR": "DragNDrop",
        "CPACK_PACKAGE_VENDOR":
            "University Library at The University of Illinois at Urbana "
            "Champaign: Preservation Services",
    }


def dmg_package_name(package_metadata):
    if "arm64" in platform.platform():
        platform_info = "arm64"
    elif "x86_64" in platform.platform():
        platform_info = "x86_64"
    else:
        platform_info = platform.system().lower()
    return f"speedwagon-UIUC_Prescon-{package_metadata['Version']}-{platform_info}"


def write_cpack_config_file(
        source_app,
        destination_path,
        package_metadata: email.message.Message,
        app_name: str,
):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            os.path.abspath(os.path.join(os.path.dirname(__file__)))),
        autoescape=jinja2.select_autoescape()
    )
    template = env.get_template("CPackConfig.cmake.in")

    data = {**get_default_cpack_data(app_name=app_name), **{
        "CPACK_INSTALLED_DIRECTORIES": {
            "source": source_app,
            "output": f"/{app_name}"
        },
        "CPACK_PACKAGE_FILE_NAME": dmg_package_name(package_metadata),
        "CPACK_PACKAGE_VERSION": package_metadata['Version'],
        "CPACK_RESOURCE_FILE_LICENSE": os.path.join(TOP_LEVEL_DIR, "LICENSE"),
        "CPACK_PACKAGE_DESCRIPTION_FILE":
            os.path.join(TOP_LEVEL_DIR, "README.md")
    }}
    config_file = os.path.join(destination_path, "CPackConfig.cmake")
    with open(config_file, "w") as writer:
        writer.write(template.render(**data))
    return os.path.abspath(config_file)


def run_cpack(
        config_file,
        build_path: str = os.path.join(TOP_LEVEL_DIR, "dist"),
):
    cpack_cmd = shutil.which("cpack", path=cmake.CMAKE_BIN_DIR)
    args = [
        "--config", config_file,
        "-B", build_path,
        "-G", "DragNDrop"
    ]
    subprocess.check_call([cpack_cmd] + args)


if __name__ == '__main__':
    main()
