# Adds Hypershade DropNote to Maya's plug-in and module paths.
from __future__ import absolute_import

import os

import maya.cmds as cmds


PROJECT_ROOT = r"F:\R_D\HyperShade Notes\Developement Files\HyperShade Notes"
PLUGIN_DIR = r"F:\R_D\HyperShade Notes\Developement Files\HyperShade Notes\plug-ins"
MODULE_NAME = "HypershadeDropNote.mod"


def module_file_text():
    root = PROJECT_ROOT.replace("\\", "/")
    return "\n".join([
        "+ HypershadeDropNote 0.1 %s" % root,
        "MAYA_PLUG_IN_PATH +:= plug-ins",
        "PYTHONPATH +:= .",
        ""
    ])


def install_module_file():
    user_app_dir = cmds.internalVar(userAppDir=True)
    modules_dir = os.path.join(user_app_dir, "modules")

    if not os.path.isdir(modules_dir):
        os.makedirs(modules_dir)

    module_path = os.path.join(modules_dir, MODULE_NAME)

    with open(module_path, "w") as stream:
        stream.write(module_file_text())

    return module_path


def add_plugin_path():
    current_path = os.environ.get("MAYA_PLUG_IN_PATH", "")
    paths = [path for path in current_path.split(os.pathsep) if path]

    if PLUGIN_DIR not in paths:
        paths.insert(0, PLUGIN_DIR)
        os.environ["MAYA_PLUG_IN_PATH"] = os.pathsep.join(paths)

    module_path = install_module_file()

    cmds.confirmDialog(
        title="Hypershade DropNote",
        message="DropNote module installed.\n\nRestart Maya, open Plug-in Manager, and load HypershadeDropNote.py.\n\nModule file:\n%s" % module_path,
        button=["OK"]
    )


add_plugin_path()
