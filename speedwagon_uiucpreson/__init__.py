from speedwagon.plugins import Plugin
from . import plugin
uiucprescon_plugin: Plugin = plugin.register_active_plugin()
uiucprescon_plugin_deprecated: Plugin = plugin.register_deprecated_plugin()

