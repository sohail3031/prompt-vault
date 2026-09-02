from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from promptvault.crud import DataOperations
from promptvault.ui.add_prompt_dialog import AddPromptDialog
from promptvault.ui.edit_prompt_dialog import EditPromptDialog
from promptvault.ui.tag_dialog import TagDialog

PLACEHOLDER_TITLE = "Select a prompt to view its details"


def _resolve_asset_path(*parts: str) -> Path:
    """Resolve a path to a bundled asset, whether running from source
    or as a PyInstaller-packaged executable.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_path = Path(__file__).parent.parent.parent

    return base_path.joinpath(*parts)


class MainWindow(QMainWindow):
    """Main window for the PromptVault desktop app: a list + detail view.

    Displays every stored prompt in a filterable list on the left;
    selecting a prompt shows its full title, body, and tags in a
    detail panel on the right. Supports full CRUD via Add/Edit/
    Delete/Manage Tags buttons, plus a Delete key shortcut.

    Args:
        data_ops: Optional DataOperations instance to use for all
            data access. Defaults to a real DataOperations() pointed
            at the production database.
    """

    def __init__(self, data_ops: DataOperations | None = None) -> None:
        super().__init__()
        self.data_ops: DataOperations = (
            data_ops if data_ops is not None else DataOperations()
        )

        self.setWindowTitle("PromptVault")
        self.setWindowIcon(QIcon(str(_resolve_asset_path("assets", "icon.ico"))))
        self.resize(900, 600)

        # --- Widgets ---
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search by command or title...")

        self._list_widget = QListWidget()

        self._detail_title_label = QLabel()
        self._detail_body_label = QTextEdit()
        self._detail_body_label.setReadOnly(True)
        self._detail_tag_label = QLabel()

        self._add_button = QPushButton("Add")
        self._edit_button = QPushButton("Edit")
        self._delete_button = QPushButton("Delete")
        self._tags_button = QPushButton("Manage Tags")

        self._edit_button.setEnabled(False)
        self._delete_button.setEnabled(False)
        self._tags_button.setEnabled(False)

        # --- Detail panel layout ---
        detail_widget = QWidget()
        detail_layout = QVBoxLayout()
        detail_layout.addWidget(self._detail_title_label)
        detail_layout.addWidget(self._detail_body_label)
        detail_layout.addWidget(self._detail_tag_label)
        detail_widget.setLayout(detail_layout)

        # --- List + detail, side by side ---
        content_layout = QHBoxLayout()
        content_layout.addWidget(self._list_widget)
        content_layout.addWidget(detail_widget)

        # --- Button row ---
        button_row = QHBoxLayout()
        button_row.addWidget(self._add_button)
        button_row.addWidget(self._edit_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._tags_button)

        # --- Search box on top, buttons, content below ---
        outer_layout = QVBoxLayout()
        outer_layout.addWidget(self._search_box)
        outer_layout.addLayout(button_row)
        outer_layout.addLayout(content_layout)

        central_widget = QWidget()
        central_widget.setLayout(outer_layout)
        self.setCentralWidget(central_widget)

        # --- Signals ---
        self._list_widget.itemClicked.connect(self._on_prompt_selected)
        self._search_box.textChanged.connect(self._on_search_text_changed)
        self._add_button.clicked.connect(self._on_add_clicked)
        self._edit_button.clicked.connect(self._on_edit_clicked)
        self._delete_button.clicked.connect(self._on_delete_clicked)
        self._tags_button.clicked.connect(self._on_tags_clicked)

        # --- Delete key shortcut, scoped to the list widget only ---
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._list_widget)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        delete_shortcut.activated.connect(self._on_delete_clicked)

        # --- Initial data load ---
        self._selected_command: str | None = None
        self._all_prompts: list[dict] = []
        self._show_placeholder_detail()
        self.refresh()

    def refresh(self) -> None:
        """Reload the prompt list from the database and redisplay it.

        Called on startup and after every successful add/edit/delete/
        tag change, so the UI never drifts from what's actually in
        the database.
        """
        self._all_prompts = self.data_ops.list_prompts_with_tags()
        self._on_search_text_changed(self._search_box.text())

    def _populate_list(self, prompts: list[dict]) -> None:
        """Clear and refill the list widget from the given prompts."""
        self._list_widget.clear()

        for prompt in prompts:
            item = QListWidgetItem(f"{prompt['command']} - {prompt['title']}")
            item.setData(Qt.ItemDataRole.UserRole, prompt["command"])
            self._list_widget.addItem(item)

    def _show_placeholder_detail(self) -> None:
        """Reset the detail panel to its empty/no-selection state."""
        self._detail_title_label.setText(PLACEHOLDER_TITLE)
        self._detail_body_label.clear()
        self._detail_tag_label.clear()

    def _on_prompt_selected(self) -> None:
        """Load the selected prompt's full details into the detail panel."""
        item = self._list_widget.currentItem()

        if item is None:
            self._selected_command = None
            self._edit_button.setEnabled(False)
            self._delete_button.setEnabled(False)
            self._tags_button.setEnabled(False)
            self._show_placeholder_detail()
            return

        command = item.data(Qt.ItemDataRole.UserRole)
        prompt = self.data_ops.get_prompt(command=command)

        if prompt is None:
            return

        tags = None
        for entry in self._all_prompts:
            if entry["command"] == command:
                tags = entry["tags"]
                break

        self._detail_title_label.setText(prompt.title)
        self._detail_body_label.setPlainText(prompt.body)
        self._detail_tag_label.setText(f"Tags: {tags if tags else 'none'}")

        self._selected_command = command
        self._edit_button.setEnabled(True)
        self._delete_button.setEnabled(True)
        self._tags_button.setEnabled(True)

    def _on_search_text_changed(self, text: str) -> None:
        """Filter the visible list in-memory by command/title substring."""
        text = text.lower().strip()

        filtered = [
            prompt
            for prompt in self._all_prompts
            if text in prompt["command"].lower() or text in prompt["title"].lower()
        ]

        self._populate_list(prompts=filtered)

    def _on_add_clicked(self) -> None:
        """Open the Add Prompt dialog; refresh the list on success."""
        dialog = AddPromptDialog(data_ops=self.data_ops, parent=self)

        if dialog.exec():
            self.refresh()

    def _on_edit_clicked(self) -> None:
        """Open the Edit Prompt dialog for the selected prompt."""
        if self._selected_command is None:
            return

        prompt = self.data_ops.get_prompt(command=self._selected_command)

        if prompt is None:
            self._show_error(f"No prompt found with command: {self._selected_command}")
            return

        dialog = EditPromptDialog(
            data_ops=self.data_ops,
            command=self._selected_command,
            current_title=prompt.title,
            current_body=prompt.body,
            parent=self,
        )

        if dialog.exec():
            self.refresh()
            self._on_prompt_selected()

    def _on_delete_clicked(self) -> None:
        """Confirm and delete the selected prompt.

        Triggered either by the Delete button or the Delete key
        shortcut (when the list widget has focus).
        """
        if self._selected_command is None:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete prompt '{self._selected_command}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.data_ops.delete_prompt(command=self._selected_command)
        except Exception as error:
            self._show_error(str(error))
            return

        self._selected_command = None
        self._edit_button.setEnabled(False)
        self._delete_button.setEnabled(False)
        self._tags_button.setEnabled(False)
        self._show_placeholder_detail()

        self.refresh()

    def _on_tags_clicked(self) -> None:
        """Open the tag management dialog for the selected prompt."""
        if self._selected_command is None:
            return

        dialog = TagDialog(
            data_ops=self.data_ops, command=self._selected_command, parent=self
        )
        dialog.exec()

        # Tags may have changed regardless of how the dialog was closed.
        self.refresh()
        self._on_prompt_selected()

    def _show_error(self, message: str) -> None:
        """Show an error message to the user via a warning dialog."""
        QMessageBox.warning(self, "Error", message)
