from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from promptvault.crud import DataOperations, DuplicateCommandError, InvalidCommandError


class AddPromptDialog(QDialog):
    """Modal dialog for creating a new prompt.

    Stays open and shows an inline error message if the submitted
    data is invalid or the command already exists; only closes
    (accepted) once the prompt is successfully created.

    Args:
        data_ops: The DataOperations instance to write through.
        parent: The parent widget (typically the main window).
    """

    def __init__(self, data_ops: DataOperations, parent=None) -> None:
        super().__init__(parent)
        self.data_ops = data_ops

        self.setWindowTitle("Add Prompt")
        self.resize(450, 400)

        self._command_input = QLineEdit()
        self._title_input = QLineEdit()
        self._body_input = QTextEdit()
        self._tags_input = QLineEdit()
        self._tags_input.setPlaceholderText("Optional, comma-separated")

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Command:", self._command_input)
        form_layout.addRow("Title:", self._title_input)
        form_layout.addRow("Body:", self._body_input)
        form_layout.addRow("Tags:", self._tags_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_submit)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self._error_label)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def _on_submit(self) -> None:
        """Attempt to add the prompt; keep the dialog open on failure."""
        command = self._command_input.text().strip()
        title = self._title_input.text().strip()
        body = self._body_input.toPlainText().strip()
        tags_text = self._tags_input.text().strip()

        tag_list = [t.strip() for t in tags_text.split(",") if t.strip()] or None

        try:
            self.data_ops.add_prompt(
                command=command, title=title, body=body, tags=tag_list
            )
        except (DuplicateCommandError, InvalidCommandError) as error:
            self._error_label.setText(str(error))
            self._error_label.setVisible(True)
            return

        self.accept()
