from enum import Enum
from typing import List, Tuple

from PySide6.QtCore import QPoint, SignalInstance
from PySide6.QtWidgets import QMenu

from foundry import icon
from foundry.game.gfx.objects.object_like import ObjectLike
from foundry.game.level.LevelRef import LevelRef
from smb3parse.data_points import Position


class CMMode(Enum):
    BG = 1
    OBJ = 2
    LIST = 3


MAX_ORIGIN = 0xFF, 0xFF


class ContextMenu(QMenu):
    pass


class LevelContextMenu(ContextMenu):
    triggered: SignalInstance

    def __init__(self, level_ref: LevelRef):
        super(LevelContextMenu, self).__init__()

        self.level_ref = level_ref

        self.copied_objects: List[ObjectLike] = []
        self.copied_objects_origin = Position.from_xy(0, 0)
        self.last_opened_at = QPoint(0, 0)

        self.add_object_action = self.addAction("Add Object")
        self.add_object_action.setIcon(icon("plus.svg"))

        self.addSeparator()

        self.cut_action = self.addAction("Cut")
        self.cut_action.setIcon(icon("scissors.svg"))
        self.copy_action = self.addAction("Copy")
        self.copy_action.setIcon(icon("copy.svg"))
        self.paste_action = self.addAction("Paste")
        self.paste_action.setIcon(icon("clipboard.svg"))

        self.addSeparator()

        self.into_foreground_action = self.addAction("To Foreground")
        self.into_foreground_action.setIcon(icon("upload.svg"))
        self.into_background_action = self.addAction("To Background")
        self.into_background_action.setIcon(icon("download.svg"))

        self.addSeparator()

        self.remove_action = self.addAction("Remove")
        self.remove_action.setIcon(icon("minus.svg"))

    def set_copied_objects(self, objects: List[ObjectLike]):
        if not objects:
            return

        self.copied_objects = objects

        min_x, min_y = MAX_ORIGIN

        for obj in objects:
            obj_x, obj_y = obj.get_position()

            min_x = min(min_x, obj_x)
            min_y = min(min_y, obj_y)

        min_x = max(min_x, 0)
        min_y = max(min_y, 0)

        self.copied_objects_origin = Position.from_xy(min_x, min_y)

    def get_copied_objects(self) -> Tuple[List[ObjectLike], Tuple[int, int]]:
        return self.copied_objects, self.copied_objects_origin

    def set_position(self, position: QPoint):
        self.last_opened_at = position

    def get_position(self) -> QPoint:
        return self.last_opened_at

    def get_all_menu_item_ids(self):
        return [action.property("ID") for action in self.actions()]

    def as_object_menu(self) -> "LevelContextMenu":
        return self._setup_items(CMMode.OBJ)

    def as_background_menu(self) -> "LevelContextMenu":
        return self._setup_items(CMMode.BG)

    def as_list_menu(self) -> "LevelContextMenu":
        return self._setup_items(CMMode.LIST)

    def _setup_items(self, mode: CMMode):
        objects_selected = bool(self.level_ref.selected_objects)
        objects_copied = bool(self.copied_objects)

        self.cut_action.setEnabled(not mode == CMMode.BG and objects_selected)
        self.copy_action.setEnabled(not mode == CMMode.BG and objects_selected)
        self.paste_action.setEnabled(not mode == CMMode.LIST and objects_copied)

        self.into_background_action.setEnabled(not mode == CMMode.BG and objects_selected)
        self.into_foreground_action.setEnabled(not mode == CMMode.BG and objects_selected)

        self.remove_action.setEnabled(not mode == CMMode.BG and objects_selected)
        self.add_object_action.setEnabled(not mode == CMMode.LIST)

        return self
