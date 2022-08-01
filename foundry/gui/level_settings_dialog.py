from typing import List, Optional

from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QLabel, QVBoxLayout

from foundry.game.gfx.objects import EnemyItem
from foundry.game.level.LevelRef import LevelRef
from foundry.gui import label_and_widget
from foundry.gui.CustomDialog import CustomDialog
from foundry.gui.Spinner import Spinner
from foundry.gui.commands import AddObject, ChangeLockIndex, RemoveObjects
from smb3parse.constants import OBJ_AUTOSCROLL, OBJ_BOOMBOOM, OBJ_FLYING_BOOMBOOM

AUTOSCROLL_LABELS = {
    -1: "No Autoscroll in Level.",
    0: "Horizontal Autoscroll",
    1: "Horizontal Autoscroll",
    2: "Moves Level up and right; screen wraps, vertically",
    3: "Moves ceiling down and up (Fortress Spike Levels)",
    4: "Moves ground up, until a door hits the ground",
    5: "Moves ground up and down, used for changes in over-water Levels",
}


class LevelSettingsDialog(CustomDialog):
    def __init__(self, parent, level_ref: LevelRef):
        super(LevelSettingsDialog, self).__init__(parent, title="Other Level Settings")

        self.level_ref = level_ref

        self.original_autoscroll_item = _get_autoscroll(self.level_ref.enemies)
        self.original_y_value = self.original_autoscroll_item.y_position if self.original_autoscroll_item else -1

        QVBoxLayout(self)

        # Autoscroll
        auto_scroll_group = QGroupBox("Autoscrolling", self)
        QVBoxLayout(auto_scroll_group)

        self.enabled_checkbox = QCheckBox("Enable Autoscroll in level", self)
        self.enabled_checkbox.toggled.connect(self._insert_autoscroll_object)

        self.y_position_spinner = Spinner(self, maximum=0x60 - 1)
        self.y_position_spinner.valueChanged.connect(self._update_y_position)

        self.auto_scroll_type_label = QLabel(self)

        auto_scroll_group.layout().addWidget(self.enabled_checkbox)
        auto_scroll_group.layout().addLayout(label_and_widget("Scroll Type: ", self.y_position_spinner))
        auto_scroll_group.layout().addWidget(self.auto_scroll_type_label)

        boom_boom_group = QGroupBox("Boom Boom Lock Destruction Index")
        QVBoxLayout(boom_boom_group)

        boom_booms = _get_boom_booms(self.level_ref.enemies)
        self.original_lock_indexes = [boom_boom.lock_index for boom_boom in boom_booms]

        self.boom_boom_dropdown = QComboBox()
        self.boom_boom_dropdown.addItems(
            [f"{boom_boom.name} at {boom_boom.get_position()}" for boom_boom in boom_booms]
        )
        self.boom_boom_dropdown.currentIndexChanged.connect(self._on_boom_boom_dropdown)

        self.boom_boom_index_spinner = Spinner(self, maximum=3)
        self.boom_boom_index_spinner.setEnabled(bool(boom_booms))
        self.boom_boom_index_spinner.valueChanged.connect(self._on_boom_boom_spinner)

        if boom_booms:
            self._on_boom_boom_dropdown(0)

        boom_boom_group.layout().addWidget(self.boom_boom_dropdown)
        boom_boom_group.layout().addLayout(label_and_widget("Lock index", self.boom_boom_index_spinner))

        self.layout().addWidget(auto_scroll_group)
        self.layout().addWidget(boom_boom_group)

        self.update()

    @property
    def undo_stack(self) -> QUndoStack:
        return self.parent().window().findChild(QUndoStack, "undo_stack")

    def update(self):
        # auto scroll
        autoscroll_item = _get_autoscroll(self.level_ref.enemies)

        self.enabled_checkbox.setChecked(autoscroll_item is not None)
        self.y_position_spinner.setEnabled(autoscroll_item is not None)

        if autoscroll_item is None:
            self.auto_scroll_type_label.setText(AUTOSCROLL_LABELS[-1])
        else:
            self.y_position_spinner.setValue(autoscroll_item.y_position)
            self.auto_scroll_type_label.setText(AUTOSCROLL_LABELS[autoscroll_item.y_position >> 4])

    def _update_y_position(self, _):
        autoscroll_item = _get_autoscroll(self.level_ref.enemies)

        autoscroll_item.y_position = self.y_position_spinner.value()

        self.level_ref.data_changed.emit()

        self.update()

    def _insert_autoscroll_object(self, should_insert: bool):
        autoscroll_item = _get_autoscroll(self.level_ref.enemies)

        if autoscroll_item is not None:
            self.level_ref.enemies.remove(autoscroll_item)

        if should_insert:
            self.level_ref.enemies.insert(0, self._create_autoscroll_object())

        self.level_ref.data_changed.emit()

        self.update()

    def _create_autoscroll_object(self):
        return self.level_ref.level.enemy_item_factory.from_properties(
            OBJ_AUTOSCROLL, 0, self.y_position_spinner.value()
        )

    def _on_boom_boom_dropdown(self, new_index: int):
        boom_boom = _get_boom_booms(self.level_ref.enemies)[new_index]

        self.boom_boom_index_spinner.setValue(boom_boom.lock_index)

    def _on_boom_boom_spinner(self, new_value):
        boom_boom = _get_boom_booms(self.level_ref.enemies)[self.boom_boom_dropdown.currentIndex()]

        boom_boom.lock_index = new_value

    def closeEvent(self, event):
        self._handle_auto_scroll_on_close()
        self._handle_boom_booms_on_close()

        super(LevelSettingsDialog, self).closeEvent(event)

    def _handle_boom_booms_on_close(self):
        boom_booms = _get_boom_booms(self.level_ref.enemies)

        for old_index, boom_boom in zip(self.original_lock_indexes, boom_booms):
            boom_boom.lock_index, new_index = old_index, boom_boom.lock_index

            if boom_boom.lock_index != new_index:
                self.undo_stack.push(ChangeLockIndex(boom_boom, new_index))

    def _handle_auto_scroll_on_close(self):
        current_autoscroll_item = _get_autoscroll(self.level_ref.enemies)

        autoscroll_kept_disabled = self.original_autoscroll_item is None and current_autoscroll_item is None
        autoscroll_was_disabled = self.original_autoscroll_item is not None and current_autoscroll_item is None
        autoscroll_was_enabled = self.original_autoscroll_item is None and current_autoscroll_item is not None

        if autoscroll_kept_disabled:
            # nothing to do
            pass
        elif autoscroll_was_disabled:
            self.level_ref.level.enemies.insert(0, self.original_autoscroll_item)
            self.undo_stack.push(RemoveObjects(self.level_ref.level, [self.original_autoscroll_item]))
        elif autoscroll_was_enabled:
            self.level_ref.level.remove_object(current_autoscroll_item)
            self.undo_stack.push(AddObject(self.level_ref.level, current_autoscroll_item, 0))
        else:
            # autoscroll object might have been changed, first reset state from the start
            assert self.original_autoscroll_item is not None

            if current_autoscroll_item is self.original_autoscroll_item:
                current_autoscroll_item = self.original_autoscroll_item.copy()
            else:
                self.level_ref.level.remove_object(current_autoscroll_item)
                self.level_ref.level.enemies.insert(0, self.original_autoscroll_item)

            if self.original_y_value != current_autoscroll_item.y_position:
                assert self.original_autoscroll_item is not current_autoscroll_item

                self.undo_stack.beginMacro("Change Autoscroll Path")

                self.undo_stack.push(RemoveObjects(self.level_ref.level, [self.original_autoscroll_item]))
                self.undo_stack.push(AddObject(self.level_ref.level, current_autoscroll_item, 0))

                self.undo_stack.endMacro()


def _get_autoscroll(enemy_items: List[EnemyItem]) -> Optional[EnemyItem]:
    for item in enemy_items:
        if item.obj_index == OBJ_AUTOSCROLL:
            return item
    else:
        return None


def _get_boom_booms(enemy_items: List[EnemyItem]) -> List[EnemyItem]:
    boom_booms = []

    for item in enemy_items:
        if item.obj_index in [OBJ_BOOMBOOM, OBJ_FLYING_BOOMBOOM]:
            boom_booms.append(item)

    return boom_booms
