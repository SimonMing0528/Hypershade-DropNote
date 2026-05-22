# Hypershade DropNote runtime.
from __future__ import print_function

import json

import maya.cmds as cmds

try:
    from PySide2 import QtWidgets, QtGui, QtCore
    import shiboken2 as shiboken
except Exception:
    from PySide6 import QtWidgets, QtGui, QtCore
    import shiboken6 as shiboken


PLUGIN_NAME = "Hypershade DropNote"
STORAGE_NODE = "HSDropNote_Data"
STORAGE_ATTR = "data"

DEFAULT_TITLE = "Shader Group"
DEFAULT_COLOR = (255, 170, 35, 72)
HANDLE_SIZE = 22
MOVE_HANDLE_WIDTH = 150
MOVE_HANDLE_HEIGHT = 22
MIN_WIDTH = 160
MIN_HEIGHT = 110

BACKDROP_ITEMS = []
EVENT_FILTER = None


def qt_is_alive(obj):
    try:
        return obj is not None and shiboken.isValid(obj)
    except Exception:
        return obj is not None


def get_scene(view):
    try:
        if qt_is_alive(view):
            return view.scene()
    except Exception:
        pass
    return None


def all_graphics_views():
    app = QtWidgets.QApplication.instance()
    if not app:
        return []

    views = []
    seen = set()

    for widget in app.allWidgets():
        try:
            if not qt_is_alive(widget):
                continue
            if not isinstance(widget, QtWidgets.QGraphicsView):
                continue

            try:
                ptr = int(shiboken.getCppPointer(widget)[0])
            except Exception:
                ptr = id(widget)

            if ptr not in seen:
                seen.add(ptr)
                views.append(widget)
        except Exception:
            continue

    return views


def selected_node_items(scene):
    try:
        raw_selected = scene.selectedItems()
    except Exception:
        raw_selected = []

    selected = []

    for item in raw_selected:
        if getattr(item, "_dropnote_item", False):
            continue

        try:
            rect = item.sceneBoundingRect()
        except Exception:
            continue

        if rect.width() >= 20 and rect.height() >= 20:
            selected.append(item)

    return selected


def view_has_selected_nodes(view):
    scene = get_scene(view)
    return bool(scene and selected_node_items(scene))


def score_view(view):
    score = 0

    try:
        if view.isVisible():
            score += 10
    except Exception:
        pass

    try:
        if view.hasFocus():
            score += 30
    except Exception:
        pass

    try:
        if view.underMouse():
            score += 20
    except Exception:
        pass

    if get_scene(view):
        score += 10

    if view_has_selected_nodes(view):
        score += 1000

    try:
        name = view.objectName().lower()
        if "node" in name or "hyper" in name:
            score += 15
    except Exception:
        pass

    return score


def find_best_graphics_view():
    scored = []

    for view in all_graphics_views():
        if get_scene(view):
            scored.append((score_view(view), view))

    if not scored:
        return None

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return scored[0][1]


def graphics_view_from_widget(widget):
    while widget is not None:
        try:
            if isinstance(widget, QtWidgets.QGraphicsView):
                return widget
            widget = widget.parent()
        except Exception:
            return None

    return None


def focused_graphics_view():
    app = QtWidgets.QApplication.instance()
    if not app:
        return None

    view = graphics_view_from_widget(app.focusWidget())
    if view and get_scene(view):
        return view

    return None


def is_dropnote_view(view):
    if not view or not get_scene(view):
        return False

    if view_has_selected_nodes(view):
        return True

    try:
        name = view.objectName().lower()
        if "node" in name or "hyper" in name:
            return True
    except Exception:
        pass

    try:
        return view.isVisible() and view.underMouse()
    except Exception:
        return False


def ensure_storage_node():
    if not cmds.objExists(STORAGE_NODE):
        node = cmds.createNode("network", name=STORAGE_NODE)
        cmds.setAttr(node + ".hiddenInOutliner", True)
    else:
        node = STORAGE_NODE

    if not cmds.attributeQuery(STORAGE_ATTR, node=node, exists=True):
        cmds.addAttr(node, longName=STORAGE_ATTR, dataType="string")

    return node


def load_data():
    if not cmds.objExists(STORAGE_NODE):
        return []
    if not cmds.attributeQuery(STORAGE_ATTR, node=STORAGE_NODE, exists=True):
        return []

    try:
        raw = cmds.getAttr(STORAGE_NODE + "." + STORAGE_ATTR)
    except Exception:
        raw = ""

    if not raw:
        return []

    try:
        data = json.loads(raw)
    except Exception:
        data = []

    return data if isinstance(data, list) else []


def save_data():
    node = ensure_storage_node()
    data = []

    for item in list(BACKDROP_ITEMS):
        if item.scene() is None:
            continue

        rect = item.rect()
        pos = item.pos()
        color = item.base_color

        data.append({
            "title": item.label.toPlainText(),
            "x": pos.x(),
            "y": pos.y(),
            "rect_x": rect.x(),
            "rect_y": rect.y(),
            "w": rect.width(),
            "h": rect.height(),
            "color": [color.red(), color.green(), color.blue(), color.alpha()],
        })

    cmds.setAttr(node + "." + STORAGE_ATTR, json.dumps(data), type="string")
    print("%s: saved %d DropNote(s)." % (PLUGIN_NAME, len(data)))


def color_from_data(entry):
    values = entry.get("color", DEFAULT_COLOR)
    try:
        return QtGui.QColor(values[0], values[1], values[2], values[3])
    except Exception:
        return QtGui.QColor(*DEFAULT_COLOR)


class DropNoteItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, rect, title=DEFAULT_TITLE, color=None):
        super(DropNoteItem, self).__init__(rect)

        self._dropnote_item = True
        self.base_color = color or QtGui.QColor(*DEFAULT_COLOR)
        self.resizing = False
        self.resize_corner = None
        self.moving_from_handle = False
        self.resize_start_pos = None
        self.resize_start_rect = None
        self.move_start_pos = None
        self.move_start_item_pos = None

        self.setZValue(-100000)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton | QtCore.Qt.RightButton)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)

        self.label = QtWidgets.QGraphicsTextItem(title, self)
        self.label.setDefaultTextColor(QtGui.QColor(255, 255, 255))

        font = QtGui.QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.label.setFont(font)

        self.apply_style()
        self.update_label()

    def apply_style(self):
        fill = QtGui.QColor(self.base_color)
        border = QtGui.QColor(self.base_color)
        border.setAlpha(235)

        self.setBrush(QtGui.QBrush(fill))

        pen = QtGui.QPen(border)
        pen.setWidth(4)
        self.setPen(pen)

    def update_label(self):
        rect = self.rect()
        self.label.setPos(rect.left() + 18, rect.top() + 12)

    def handle_rect(self):
        return self.resize_handle_rect("bottom_right")

    def resize_handle_rect(self, corner):
        rect = self.rect()

        if corner == "bottom_left":
            return QtCore.QRectF(
                rect.left(),
                rect.bottom() - HANDLE_SIZE,
                HANDLE_SIZE,
                HANDLE_SIZE
            )

        if corner == "top_right":
            return QtCore.QRectF(
                rect.right() - HANDLE_SIZE,
                rect.top(),
                HANDLE_SIZE,
                HANDLE_SIZE
            )

        return QtCore.QRectF(
            rect.right() - HANDLE_SIZE,
            rect.bottom() - HANDLE_SIZE,
            HANDLE_SIZE,
            HANDLE_SIZE
        )

    def move_handle_rect(self):
        rect = self.rect()
        width = min(MOVE_HANDLE_WIDTH, max(60, rect.width() * 0.42))
        return QtCore.QRectF(
            rect.center().x() - width * 0.5,
            rect.top() + 4,
            width,
            MOVE_HANDLE_HEIGHT
        )

    def edit_properties(self):
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Edit DropNote")

        name_edit = QtWidgets.QLineEdit(self.label.toPlainText())
        color_button = QtWidgets.QPushButton("Choose Color")
        preview = QtWidgets.QFrame()
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        chosen_color = QtGui.QColor(self.base_color)

        def update_preview():
            preview.setFixedSize(42, 22)
            preview.setStyleSheet(
                "background-color: rgba(%d, %d, %d, %d); border: 1px solid rgba(255, 255, 255, 160);"
                % (
                    chosen_color.red(),
                    chosen_color.green(),
                    chosen_color.blue(),
                    chosen_color.alpha()
                )
            )

        def choose_color():
            new_color = QtWidgets.QColorDialog.getColor(chosen_color, dialog)
            if new_color.isValid():
                new_color.setAlpha(chosen_color.alpha())
                chosen_color.setRgb(
                    new_color.red(),
                    new_color.green(),
                    new_color.blue(),
                    new_color.alpha()
                )
                update_preview()

        form = QtWidgets.QFormLayout()
        color_row = QtWidgets.QHBoxLayout()
        color_row.addWidget(preview)
        color_row.addWidget(color_button)
        color_row.addStretch()

        form.addRow("Name", name_edit)
        form.addRow("Color", color_row)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addLayout(form)
        layout.addWidget(buttons)

        color_button.clicked.connect(choose_color)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        update_preview()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            text = name_edit.text().strip()
            if text:
                self.label.setPlainText(text)

            self.base_color = chosen_color
            self.apply_style()
            save_data()

    def rename(self):
        text, ok = QtWidgets.QInputDialog.getText(
            None,
            "Rename DropNote",
            "DropNote name:",
            text=self.label.toPlainText()
        )

        if ok and text:
            self.label.setPlainText(text)
            save_data()

    def change_color(self):
        color = QtWidgets.QColorDialog.getColor(self.base_color)

        if color.isValid():
            color.setAlpha(self.base_color.alpha())
            self.base_color = color
            self.apply_style()
            save_data()

    def delete(self):
        scene = self.scene()
        if scene:
            scene.removeItem(self)

        if self in BACKDROP_ITEMS:
            BACKDROP_ITEMS.remove(self)

        save_data()

    def show_menu(self, screen_pos):
        menu = QtWidgets.QMenu()
        rename_action = menu.addAction("Rename")
        color_action = menu.addAction("Change Color")
        save_action = menu.addAction("Save")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")

        action = menu.exec_(screen_pos)

        if action == rename_action:
            self.rename()
        elif action == color_action:
            self.change_color()
        elif action == save_action:
            save_data()
        elif action == delete_action:
            self.delete()

    def draw_resize_handle(self, painter, corner):
        handle = self.resize_handle_rect(corner)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 210), 1))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 90)))
        painter.drawRect(handle)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 210), 2))

        if corner == "bottom_left":
            painter.drawLine(
                QtCore.QPointF(handle.right() - 6, handle.bottom() - 6),
                QtCore.QPointF(handle.left() + 6, handle.top() + 6)
            )
            painter.drawLine(
                QtCore.QPointF(handle.right() - 13, handle.bottom() - 6),
                QtCore.QPointF(handle.left() + 6, handle.top() + 13)
            )
            return

        if corner == "top_right":
            painter.drawLine(
                QtCore.QPointF(handle.left() + 6, handle.top() + 6),
                QtCore.QPointF(handle.right() - 6, handle.bottom() - 6)
            )
            painter.drawLine(
                QtCore.QPointF(handle.left() + 13, handle.top() + 6),
                QtCore.QPointF(handle.right() - 6, handle.bottom() - 13)
            )
            return

        painter.drawLine(
            QtCore.QPointF(handle.left() + 6, handle.bottom() - 6),
            QtCore.QPointF(handle.right() - 6, handle.top() + 6)
        )
        painter.drawLine(
            QtCore.QPointF(handle.left() + 13, handle.bottom() - 6),
            QtCore.QPointF(handle.right() - 6, handle.top() + 13)
        )

    def resize_corner_at(self, pos):
        for corner in ("bottom_right", "bottom_left", "top_right"):
            if self.resize_handle_rect(corner).contains(pos):
                return corner

        return None

    def paint(self, painter, option, widget=None):
        super(DropNoteItem, self).paint(painter, option, widget)

        move_handle = self.move_handle_rect()

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 170), 1))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 42)))
        painter.drawRoundedRect(move_handle, 3, 3)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 135), 1))
        y = move_handle.center().y()
        painter.drawLine(
            QtCore.QPointF(move_handle.left() + 14, y - 3),
            QtCore.QPointF(move_handle.right() - 14, y - 3)
        )
        painter.drawLine(
            QtCore.QPointF(move_handle.left() + 14, y + 3),
            QtCore.QPointF(move_handle.right() - 14, y + 3)
        )

        self.draw_resize_handle(painter, "bottom_left")
        self.draw_resize_handle(painter, "top_right")
        self.draw_resize_handle(painter, "bottom_right")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.show_menu(event.screenPos())
            event.accept()
            return

        if event.button() == QtCore.Qt.LeftButton and self.move_handle_rect().contains(event.pos()):
            self.moving_from_handle = True
            self.move_start_pos = event.scenePos()
            self.move_start_item_pos = QtCore.QPointF(self.pos())
            self.setSelected(True)
            event.accept()
            return

        resize_corner = self.resize_corner_at(event.pos())
        if event.button() == QtCore.Qt.LeftButton and resize_corner:
            self.resizing = True
            self.resize_corner = resize_corner
            self.resize_start_pos = event.scenePos()
            self.resize_start_rect = QtCore.QRectF(self.rect())
            event.accept()
            return

        super(DropNoteItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.moving_from_handle:
            delta = event.scenePos() - self.move_start_pos
            self.setPos(self.move_start_item_pos + delta)
            event.accept()
            return

        if self.resizing:
            delta = event.scenePos() - self.resize_start_pos
            rect = QtCore.QRectF(self.resize_start_rect)

            if self.resize_corner == "bottom_right":
                rect.setWidth(max(MIN_WIDTH, rect.width() + delta.x()))
                rect.setHeight(max(MIN_HEIGHT, rect.height() + delta.y()))

            elif self.resize_corner == "bottom_left":
                new_left = min(rect.left() + delta.x(), rect.right() - MIN_WIDTH)
                rect.setLeft(new_left)
                rect.setHeight(max(MIN_HEIGHT, rect.height() + delta.y()))

            elif self.resize_corner == "top_right":
                new_top = min(rect.top() + delta.y(), rect.bottom() - MIN_HEIGHT)
                rect.setTop(new_top)
                rect.setWidth(max(MIN_WIDTH, rect.width() + delta.x()))

            self.prepareGeometryChange()
            self.setRect(rect)
            self.update_label()
            self.update()
            event.accept()
            return

        super(DropNoteItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.moving_from_handle:
            self.moving_from_handle = False
            self.move_start_pos = None
            self.move_start_item_pos = None
            save_data()
            event.accept()
            return

        if self.resizing:
            self.resizing = False
            self.resize_corner = None
            self.resize_start_pos = None
            self.resize_start_rect = None
            save_data()
            event.accept()
            return

        super(DropNoteItem, self).mouseReleaseEvent(event)
        save_data()

    def mouseDoubleClickEvent(self, event):
        self.edit_properties()
        event.accept()

    def contextMenuEvent(self, event):
        self.show_menu(event.screenPos())
        event.accept()


def create_backdrop_from_selection(scene):
    selected = selected_node_items(scene)
    if not selected:
        return None

    bounds = selected[0].sceneBoundingRect()
    for item in selected[1:]:
        try:
            bounds = bounds.united(item.sceneBoundingRect())
        except Exception:
            pass

    rect = QtCore.QRectF(
        bounds.left() - 80,
        bounds.top() - 95,
        bounds.width() + 160,
        bounds.height() + 165
    )

    backdrop = DropNoteItem(rect)
    scene.addItem(backdrop)
    BACKDROP_ITEMS.append(backdrop)

    for item in selected:
        try:
            item.setSelected(False)
        except Exception:
            pass

    backdrop.setSelected(True)
    save_data()
    return backdrop


def restore_backdrops(scene):
    restored = 0

    for old in list(BACKDROP_ITEMS):
        try:
            if old.scene():
                old.scene().removeItem(old)
        except Exception:
            pass

    BACKDROP_ITEMS[:] = []

    for entry in load_data():
        try:
            rect = QtCore.QRectF(
                float(entry.get("rect_x", 0)),
                float(entry.get("rect_y", 0)),
                float(entry.get("w", 400)),
                float(entry.get("h", 250))
            )

            backdrop = DropNoteItem(
                rect,
                title=entry.get("title", DEFAULT_TITLE),
                color=color_from_data(entry)
            )
            backdrop.setPos(
                QtCore.QPointF(
                    float(entry.get("x", 0)),
                    float(entry.get("y", 0))
                )
            )

            scene.addItem(backdrop)
            BACKDROP_ITEMS.append(backdrop)
            restored += 1
        except Exception as error:
            print("%s: failed to restore one DropNote: %s" % (PLUGIN_NAME, error))

    if restored:
        print("%s: restored %d DropNote(s)." % (PLUGIN_NAME, restored))


def delete_selected_dropnotes(scene):
    deleted = 0

    try:
        selected = scene.selectedItems()
    except Exception:
        selected = []

    for item in list(selected):
        if getattr(item, "_dropnote_item", False):
            item.delete()
            deleted += 1

    return deleted


def run():
    view = find_best_graphics_view()

    if view is None:
        QtWidgets.QMessageBox.warning(
            None,
            PLUGIN_NAME,
            "Could not find a Hypershade / Node Editor graph.\n\nOpen Hypershade or Node Editor, click the graph area, then run DropNote again."
        )
        return

    scene = get_scene(view)

    if scene is None:
        QtWidgets.QMessageBox.warning(
            None,
            PLUGIN_NAME,
            "Found the graph view, but could not access the scene.\n\nClick the graph area, then run DropNote again."
        )
        return

    restore_backdrops(scene)

    if create_backdrop_from_selection(scene):
        print("%s: created from selection." % PLUGIN_NAME)
    else:
        print("%s: restored saved DropNotes. Select graph nodes and run again to create a new one." % PLUGIN_NAME)


class DropNoteEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() != QtCore.QEvent.KeyPress:
            return False

        view = focused_graphics_view()
        if not is_dropnote_view(view):
            return False

        key = event.key()
        modifiers = event.modifiers()
        scene = get_scene(view)

        if key == QtCore.Qt.Key_B and modifiers == QtCore.Qt.ShiftModifier:
            run()
            event.accept()
            return True

        if key in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            if scene and delete_selected_dropnotes(scene):
                event.accept()
                return True

        return False


def install_event_filter():
    global EVENT_FILTER

    app = QtWidgets.QApplication.instance()
    if not app:
        return

    if EVENT_FILTER is None or not qt_is_alive(EVENT_FILTER):
        EVENT_FILTER = DropNoteEventFilter()
        app.installEventFilter(EVENT_FILTER)
        print("%s: Shift+B hotkey installed." % PLUGIN_NAME)


def uninstall_event_filter():
    global EVENT_FILTER

    app = QtWidgets.QApplication.instance()
    if app and EVENT_FILTER is not None and qt_is_alive(EVENT_FILTER):
        app.removeEventFilter(EVENT_FILTER)
        print("%s: hotkey removed." % PLUGIN_NAME)

    EVENT_FILTER = None
