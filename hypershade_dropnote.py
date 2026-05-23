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
DEFAULT_FONT_SIZE = 18
DEFAULT_FONT_FAMILY = ""
DEFAULT_STICKY_BODY = "Add note..."
DEFAULT_STICKY_COLOR = (24, 24, 24, 255)
DEFAULT_STICKY_TEXT_COLOR = (245, 245, 235, 255)
DEFAULT_STICKY_FONT_SIZE = 8
HANDLE_SIZE = 16
MOVE_HANDLE_WIDTH = 76
MOVE_HANDLE_HEIGHT = 10
MIN_WIDTH = 160
MIN_HEIGHT = 110
DEFAULT_BACKDROP_WIDTH = 420
DEFAULT_BACKDROP_HEIGHT = 260
DEFAULT_STICKY_WIDTH = 260
DEFAULT_STICKY_HEIGHT = 150
STICKY_CORNER_CUT = 18

BACKDROP_ITEMS = []
EVENT_FILTER = None
HOTKEYS_DOWN = set()
APP_FILTER_ATTR = "_hypershade_dropnote_event_filter"
ITEMS_VISIBLE = False
CURRENT_PANEL_KEY = "__default__"


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


def panel_key_from_view(view):
    widget = view

    while widget is not None:
        try:
            if isinstance(widget, QtWidgets.QTabWidget):
                index = widget.currentIndex()
                title = widget.tabText(index).strip()
                if title:
                    return "tab:" + title
        except Exception:
            pass

        try:
            widget = widget.parent()
        except Exception:
            widget = None

    scene = get_scene(view)
    if scene is not None:
        try:
            return "scene:%s" % int(shiboken.getCppPointer(scene)[0])
        except Exception:
            return "scene:%s" % id(scene)

    return "__default__"


def set_current_panel_key_from_view(view):
    global CURRENT_PANEL_KEY

    CURRENT_PANEL_KEY = panel_key_from_view(view)
    return CURRENT_PANEL_KEY


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
    old_data = load_data()
    data = [
        entry for entry in old_data
        if entry.get("panel_key", CURRENT_PANEL_KEY) != CURRENT_PANEL_KEY
    ]
    saved_count = 0

    for item in list(BACKDROP_ITEMS):
        if item.scene() is None:
            continue

        if hasattr(item, "to_data"):
            try:
                entry = item.to_data()
                entry["panel_key"] = CURRENT_PANEL_KEY
                data.append(entry)
                saved_count += 1
            except Exception as error:
                print("%s: failed to save one item: %s" % (PLUGIN_NAME, error))
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
            "font_size": item.font_size,
            "font_family": item.font_family,
            "fill_transparent": item.fill_transparent,
            "panel_key": CURRENT_PANEL_KEY,
        })
        saved_count += 1

    cmds.setAttr(node + "." + STORAGE_ATTR, json.dumps(data), type="string")
    print("%s: saved %d item(s) for %s." % (PLUGIN_NAME, saved_count, CURRENT_PANEL_KEY))


def color_from_data(entry):
    values = entry.get("color", DEFAULT_COLOR)
    try:
        return QtGui.QColor(values[0], values[1], values[2], values[3])
    except Exception:
        return QtGui.QColor(*DEFAULT_COLOR)


def text_color_from_data(entry):
    values = entry.get("text_color", DEFAULT_STICKY_TEXT_COLOR)
    try:
        return QtGui.QColor(values[0], values[1], values[2], values[3])
    except Exception:
        return QtGui.QColor(*DEFAULT_STICKY_TEXT_COLOR)


class DropNoteItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, rect, title=DEFAULT_TITLE, color=None):
        super(DropNoteItem, self).__init__(rect)

        self._dropnote_item = True
        self.base_color = color or QtGui.QColor(*DEFAULT_COLOR)
        self.fill_transparent = False
        self.font_size = DEFAULT_FONT_SIZE
        self.font_family = DEFAULT_FONT_FAMILY
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
        font.setBold(True)
        font.setPointSize(self.font_size)
        if self.font_family:
            font.setFamily(self.font_family)
        self.label.setFont(font)

        self.apply_style()
        self.update_label()

    def apply_style(self):
        fill = QtGui.QColor(self.base_color)
        border = QtGui.QColor(self.base_color)
        border.setAlpha(235)

        if self.fill_transparent:
            fill.setAlpha(0)

        self.setBrush(QtGui.QBrush(fill))

        pen = QtGui.QPen(border)
        pen.setWidth(4)
        self.setPen(pen)

    def update_label(self):
        rect = self.rect()
        self.label.setPos(rect.left() + 18, rect.top() + 12)

    def apply_font_size(self):
        font = self.label.font()
        font.setPointSize(self.font_size)
        if self.font_family:
            font.setFamily(self.font_family)
        self.label.setFont(font)

    def to_data(self):
        rect = self.rect()
        pos = self.pos()
        color = self.base_color

        return {
            "kind": "backdrop",
            "title": self.label.toPlainText(),
            "x": pos.x(),
            "y": pos.y(),
            "rect_x": rect.x(),
            "rect_y": rect.y(),
            "w": rect.width(),
            "h": rect.height(),
            "color": [color.red(), color.green(), color.blue(), color.alpha()],
            "font_size": self.font_size,
            "font_family": self.font_family,
            "fill_transparent": self.fill_transparent,
        }

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
        font_combo = QtWidgets.QFontComboBox()
        if self.font_family:
            font_combo.setCurrentFont(QtGui.QFont(self.font_family))
        font_size_spin = QtWidgets.QSpinBox()
        font_size_spin.setRange(8, 48)
        font_size_spin.setValue(self.font_size)
        color_button = QtWidgets.QPushButton("Choose Color")
        transparent_check = QtWidgets.QCheckBox("Transparent fill")
        transparent_check.setChecked(self.fill_transparent)
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
        form.addRow("Font", font_combo)
        form.addRow("Name Size", font_size_spin)
        form.addRow("Color", color_row)
        form.addRow("", transparent_check)

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

            self.font_size = font_size_spin.value()
            self.font_family = font_combo.currentFont().family()
            self.fill_transparent = transparent_check.isChecked()
            self.base_color = chosen_color
            self.apply_font_size()
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
        inset = 4
        second_inset = 8

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 115), 1))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 32)))
        painter.drawRect(handle)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 120), 1))

        if corner == "bottom_left":
            painter.drawLine(
                QtCore.QPointF(handle.right() - inset, handle.bottom() - inset),
                QtCore.QPointF(handle.left() + inset, handle.top() + inset)
            )
            painter.drawLine(
                QtCore.QPointF(handle.right() - second_inset, handle.bottom() - inset),
                QtCore.QPointF(handle.left() + inset, handle.top() + second_inset)
            )
            return

        if corner == "top_right":
            painter.drawLine(
                QtCore.QPointF(handle.left() + inset, handle.top() + inset),
                QtCore.QPointF(handle.right() - inset, handle.bottom() - inset)
            )
            painter.drawLine(
                QtCore.QPointF(handle.left() + second_inset, handle.top() + inset),
                QtCore.QPointF(handle.right() - inset, handle.bottom() - second_inset)
            )
            return

        painter.drawLine(
            QtCore.QPointF(handle.left() + inset, handle.bottom() - inset),
            QtCore.QPointF(handle.right() - inset, handle.top() + inset)
        )
        painter.drawLine(
            QtCore.QPointF(handle.left() + second_inset, handle.bottom() - inset),
            QtCore.QPointF(handle.right() - inset, handle.top() + second_inset)
        )

    def resize_corner_at(self, pos):
        for corner in ("bottom_right", "bottom_left", "top_right"):
            if self.resize_handle_rect(corner).contains(pos):
                return corner

        return None

    def paint(self, painter, option, widget=None):
        super(DropNoteItem, self).paint(painter, option, widget)

        move_handle = self.move_handle_rect()

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 95), 1))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 20)))
        painter.drawRoundedRect(move_handle, 2, 2)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 85), 1))
        y = move_handle.center().y()
        painter.drawLine(
            QtCore.QPointF(move_handle.left() + 9, y - 2),
            QtCore.QPointF(move_handle.right() - 9, y - 2)
        )
        painter.drawLine(
            QtCore.QPointF(move_handle.left() + 9, y + 2),
            QtCore.QPointF(move_handle.right() - 9, y + 2)
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


class StickyNoteItem(QtWidgets.QGraphicsRectItem):
    def __init__(self, rect, body=DEFAULT_STICKY_BODY, color=None):
        super(StickyNoteItem, self).__init__(rect)

        self._dropnote_item = True
        self._sticky_note_item = True
        self.base_color = color or QtGui.QColor(*DEFAULT_STICKY_COLOR)
        self.text_color = QtGui.QColor(*DEFAULT_STICKY_TEXT_COLOR)
        self.font_size = DEFAULT_STICKY_FONT_SIZE
        self.font_family = DEFAULT_FONT_FAMILY
        self.resizing = False
        self.moving_from_handle = False
        self.resize_start_pos = None
        self.resize_start_rect = None
        self.move_start_pos = None
        self.move_start_item_pos = None

        self.setZValue(-99990)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton | QtCore.Qt.RightButton)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)

        self.body_item = QtWidgets.QGraphicsTextItem(body, self)

        self.apply_text_color()

        self.apply_font()
        self.apply_style()
        self.update_text_layout()

    def apply_style(self):
        self.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
        self.setPen(QtGui.QPen(QtCore.Qt.NoPen))

    def apply_text_color(self):
        self.body_item.setDefaultTextColor(self.text_color)

    def apply_font(self):
        body_font = QtGui.QFont()
        body_font.setPointSize(self.font_size)

        if self.font_family:
            body_font.setFamily(self.font_family)

        self.body_item.setFont(body_font)

    def update_text_layout(self):
        rect = self.rect()
        margin = 16

        self.body_item.setTextWidth(max(40, rect.width() - margin * 2))

        self.body_item.setPos(rect.left() + margin, rect.top() + 22)

    def fit_rect_to_text(self):
        rect = QtCore.QRectF(self.rect())
        margin = 16
        body_top = 22
        bottom_margin = 18

        self.update_text_layout()

        body_rect = self.body_item.boundingRect()
        needed_height = body_top + body_rect.height() + bottom_margin
        needed_width = max(
            rect.width(),
            body_rect.width() + margin * 2
        )

        changed = False

        if needed_width > rect.width():
            rect.setWidth(needed_width)
            changed = True

        if needed_height > rect.height():
            rect.setHeight(needed_height)
            changed = True

        if changed:
            self.prepareGeometryChange()
            self.setRect(rect)
            self.update_text_layout()

    def resize_handle_rect(self):
        rect = self.rect()
        return QtCore.QRectF(
            rect.right() - HANDLE_SIZE,
            rect.bottom() - HANDLE_SIZE,
            HANDLE_SIZE,
            HANDLE_SIZE
        )

    def note_path(self):
        rect = self.rect()
        cut = min(STICKY_CORNER_CUT, rect.width() * 0.25, rect.height() * 0.25)

        path = QtGui.QPainterPath()
        path.moveTo(rect.left(), rect.top() + cut)
        path.lineTo(rect.left() + cut, rect.top())
        path.lineTo(rect.right(), rect.top())
        path.lineTo(rect.right(), rect.bottom())
        path.lineTo(rect.left(), rect.bottom())
        path.closeSubpath()

        return path

    def to_data(self):
        rect = self.rect()
        pos = self.pos()
        color = self.base_color
        text_color = self.text_color

        return {
            "kind": "sticky",
            "body": self.body_item.toPlainText(),
            "x": pos.x(),
            "y": pos.y(),
            "rect_x": rect.x(),
            "rect_y": rect.y(),
            "w": rect.width(),
            "h": rect.height(),
            "color": [color.red(), color.green(), color.blue(), color.alpha()],
            "text_color": [text_color.red(), text_color.green(), text_color.blue(), text_color.alpha()],
            "font_size": self.font_size,
            "font_family": self.font_family,
        }

    def edit_properties(self):
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Edit Sticky Note")

        body_edit = QtWidgets.QPlainTextEdit(self.body_item.toPlainText())
        body_edit.setMinimumHeight(90)

        font_combo = QtWidgets.QFontComboBox()
        if self.font_family:
            font_combo.setCurrentFont(QtGui.QFont(self.font_family))

        font_size_spin = QtWidgets.QSpinBox()
        font_size_spin.setRange(8, 48)
        font_size_spin.setValue(self.font_size)

        color_button = QtWidgets.QPushButton("Choose Color")
        text_color_button = QtWidgets.QPushButton("Choose Text Color")
        preview = QtWidgets.QFrame()
        text_preview = QtWidgets.QFrame()
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        chosen_color = QtGui.QColor(self.base_color)
        chosen_text_color = QtGui.QColor(self.text_color)

        def update_preview():
            preview.setFixedSize(42, 22)
            preview.setStyleSheet(
                "background-color: rgba(%d, %d, %d, %d); border: 1px solid rgba(255, 255, 255, 120);"
                % (
                    chosen_color.red(),
                    chosen_color.green(),
                    chosen_color.blue(),
                    chosen_color.alpha()
                )
            )
            text_preview.setFixedSize(42, 22)
            text_preview.setStyleSheet(
                "background-color: rgba(%d, %d, %d, %d); border: 1px solid rgba(255, 255, 255, 120);"
                % (
                    chosen_text_color.red(),
                    chosen_text_color.green(),
                    chosen_text_color.blue(),
                    chosen_text_color.alpha()
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

        def choose_text_color():
            new_color = QtWidgets.QColorDialog.getColor(chosen_text_color, dialog)
            if new_color.isValid():
                new_color.setAlpha(chosen_text_color.alpha())
                chosen_text_color.setRgb(
                    new_color.red(),
                    new_color.green(),
                    new_color.blue(),
                    new_color.alpha()
                )
                update_preview()

        color_row = QtWidgets.QHBoxLayout()
        color_row.addWidget(preview)
        color_row.addWidget(color_button)
        color_row.addStretch()

        text_color_row = QtWidgets.QHBoxLayout()
        text_color_row.addWidget(text_preview)
        text_color_row.addWidget(text_color_button)
        text_color_row.addStretch()

        form = QtWidgets.QFormLayout()
        form.addRow("Text", body_edit)
        form.addRow("Font", font_combo)
        form.addRow("Font Size", font_size_spin)
        form.addRow("Fill Color", color_row)
        form.addRow("Text Color", text_color_row)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addLayout(form)
        layout.addWidget(buttons)

        color_button.clicked.connect(choose_color)
        text_color_button.clicked.connect(choose_text_color)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        update_preview()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            body = body_edit.toPlainText()

            self.body_item.setPlainText(body or DEFAULT_STICKY_BODY)
            self.font_family = font_combo.currentFont().family()
            self.font_size = font_size_spin.value()
            self.base_color = chosen_color
            self.text_color = chosen_text_color
            self.apply_text_color()
            self.apply_font()
            self.apply_style()
            self.update_text_layout()
            self.fit_rect_to_text()
            save_data()

    def delete(self):
        scene = self.scene()
        if scene:
            scene.removeItem(self)

        if self in BACKDROP_ITEMS:
            BACKDROP_ITEMS.remove(self)

        save_data()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        path = self.note_path()
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 95), 1))
        painter.setBrush(QtGui.QBrush(self.base_color))
        painter.drawPath(path)

        rect = self.rect()
        cut = min(STICKY_CORNER_CUT, rect.width() * 0.25, rect.height() * 0.25)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 55), 1))
        painter.drawLine(
            QtCore.QPointF(rect.left(), rect.top() + cut),
            QtCore.QPointF(rect.left() + cut, rect.top())
        )

        resize_handle = self.resize_handle_rect()

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 70), 1))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 16)))
        painter.drawRect(resize_handle)

        painter.drawLine(
            QtCore.QPointF(resize_handle.left() + 4, resize_handle.bottom() - 4),
            QtCore.QPointF(resize_handle.right() - 4, resize_handle.top() + 4)
        )

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.resize_handle_rect().contains(event.pos()):
            self.resizing = True
            self.resize_start_pos = event.scenePos()
            self.resize_start_rect = QtCore.QRectF(self.rect())
            event.accept()
            return

        super(StickyNoteItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            delta = event.scenePos() - self.resize_start_pos
            rect = QtCore.QRectF(self.resize_start_rect)
            rect.setWidth(max(MIN_WIDTH, rect.width() + delta.x()))
            rect.setHeight(max(MIN_HEIGHT, rect.height() + delta.y()))

            self.prepareGeometryChange()
            self.setRect(rect)
            self.update_text_layout()
            self.update()
            event.accept()
            return

        super(StickyNoteItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            self.resize_start_pos = None
            self.resize_start_rect = None
            save_data()
            event.accept()
            return

        super(StickyNoteItem, self).mouseReleaseEvent(event)
        save_data()

    def mouseDoubleClickEvent(self, event):
        self.edit_properties()
        event.accept()


def create_backdrop_from_selection(scene):
    global ITEMS_VISIBLE

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
    ITEMS_VISIBLE = True
    save_data()
    return backdrop


def create_backdrop_at_view_center(scene, view):
    global ITEMS_VISIBLE

    try:
        center = view.mapToScene(view.viewport().rect().center())
    except Exception:
        center = QtCore.QPointF(0, 0)

    rect = QtCore.QRectF(
        center.x() - DEFAULT_BACKDROP_WIDTH * 0.5,
        center.y() - DEFAULT_BACKDROP_HEIGHT * 0.5,
        DEFAULT_BACKDROP_WIDTH,
        DEFAULT_BACKDROP_HEIGHT
    )

    backdrop = DropNoteItem(rect)
    scene.addItem(backdrop)
    BACKDROP_ITEMS.append(backdrop)
    backdrop.setSelected(True)
    ITEMS_VISIBLE = True
    save_data()
    return backdrop


def create_sticky_at_view_center(scene, view):
    global ITEMS_VISIBLE

    try:
        center = view.mapToScene(view.viewport().rect().center())
    except Exception:
        center = QtCore.QPointF(0, 0)

    existing_sticky_count = 0
    for item in BACKDROP_ITEMS:
        try:
            if item.scene() is scene and getattr(item, "_sticky_note_item", False):
                existing_sticky_count += 1
        except Exception:
            pass

    offset = 28 * existing_sticky_count
    rect = QtCore.QRectF(
        center.x() - DEFAULT_STICKY_WIDTH * 0.5 + offset,
        center.y() - DEFAULT_STICKY_HEIGHT * 0.5 + offset,
        DEFAULT_STICKY_WIDTH,
        DEFAULT_STICKY_HEIGHT
    )

    sticky = StickyNoteItem(rect)
    scene.addItem(sticky)
    BACKDROP_ITEMS.append(sticky)
    sticky.setSelected(True)
    ITEMS_VISIBLE = True
    save_data()
    return sticky


def restore_backdrops(scene, panel_key=None):
    global ITEMS_VISIBLE

    if panel_key is None:
        panel_key = CURRENT_PANEL_KEY

    restored = 0

    for old in list(BACKDROP_ITEMS):
        try:
            if old.scene():
                old.scene().removeItem(old)
        except Exception:
            pass

    BACKDROP_ITEMS[:] = []

    for entry in load_data():
        entry_panel_key = entry.get("panel_key")
        if entry_panel_key is not None and entry_panel_key != panel_key:
            continue

        try:
            rect = QtCore.QRectF(
                float(entry.get("rect_x", 0)),
                float(entry.get("rect_y", 0)),
                float(entry.get("w", 400)),
                float(entry.get("h", 250))
            )

            if entry.get("kind", "backdrop") == "sticky":
                sticky_body = entry.get("body", DEFAULT_STICKY_BODY)
                old_title = entry.get("title", "")
                if old_title:
                    sticky_body = old_title + "\n" + sticky_body

                backdrop = StickyNoteItem(
                    rect,
                    body=sticky_body,
                    color=color_from_data(entry)
                )
                backdrop.font_size = int(entry.get("font_size", DEFAULT_STICKY_FONT_SIZE))
                backdrop.font_family = entry.get("font_family", DEFAULT_FONT_FAMILY)
                backdrop.text_color = text_color_from_data(entry)
                backdrop.apply_text_color()
                backdrop.apply_font()
                backdrop.apply_style()
                backdrop.update_text_layout()
                backdrop.fit_rect_to_text()
            else:
                backdrop = DropNoteItem(
                    rect,
                    title=entry.get("title", DEFAULT_TITLE),
                    color=color_from_data(entry)
                )
                backdrop.font_size = int(entry.get("font_size", DEFAULT_FONT_SIZE))
                backdrop.font_family = entry.get("font_family", DEFAULT_FONT_FAMILY)
                backdrop.fill_transparent = bool(entry.get("fill_transparent", False))
                backdrop.apply_font_size()
                backdrop.apply_style()

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

    ITEMS_VISIBLE = True


def hide_runtime_items():
    global ITEMS_VISIBLE

    for item in list(BACKDROP_ITEMS):
        try:
            scene = item.scene()
            if scene:
                scene.removeItem(item)
        except Exception:
            pass

    BACKDROP_ITEMS[:] = []
    ITEMS_VISIBLE = False
    print("%s: hidden runtime items." % PLUGIN_NAME)


def runtime_items_for_scene(scene):
    items = []

    for item in BACKDROP_ITEMS:
        try:
            if item.scene() is scene:
                items.append(item)
        except Exception:
            pass

    return items


def hide_runtime_items_for_scene(scene):
    global ITEMS_VISIBLE

    for item in runtime_items_for_scene(scene):
        try:
            scene.removeItem(item)
        except Exception:
            pass

        if item in BACKDROP_ITEMS:
            BACKDROP_ITEMS.remove(item)

    ITEMS_VISIBLE = bool(BACKDROP_ITEMS)
    print("%s: hidden runtime items for %s." % (PLUGIN_NAME, CURRENT_PANEL_KEY))


def scene_has_runtime_items(scene):
    for item in BACKDROP_ITEMS:
        try:
            if item.scene() is scene:
                return True
        except Exception:
            pass

    return False


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


def refresh_dropnotes():
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

    panel_key = set_current_panel_key_from_view(view)
    restore_backdrops(scene, panel_key)
    print("%s: shown saved DropNotes." % PLUGIN_NAME)


def toggle_dropnotes_visibility():
    view = find_best_graphics_view()
    if view is None:
        refresh_dropnotes()
        return

    scene = get_scene(view)
    if scene is None:
        refresh_dropnotes()
        return

    set_current_panel_key_from_view(view)

    if runtime_items_for_scene(scene):
        hide_runtime_items_for_scene(scene)
    else:
        refresh_dropnotes()


def create_dropnote():
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

    panel_key = set_current_panel_key_from_view(view)

    if not scene_has_runtime_items(scene):
        restore_backdrops(scene, panel_key)

    if create_backdrop_from_selection(scene):
        print("%s: created from selection." % PLUGIN_NAME)
    else:
        create_backdrop_at_view_center(scene, view)
        print("%s: created at view center." % PLUGIN_NAME)


def create_sticky_note():
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

    panel_key = set_current_panel_key_from_view(view)

    if not scene_has_runtime_items(scene):
        restore_backdrops(scene, panel_key)

    create_sticky_at_view_center(scene, view)
    print("%s: created Sticky Note." % PLUGIN_NAME)


def run():
    create_dropnote()


class DropNoteEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyRelease:
            key = event.key()
            if key in (QtCore.Qt.Key_B, QtCore.Qt.Key_N, QtCore.Qt.Key_S):
                HOTKEYS_DOWN.discard(key)
            return False

        if event.type() != QtCore.QEvent.KeyPress:
            return False

        view = focused_graphics_view()
        if not is_dropnote_view(view):
            return False

        key = event.key()
        modifiers = event.modifiers()
        scene = get_scene(view)

        if key in (QtCore.Qt.Key_B, QtCore.Qt.Key_N, QtCore.Qt.Key_S):
            if event.isAutoRepeat() or key in HOTKEYS_DOWN:
                event.accept()
                return True

        if key in (QtCore.Qt.Key_B, QtCore.Qt.Key_N, QtCore.Qt.Key_S) and modifiers == QtCore.Qt.ShiftModifier:
            HOTKEYS_DOWN.add(key)

        if key == QtCore.Qt.Key_B and modifiers == QtCore.Qt.ShiftModifier:
            toggle_dropnotes_visibility()
            event.accept()
            return True

        if key == QtCore.Qt.Key_N and modifiers == QtCore.Qt.ShiftModifier:
            create_dropnote()
            event.accept()
            return True

        if key == QtCore.Qt.Key_S and modifiers == QtCore.Qt.ShiftModifier:
            create_sticky_note()
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

    old_filter = getattr(app, APP_FILTER_ATTR, None)
    if old_filter is not None and qt_is_alive(old_filter):
        try:
            app.removeEventFilter(old_filter)
        except Exception:
            pass

    if EVENT_FILTER is None or not qt_is_alive(EVENT_FILTER):
        EVENT_FILTER = DropNoteEventFilter()
        app.installEventFilter(EVENT_FILTER)
        setattr(app, APP_FILTER_ATTR, EVENT_FILTER)
        print("%s: Shift+B hotkey installed." % PLUGIN_NAME)


def uninstall_event_filter():
    global EVENT_FILTER

    app = QtWidgets.QApplication.instance()
    if app and EVENT_FILTER is not None and qt_is_alive(EVENT_FILTER):
        app.removeEventFilter(EVENT_FILTER)
        print("%s: hotkey removed." % PLUGIN_NAME)

    if app and getattr(app, APP_FILTER_ATTR, None) is EVENT_FILTER:
        try:
            delattr(app, APP_FILTER_ATTR)
        except Exception:
            setattr(app, APP_FILTER_ATTR, None)

    EVENT_FILTER = None
    HOTKEYS_DOWN.clear()


def cleanup_runtime_items():
    global ITEMS_VISIBLE

    uninstall_event_filter()

    for item in list(BACKDROP_ITEMS):
        try:
            scene = item.scene()
            if scene:
                scene.removeItem(item)
        except Exception:
            pass

    BACKDROP_ITEMS[:] = []
    ITEMS_VISIBLE = False
    print("%s: runtime items cleaned." % PLUGIN_NAME)
