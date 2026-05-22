# Hypershade DropNote

[English](#hypershade-dropnote) | [中文](#hypershade-dropnote-中文说明)

Hypershade DropNote creates simple Nuke-style colored backdrops in Maya Hypershade / Node Editor.

It is meant for artists who want to visually group shader nodes and keep material graphs readable.

<img width="2057" height="1516" alt="hypershade_dropnote_LOGO" src="https://github.com/user-attachments/assets/cd9d55d1-f5cf-405a-a42c-a18918a8d6c7" />

## Install For Plug-in Manager

1. Download or clone this repository.
2. In Maya, open `Windows > Settings/Preferences > Plug-in Manager`.
3. Click `Browse`.
4. Select this file from the downloaded folder:

```text
plug-ins/HypershadeDropNote.py
```

5. Enable `Loaded`.
6. Enable `Auto load` if you want Maya to load it automatically next time.

## Usage

1. Open Hypershade or Node Editor.
2. Select graph nodes.
3. Press `Shift+B` to show or hide saved DropNotes and Sticky Notes.
4. Press `Shift+N` to create a DropNote.
5. Press `Shift+S` to create a Sticky Note.
6. If shader nodes are selected, the new DropNote wraps them.
7. If no shader nodes are selected, the new DropNote/Sticky Note appears at the view center.
8. Double-click a DropNote or Sticky Note to edit it.
9. Drag the top handle to move it.
10. Drag a corner handle to resize it.
11. Select the item and press `Delete` to remove it.

## Command

You can also run the command manually:

```python
import maya.cmds as cmds
cmds.hypershadeDropNote()
```

## Development Reload

During development, run `scripts/reload_dropnote.py` in Maya Script Editor after editing code.

```python
exec(open(r"PATH_TO_REPOSITORY\scripts\reload_dropnote.py").read())
```

---


# Hypershade DropNote 中文说明

Hypershade DropNote 为 Maya Hypershade / Node Editor 添加 Nuke 风格的backdrop和sticky note。

它适合艺术家用来对材质节点进行视觉分组，让复杂的材质网络更清晰。


## 通过插件管理器安装

1. 下载或克隆这个仓库。
2. 在 Maya 中打开 `Windows > Settings/Preferences > Plug-in Manager`。
3. 点击 `Browse`。
4. 在下载的文件夹中选择：

```text
plug-ins/HypershadeDropNote.py
```

5. 勾选 `Loaded`。
6. 如果希望 Maya 下次自动加载，可以勾选 `Auto load`。

## 使用方式

1. 打开 Hypershade。
2. 选择节点。
3. 按 `Shift+B` 显示或隐藏已保存的 DropNote 和 Sticky Note。
4. 按 `Shift+N` 创建 DropNote。
5. 按 `Shift+S` 创建 Sticky Note。
6. 如果当前选中了材质节点，新建的 DropNote 会包住这些节点。
7. 如果没有选中节点，新建的 DropNote / Sticky Note会出现在当前视图中心。
8. 双击 DropNote 或 Sticky Note 可以编辑。
9. 拖动 DropNote 顶部手柄可以移动；Sticky Note 可直接拖动移动。
10. 拖动角落手柄可以缩放。
11. 选中项目后按 `Delete` 可以删除。

## 命令

也可以手动运行命令：

```python
import maya.cmds as cmds
cmds.hypershadeDropNote()
```

## 开发热重载

开发调试时，修改代码后可以在 Maya Script Editor 中运行 `scripts/reload_dropnote.py`，无需反复重启 Maya 实现实时热重载调试。

```python
exec(open(r"PATH_TO_REPOSITORY\scripts\reload_dropnote.py").read())

