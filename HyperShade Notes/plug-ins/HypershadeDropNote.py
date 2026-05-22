# Maya Plug-in Manager entry point.
from __future__ import absolute_import

import sys

import maya.api.OpenMaya as om


PLUGIN_NAME = "HypershadeDropNote"
COMMAND_NAME = "hypershadeDropNote"
PLUGIN_ROOT = r"F:\R_D\HyperShade Notes\Developement Files\HyperShade Notes"


def maya_useNewAPI():
    pass


def ensure_plugin_root_on_path():
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
    ensure_plugin_root_on_path()

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
    ensure_plugin_root_on_path()

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
