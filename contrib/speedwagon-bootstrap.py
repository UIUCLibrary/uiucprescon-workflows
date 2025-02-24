# nuitka-project-if: {OS} in ("Windows", "Linux", "Darwin", "FreeBSD"):
#    nuitka-project: --standalone
# nuitka-project-if: {OS} == "Darwin":
#    nuitka-project:  --macos-create-app-bundle
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-package-data=speedwagon
# nuitka-project: --include-package=speedwagon
# nuitka-project: --include-package=http.cookies
# nuitka-project: --include-package=pytz_deprecation_shim
from xml.dom import minidom
import xml.etree.ElementTree as ET
import sys
from multiprocessing import freeze_support
import speedwagon.startup

def main():
    parser = speedwagon.config.config.CliArgsSetter.get_arg_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.command is not None:
        speedwagon.startup.run_command(command_name=args.command, args=args)
        return
    app = speedwagon.startup.ApplicationLauncher()
    app.application_name = "Speedwagon: UIUC Prescon Edition"
    app.application_config_directory_name = "speedwagon-prescon"
    app.initialize()
    sys.exit(app.run())


if __name__ == '__main__':
    freeze_support()
    main()
