# 概述

这是 **HyperShade Notes 的开发分支**。

HyperShade Notes 是一个受 Nuke Backdrop 启发的 Maya Hypershade / Node Editor 视觉整理工具。  
它提供 DropNote 和 Sticky Note，用于整理复杂的材质节点网络。

dev 分支可能包含实验脚本、测试场景和开发专用工具。

# 拉取 dev 分支

直接克隆 dev 分支：

bash

`git clone -b dev https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git`

如果你已经克隆过仓库：

bash

`git fetch origin git checkout dev git pull origin dev`

请把：

添加到对话

YOUR_USERNAME/YOUR_REPOSITORY_NAME

替换成你的实际 GitHub 仓库路径。


# 文件说明

## hypershade_dropnote.py

插件主运行文件。

这里包含核心逻辑：

-   DropNote 的绘制与交互
-   Sticky Note 的绘制与交互
-   将 Note 数据保存到 Maya 场景文件
-   从 Maya 场景文件恢复 Note
-   Shift+B、Shift+N、Shift+S 等快捷键
-   Qt 事件过滤器
-   开发热重载时的运行时清理逻辑

大部分功能开发都在这个文件中完成。


## plug-ins/HypershadeDropNote.py

Maya 插件管理器入口文件。

这个文件让 Maya 可以通过插件管理器加载 HyperShade Notes：

添加到对话

Windows > Settings/Preferences > Plug-in Manager

它会注册 Maya 命令：

python

`cmds.hypershadeDropNote()`

插件加载时也会安装快捷键事件监听。

## scripts/add_plugin_path.py

开发辅助脚本。

这个脚本会把本地插件目录加入 Maya 插件路径，并写入 Maya module 文件。

如果 Maya 无法自动找到插件，可以在本地开发时使用它。

## scripts/reload_dropnote.py

开发热重载脚本。

开发时使用它，可以避免每次改代码后都重启 Maya。

在 Maya Script Editor 中运行：

python

`exec(open(r"PATH_TO_REPOSITORY\scripts\reload_dropnote.py").read())`

它会执行：

-   清理已有 DropNote / Sticky Note 运行时对象
-   移除旧快捷键监听
-   卸载插件
-   清理 Python 模块缓存
-   重新加载插件


# 在 Maya 中安装

普通测试方式：

1.  打开 Maya。
2.  打开 Windows > Settings/Preferences > Plug-in Manager。
3.  点击 Browse。
4.  选择：

添加到对话

plug-ins/HypershadeDropNote.py

5.  勾选 Loaded。
6.  如果需要自动加载，可以勾选 Auto load。

# 开发流程

推荐开发流程：

1.  打开 Maya。
2.  加载 plug-ins/HypershadeDropNote.py。
3.  修改 hypershade_dropnote.py。
4.  运行：

python

`exec(open(r"PATH_TO_REPOSITORY\scripts\reload_dropnote.py").read())`

5.  在 Hypershade / Node Editor 中测试。
6.  重复修改和测试。

# 快捷键

添加到对话

Shift+B = 显示 / 隐藏已保存的 DropNote 和 Sticky Note Shift+N = 创建 DropNote Shift+S = 创建 Sticky Note Delete = 删除选中的 Note

# 注意事项

这个插件只是在 Hypershade 中添加一层视觉整理辅助。  
它不会修改 Maya 内部材质节点，也不会接管 Maya 原生节点图逻辑。

当前面板数据按 Hypershade 标签页名称关联。  
请使用唯一的标签页名称，避免多个同名标签页共用同一套 Note 数据。  
```
