# Maya Plug-in Manager entry point.
from __future__ import absolute_import

import sys
import os
import inspect

import maya.api.OpenMaya as om


PLUGIN_NAME = "HypershadeDropNote"
COMMAND_NAME = "hypershadeDropNote"
PLUGIN_ROOT = None


def maya_useNewAPI():
    pass


def project_root_from_plugin_path(plugin_path):
    if not plugin_path:
        return None

    plugin_path = os.path.abspath(plugin_path)

    if os.path.isfile(plugin_path):
        plugin_dir = os.path.dirname(plugin_path)
    else:
        plugin_dir = plugin_path

    if os.path.basename(plugin_dir).lower() == "plug-ins":
        return os.path.abspath(os.path.join(plugin_dir, os.pardir))

    return plugin_dir


def plugin_path_from_frame():
    try:
        return inspect.currentframe().f_code.co_filename
    except Exception:
        return None


def plugin_path_from_maya_plugin(plugin):
    try:
        return om.MFnPlugin(plugin).loadPath()
    except Exception:
        return None


def resolve_plugin_root(plugin=None):
    global PLUGIN_ROOT

    if PLUGIN_ROOT:
        return PLUGIN_ROOT

    paths = [
        plugin_path_from_maya_plugin(plugin),
        globals().get("__file__"),
        plugin_path_from_frame(),
    ]

    for path in paths:
        root = project_root_from_plugin_path(path)
        if root and os.path.exists(os.path.join(root, "hypershade_dropnote.py")):
            PLUGIN_ROOT = root
            return PLUGIN_ROOT

    return None


def ensure_plugin_root_on_path(plugin=None):
    plugin_root = resolve_plugin_root(plugin)

    if not plugin_root:
        raise RuntimeError("Could not find hypershade_dropnote.py next to the plug-ins folder.")

    if PLUGIN_ROOT not in sys.path:
        sys.path.insert(0, PLUGIN_ROOT)


class HypershadeDropNoteCommand(om.MPxCommand):
    def doIt(self, args):
        ensure_plugin_root_on_path()

        import hypershade_dropnote

        hypershade_dropnote.run()


def create_command():
    return HypershadeDropNoteCommand()


def initializePlugin(plugin):
    ensure_plugin_root_on_path(plugin)

    import hypershade_dropnote

    plugin_fn = om.MFnPlugin(
        plugin,
        "Hypershade DropNote",
        "0.1.0",
        "Any"
    )

    try:
        plugin_fn.registerCommand(COMMAND_NAME, create_command)
    except Exception:
        om.MGlobal.displayError("Failed to register %s command." % COMMAND_NAME)
        raise

    hypershade_dropnote.install_event_filter()
    om.MGlobal.displayInfo("%s loaded. Command: %s" % (PLUGIN_NAME, COMMAND_NAME))


def uninitializePlugin(plugin):
    ensure_plugin_root_on_path(plugin)

    try:
        import hypershade_dropnote
        hypershade_dropnote.uninstall_event_filter()
    except Exception:
        pass

    plugin_fn = om.MFnPlugin(plugin)

    try:
        plugin_fn.deregisterCommand(COMMAND_NAME)
    except Exception:
        om.MGlobal.displayError("Failed to deregister %s command." % COMMAND_NAME)
        raise

    om.MGlobal.displayInfo("%s unloaded." % PLUGIN_NAME)
