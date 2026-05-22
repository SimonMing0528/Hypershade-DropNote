# Reloads Hypershade DropNote during development.
from __future__ import absolute_import

import os
import sys

import maya.cmds as cmds


PROJECT_ROOT = r"F:\R_D\HyperShade Notes\Developement Files\HyperShade Notes"
PLUGIN_PATH = r"F:\R_D\HyperShade Notes\Developement Files\HyperShade Notes\plug-ins\HypershadeDropNote.py"
PLUGIN_NAME = "HypershadeDropNote.py"
MODULE_NAME = "hypershade_dropnote"


def ensure_project_root():
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)


def cleanup_old_runtime():
    module = sys.modules.get(MODULE_NAME)
    if module and hasattr(module, "cleanup_runtime_items"):
        try:
            module.cleanup_runtime_items()
        except Exception as error:
            print("Hypershade DropNote reload: cleanup warning: %s" % error)


def unload_plugin():
    try:
        if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
            cmds.unloadPlugin(PLUGIN_NAME)
    except Exception as error:
        print("Hypershade DropNote reload: unload warning: %s" % error)


def clear_modules():
    for name in list(sys.modules.keys()):
        if name == MODULE_NAME or name.startswith(MODULE_NAME + "."):
            del sys.modules[name]


def load_plugin():
    try:
        cmds.loadPlugin(PLUGIN_PATH)
    except Exception:
        cmds.loadPlugin(PLUGIN_NAME)


def reload_dropnote():
    ensure_project_root()
    cleanup_old_runtime()
    unload_plugin()
    clear_modules()
    load_plugin()
    print("Hypershade DropNote reload complete.")


reload_dropnote()
