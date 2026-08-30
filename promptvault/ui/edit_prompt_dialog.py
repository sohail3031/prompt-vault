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

from promptvault.crud import DataOperations
from promptvault.crud import InvalidCommandError


class EditPromptDialog(QDialog):
    """Modal dialog for editing an existing prompt's title and/or body.

    The command is shown but not editable — it's the lookup key, not
    a field that can change here (matching update_prompt's contract).

    Args:
        data_ops: The DataOperations instance to write through.
        command: The command name of the prompt being edited.
        current_title: The prompt's current title, used to pre-fill.
        current_body: The prompt's current body, used to pre-fill.
        parent: The parent widget (typically the main window).
    """

    def __init__(
        self,
        data_ops: DataOperations,
        command: str,
        current_title: str,
        current_body: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.data_ops = data_ops
        self.command = command

        self.setWindowTitle(f"Edit Prompt: {command}")
        self.resize(450, 400)

        self._title_input = QLineEdit(current_title)
        self._body_input = QTextEdit()
        self._body_input.setPlainText(current_body)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)
        self._error_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Command:", QLabel(command))
        form_layout.addRow("Title:", self._title_input)
        form_layout.addRow("Body:", self._body_input)

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
        """Attempt to update the prompt; keep the dialog open on failure."""
        title = self._title_input.text().strip()
        body = self._body_input.toPlainText().strip()

        try:
            self.data_ops.update_prompt(command=self.command, title=title, body=body)
        except InvalidCommandError as error:
            self._error_label.setText(str(error))
            self._error_label.setVisible(True)
            return

        self.accept()
