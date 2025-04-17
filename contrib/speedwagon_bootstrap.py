# nuitka-project-if: {OS} in ("Windows", "Linux", "Darwin", "FreeBSD"):
#    nuitka-project: --standalone
# nuitka-project-if: {OS} == "Darwin":
#    nuitka-project:  --macos-create-app-bundle
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --include-package-data=speedwagon
# nuitka-project: --include-package=speedwagon
# nuitka-project: --include-package=http.cookies
# nuitka-project: --include-package=pytz_deprecation_shim
"""Bootstrapping the application when running as standalone."""
import os.path
from multiprocessing import freeze_support
import sys

CONFIG_DIRECTORY_NAME = "speedwagon-prescon"

DEFAULT_CONFIG_DATA = """
[GLOBAL]
starting-tab = All
debug = True

[PLUGINS.speedwagon_uiucprescon.active_workflows]
uiucprescon_active_workflows = True

""".strip()

def main():  # pragma: no cover
    """Run main application."""
    # import speedwagon.startup
    import speedwagon.config.config

    parser = speedwagon.config.config.CliArgsSetter.get_arg_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.command is not None:
        speedwagon.startup.run_command(command_name=args.command, args=args)
        return
    app = speedwagon.startup.ApplicationLauncher()
    app.application_name = "Speedwagon: UIUC Prescon Edition"
    app.application_config_directory_name = CONFIG_DIRECTORY_NAME

    def verify_plugin_start(_: speedwagon.config.config.AbsConfigSettings, config_file_location):
        app_data_directory = config_file_location['app_data_directory']

        if not os.path.exists(app_data_directory):
            os.makedirs(app_data_directory)

        config_ini = os.path.join(
            app_data_directory,
            speedwagon.config.config.CONFIG_INI_FILE_NAME
        )
        if not os.path.exists(config_ini):
            with open(config_ini, "w") as f:
                print(f"Creating a new config file at {config_ini}")
                f.write(DEFAULT_CONFIG_DATA)
                f.write("\n")


    app.startup_tasks = [
        verify_plugin_start
        ]
    app.initialize()
    sys.exit(app.run())


if __name__ == '__main__':
    freeze_support()
    main()
