from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from promptvault.crud import DataOperations, PromptNotFoundError, TagAlreadyAppliedError


class TagDialog(QDialog):
    """Modal dialog for adding/removing tags on an existing prompt.

    Shows the prompt's current tags in a list, with a text field to
    add a new tag and a button to remove whichever tag is selected.
    Each add/remove is applied immediately (not batched) since tags
    are a live, incremental collection rather than a form to submit.

    Args:
        data_ops: The DataOperations instance to write through.
        command: The command name of the prompt being tagged.
        parent: The parent widget (typically the main window).
    """

    def __init__(self, data_ops: DataOperations, command: str, parent=None) -> None:
        super().__init__(parent)
        self.data_ops = data_ops
        self.command = command

        self.setWindowTitle(f"Manage Tags: {command}")
        self.resize(350, 350)

        self._tag_list_widget = QListWidget()
        self._new_tag_input = QLineEdit()
        self._new_tag_input.setPlaceholderText("New tag name")

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)

        add_button = QPushButton("Add Tag")
        add_button.clicked.connect(self._on_add_tag)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._on_remove_tag)

        add_row = QHBoxLayout()
        add_row.addWidget(self._new_tag_input)
        add_row.addWidget(add_button)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        close_box.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Current tags:"))
        layout.addWidget(self._tag_list_widget)
        layout.addLayout(add_row)
        layout.addWidget(remove_button)
        layout.addWidget(self._error_label)
        layout.addWidget(close_box)
        self.setLayout(layout)

        self._load_tags()

    def _load_tags(self) -> None:
        """Refresh the tag list from the database for this prompt."""
        self._tag_list_widget.clear()

        all_prompts = self.data_ops.list_prompts_with_tags()
        tags_str = None
        for entry in all_prompts:
            if entry["command"] == self.command:
                tags_str = entry["tags"]
                break

        if isinstance(tags_str, str) and tags_str:
            for tag_name in tags_str.split(", "):
                self._tag_list_widget.addItem(tag_name)

    def _on_add_tag(self) -> None:
        """Apply the tag typed into the input field."""
        tag_name = self._new_tag_input.text().strip()

        if not tag_name:
            return

        try:
            self.data_ops.add_tag_to_prompt(command=self.command, tag_name=tag_name)
        except (PromptNotFoundError, TagAlreadyAppliedError) as error:
            self._error_label.setText(str(error))
            self._error_label.setVisible(True)
            return

        self._error_label.setVisible(False)
        self._new_tag_input.clear()
        self._load_tags()

    def _on_remove_tag(self) -> None:
        """Remove whichever tag is currently selected in the list."""
        item = self._tag_list_widget.currentItem()

        if item is None:
            return

        tag_name = item.text()

        try:
            self.data_ops.remove_tag_from_prompt(
                command=self.command, tag_name=tag_name
            )
        except PromptNotFoundError as error:
            self._error_label.setText(str(error))
            self._error_label.setVisible(True)
            return

        self._error_label.setVisible(False)
        self._load_tags()
