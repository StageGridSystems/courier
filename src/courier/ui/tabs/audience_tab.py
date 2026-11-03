"""Audience management tab."""

from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from courier.audience.extract import extract_emails_from_file, extract_emails_from_text
from courier.audience.models import AudienceStore, ImportPreview
from courier.ui.widgets.chip_field import ChipField


class AudienceTab(QWidget):
    changed = Signal()

    def __init__(self, store: AudienceStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.store.ensure_default()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Audience")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.addWidget(QLabel("Lists"))
        self.list_picker = QListWidget()
        self.list_picker.currentTextChanged.connect(self._on_list_selected)
        left_l.addWidget(self.list_picker)
        list_btns = QHBoxLayout()
        add_list = QPushButton("New")
        add_list.clicked.connect(self._new_list)
        rename_list = QPushButton("Rename")
        rename_list.clicked.connect(self._rename_list)
        del_list = QPushButton("Delete")
        del_list.clicked.connect(self._delete_list)
        list_btns.addWidget(add_list)
        list_btns.addWidget(rename_list)
        list_btns.addWidget(del_list)
        left_l.addLayout(list_btns)
        left_l.addWidget(QLabel("Suppression / unsubscribe"))
        self.suppression = ChipField()
        self.suppression.set_emails(self.store.suppression)
        self.suppression.changed.connect(self._sync_suppression)
        left_l.addWidget(self.suppression)
        splitter.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.addWidget(QLabel("Add recipients (chips)"))
        self.chips = ChipField()
        right_l.addWidget(self.chips)
        chip_row = QHBoxLayout()
        add_chips = QPushButton("Add chips to list")
        add_chips.setObjectName("primaryButton")
        add_chips.clicked.connect(self._add_chips)
        chip_row.addWidget(add_chips)
        paste_btn = QPushButton("Paste & extract")
        paste_btn.clicked.connect(self._paste_extract)
        chip_row.addWidget(paste_btn)
        import_btn = QPushButton("Import file…")
        import_btn.clicked.connect(self._import_file)
        chip_row.addWidget(import_btn)
        chip_row.addStretch()
        right_l.addLayout(chip_row)

        filter_row = QHBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search / filter…")
        self.filter_edit.textChanged.connect(self._refresh_emails)
        filter_row.addWidget(self.filter_edit)
        select_all = QPushButton("Select all")
        select_all.clicked.connect(self._select_all)
        remove_sel = QPushButton("Remove selected")
        remove_sel.clicked.connect(self._remove_selected)
        export_btn = QPushButton("Export CSV")
        export_btn.clicked.connect(self._export_csv)
        filter_row.addWidget(select_all)
        filter_row.addWidget(remove_sel)
        filter_row.addWidget(export_btn)
        right_l.addLayout(filter_row)

        self.count_label = QLabel()
        self.count_label.setObjectName("mutedLabel")
        right_l.addWidget(self.count_label)
        self.email_list = QListWidget()
        self.email_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        right_l.addWidget(self.email_list)
        splitter.addWidget(right)
        splitter.setSizes([280, 720])
        root.addWidget(splitter)

        self._refresh_lists()
        self._refresh_emails()

    def bind_store(self, store: AudienceStore) -> None:
        self.store = store
        self.store.ensure_default()
        self.suppression.set_emails(self.store.suppression)
        self._refresh_lists()
        self._refresh_emails()

    def _current_list_name(self) -> str:
        item = self.list_picker.currentItem()
        if item:
            return item.text()
        return self.store.active_list

    def _refresh_lists(self) -> None:
        self.list_picker.blockSignals(True)
        self.list_picker.clear()
        for audience in self.store.lists:
            self.list_picker.addItem(audience.name)
        matches = self.list_picker.findItems(self.store.active_list, Qt.MatchFlag.MatchExactly)
        if matches:
            self.list_picker.setCurrentItem(matches[0])
        elif self.list_picker.count():
            self.list_picker.setCurrentRow(0)
        self.list_picker.blockSignals(False)

    def _on_list_selected(self, name: str) -> None:
        if not name:
            return
        self.store.active_list = name
        self._refresh_emails()
        self.changed.emit()

    def _refresh_emails(self) -> None:
        audience = self.store.get(self._current_list_name()) or self.store.ensure_default()
        query = self.filter_edit.text()
        emails = audience.filtered(query)
        self.email_list.clear()
        for email in emails:
            self.email_list.addItem(QListWidgetItem(email))
        effective = len(self.store.effective_recipients(audience.name))
        self.count_label.setText(
            f"{len(audience.emails)} in list · {effective} after suppression"
            + (f" · showing {len(emails)} filtered" if query else "")
        )

    def _sync_suppression(self) -> None:
        self.store.suppression = self.suppression.emails()
        self._refresh_emails()
        self.changed.emit()

    def _add_chips(self) -> None:
        audience = self.store.get_or_create(self._current_list_name())
        added, dupes = audience.add(self.chips.emails())
        self.chips.clear()
        self._refresh_emails()
        self.changed.emit()
        QMessageBox.information(
            self, "Audience", f"Added {added} address(es). {dupes} duplicate(s) skipped."
        )

    def _paste_extract(self) -> None:
        from PySide6.QtWidgets import QApplication

        text = QApplication.clipboard().text()
        if not text.strip():
            QMessageBox.information(self, "Paste", "Clipboard is empty.")
            return
        audience = self.store.get_or_create(self._current_list_name())
        result = extract_emails_from_text(text, existing=set(audience.emails))
        self._confirm_import(ImportPreview(result.found, result.duplicates, result.invalid_skipped))

    def _import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import audience",
            "",
            "Spreadsheets & text (*.csv *.xlsx *.xls *.txt);;All files (*)",
        )
        if not path:
            return
        audience = self.store.get_or_create(self._current_list_name())
        try:
            result = extract_emails_from_file(Path(path), existing=set(audience.emails))
        except Exception as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        self._confirm_import(ImportPreview(result.found, result.duplicates, result.invalid_skipped))

    def _confirm_import(self, preview: ImportPreview) -> None:
        msg = (
            f"Found {len(preview.found)} new address(es).\n"
            f"Duplicates: {len(preview.duplicates)}\n"
            f"Invalid skipped: {len(preview.invalid_skipped)}\n\n"
            "Add the new addresses to the current list?"
        )
        if QMessageBox.question(self, "Import preview", msg) != QMessageBox.StandardButton.Yes:
            return
        audience = self.store.get_or_create(self._current_list_name())
        audience.add(preview.found)
        self._refresh_emails()
        self.changed.emit()

    def _select_all(self) -> None:
        self.email_list.selectAll()

    def _remove_selected(self) -> None:
        selected = [i.text() for i in self.email_list.selectedItems()]
        if not selected:
            return
        if (
            QMessageBox.question(
                self, "Remove", f"Remove {len(selected)} address(es) from this list?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        audience = self.store.get(self._current_list_name())
        if audience:
            audience.remove(selected)
            self._refresh_emails()
            self.changed.emit()

    def _export_csv(self) -> None:
        audience = self.store.get(self._current_list_name())
        if not audience:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"{audience.name}.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["email"])
            for email in audience.emails:
                writer.writerow([email])
        QMessageBox.information(self, "Export", f"Wrote {len(audience.emails)} rows.")

    def _new_list(self) -> None:
        name, ok = QInputDialog.getText(self, "New list", "List name:")
        if not ok or not name.strip():
            return
        if self.store.get(name.strip()):
            QMessageBox.warning(self, "New list", "A list with that name already exists.")
            return
        self.store.get_or_create(name.strip())
        self.store.active_list = name.strip()
        self._refresh_lists()
        self._refresh_emails()
        self.changed.emit()

    def _rename_list(self) -> None:
        old = self._current_list_name()
        name, ok = QInputDialog.getText(self, "Rename list", "New name:", text=old)
        if not ok or not name.strip():
            return
        if not self.store.rename(old, name.strip()):
            QMessageBox.warning(self, "Rename", "Could not rename (name taken?).")
            return
        self._refresh_lists()
        self.changed.emit()

    def _delete_list(self) -> None:
        name = self._current_list_name()
        if (
            QMessageBox.question(self, "Delete list", f"Delete list “{name}”?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        if not self.store.delete(name):
            QMessageBox.warning(self, "Delete list", "Keep at least one audience list.")
            return
        self._refresh_lists()
        self._refresh_emails()
        self.changed.emit()
