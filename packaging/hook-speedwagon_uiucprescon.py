from PyInstaller.utils.hooks import copy_metadata, collect_all
datas, binaries, hiddenimports = collect_all('speedwagon_uiucprescon')
datas += copy_metadata('speedwagon_uiucprescon', recursive=True)
hiddenimports =[
    'speedwagon_uiucprescon.active_workflows',
    'speedwagon_uiucprescon.deprecated_workflows',
    ]