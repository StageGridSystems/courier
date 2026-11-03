"""Compose and send tab."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from courier.auth.oauth import AuthManager
from courier.composer.draft import Draft, Template
from courier.composer.html_text import html_to_plain_text
from courier.sender.gmail_send import GMAIL_ATTACHMENT_LIMIT, total_attachment_size
from courier.sender.queue import SendQueue, SendResult, export_results_csv
from courier.sender.rate_limit import RateLimiter, estimate_send_seconds, format_duration
from courier.storage.config import AppSettings, AppState, SendJobState
from courier.ui.widgets.chip_field import ChipField


class ConfirmSendDialog(QDialog):
    choice = "cancel"

    def __init__(
        self,
        *,
        count: int,
        subject: str,
        estimate: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Are you sure?")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Recipients: <b>{count}</b>"))
        layout.addWidget(QLabel(f"Subject: <b>{subject or '(empty)'}</b>"))
        layout.addWidget(QLabel(f"Estimated time: <b>{estimate}</b>"))
        layout.addWidget(
            QLabel("Each person gets their own message. The list is never exposed in To/CC.")
        )
        buttons = QDialogButtonBox()
        cancel = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        preview = buttons.addButton("Show preview first", QDialogButtonBox.ButtonRole.ActionRole)
        test = buttons.addButton(
            "Send to test audience first", QDialogButtonBox.ButtonRole.ActionRole
        )
        send_all = buttons.addButton("Send to all", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel.clicked.connect(lambda: self._pick("cancel"))
        preview.clicked.connect(lambda: self._pick("preview"))
        test.clicked.connect(lambda: self._pick("test"))
        send_all.clicked.connect(lambda: self._pick("all"))
        layout.addWidget(buttons)

    def _pick(self, choice: str) -> None:
        self.choice = choice
        if choice == "cancel":
            self.reject()
        else:
            self.accept()


class _SendWorker(QThread):
    progress = Signal(int, int, object)
    checkpoint = Signal(dict)
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, queue: SendQueue, kwargs: dict[str, Any]) -> None:
        super().__init__()
        self.queue = queue
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            results = self.queue.run(
                self.kwargs["recipients"],
                subject=self.kwargs["subject"],
                html_body=self.kwargs["html_body"],
                text_body=self.kwargs["text_body"],
                from_name=self.kwargs.get("from_name", ""),
                reply_to=self.kwargs.get("reply_to", ""),
                cc=self.kwargs.get("cc"),
                bcc=self.kwargs.get("bcc"),
                attachments=self.kwargs.get("attachments"),
                already_completed=self.kwargs.get("already_completed"),
                on_progress=lambda d, t, r: self.progress.emit(d, t, r),
                on_checkpoint=lambda c: self.checkpoint.emit(c),
                job_id=self.kwargs.get("job_id"),
            )
            self.finished_ok.emit(results)
        except Exception as exc:
            self.failed.emit(str(exc))


class ComposeTab(QWidget):
    state_changed = Signal()

    def __init__(
        self,
        state: AppState,
        auth: AuthManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = state
        self.auth = auth
        self._attachments: list[str] = []
        self._worker: _SendWorker | None = None
        self._queue: SendQueue | None = None
        self._results: list[SendResult] = []
        self._send_lock = False

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        title = QLabel("Compose / Send")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        form = QFormLayout()
        self.subject = QLineEdit()
        self.from_name = QLineEdit()
        self.reply_to = QLineEdit()
        self.cc_field = ChipField()
        self.bcc_field = ChipField()
        form.addRow("Subject", self.subject)
        form.addRow("From display name", self.from_name)
        form.addRow("Reply-To", self.reply_to)
        form.addRow("CC (optional)", self.cc_field)
        form.addRow("BCC (optional)", self.bcc_field)
        root.addLayout(form)

        splitter = QSplitter()
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.addWidget(QLabel("HTML body (merge fields: {{email}})"))
        self.html_edit = QTextEdit()
        self.html_edit.setPlaceholderText("<p>Hello {{email}},</p>")
        self.html_edit.textChanged.connect(self._on_html_changed)
        left_l.addWidget(self.html_edit)
        self.auto_text = QCheckBox("Auto-generate plain text from HTML")
        self.auto_text.setChecked(True)
        self.auto_text.toggled.connect(self._on_html_changed)
        left_l.addWidget(self.auto_text)
        left_l.addWidget(QLabel("Plain-text alternative"))
        self.text_edit = QPlainTextEdit()
        left_l.addWidget(self.text_edit)
        splitter.addWidget(left)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.addWidget(QLabel("Live preview"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        right_l.addWidget(self.preview)
        splitter.addWidget(right)
        root.addWidget(splitter, stretch=1)

        att_row = QHBoxLayout()
        self.att_label = QLabel("Attachments: none")
        self.att_label.setObjectName("mutedLabel")
        add_att = QPushButton("Add attachments…")
        add_att.clicked.connect(self._add_attachments)
        clear_att = QPushButton("Clear")
        clear_att.clicked.connect(self._clear_attachments)
        att_row.addWidget(self.att_label, stretch=1)
        att_row.addWidget(add_att)
        att_row.addWidget(clear_att)
        root.addLayout(att_row)
        self.setAcceptDrops(True)

        draft_row = QHBoxLayout()
        save_draft = QPushButton("Save draft")
        save_draft.clicked.connect(self._save_draft)
        load_draft = QPushButton("Load draft…")
        load_draft.clicked.connect(self._load_draft)
        save_tpl = QPushButton("Save template")
        save_tpl.clicked.connect(self._save_template)
        load_tpl = QPushButton("Load template…")
        load_tpl.clicked.connect(self._load_template)
        for b in (save_draft, load_draft, save_tpl, load_tpl):
            draft_row.addWidget(b)
        draft_row.addStretch()
        root.addLayout(draft_row)

        send_row = QHBoxLayout()
        self.test_btn = QPushButton("Send test to admins")
        self.test_btn.clicked.connect(lambda: self._start_send(mode="test"))
        self.send_btn = QPushButton("Send to audience")
        self.send_btn.setObjectName("primaryButton")
        self.send_btn.clicked.connect(lambda: self._start_send(mode="audience"))
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._pause)
        self.resume_btn = QPushButton("Resume")
        self.resume_btn.clicked.connect(self._resume)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.clicked.connect(self._cancel)
        export_btn = QPushButton("Export results CSV")
        export_btn.clicked.connect(self._export_results)
        for b in (
            self.test_btn,
            self.send_btn,
            self.pause_btn,
            self.resume_btn,
            self.cancel_btn,
            export_btn,
        ):
            send_row.addWidget(b)
        send_row.addStretch()
        root.addLayout(send_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        root.addWidget(self.progress)
        self.log = QListWidget()
        self.log.setMaximumHeight(120)
        root.addWidget(self.log)

        self.from_name.setText(self.state.settings.from_display_name)
        self.reply_to.setText(self.state.settings.reply_to)
        self._maybe_resume_job()

    def bind_state(self, state: AppState) -> None:
        self.state = state
        self.from_name.setText(self.state.settings.from_display_name)
        self.reply_to.setText(self.state.settings.reply_to)

    def dragEnterEvent(self, event: Any) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self._attachments.append(path)
        self._update_att_label()

    def _on_html_changed(self) -> None:
        html = self.html_edit.toHtml() if False else self.html_edit.toPlainText()
        # Prefer plain editor content as HTML source the user typed
        raw = self.html_edit.toPlainText()
        self.preview.setHtml(raw)
        if self.auto_text.isChecked():
            self.text_edit.setPlainText(html_to_plain_text(raw))
        _ = html

    def _add_attachments(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Attachments")
        self._attachments.extend(files)
        self._update_att_label()

    def _clear_attachments(self) -> None:
        self._attachments.clear()
        self._update_att_label()

    def _update_att_label(self) -> None:
        size = total_attachment_size(self._attachments)
        mb = size / (1024 * 1024)
        limit_mb = GMAIL_ATTACHMENT_LIMIT / (1024 * 1024)
        names = ", ".join(Path(p).name for p in self._attachments) or "none"
        warn = "  (over Gmail 25 MB limit!)" if size > GMAIL_ATTACHMENT_LIMIT - 100_000 else ""
        self.att_label.setText(f"Attachments ({mb:.1f}/{limit_mb:.0f} MB): {names}{warn}")

    def _compose_html(self) -> str:
        body = self.html_edit.toPlainText()
        if self.state.settings.default_footer_enabled and self.state.settings.default_footer_html:
            if "UNSUBSCRIBE" not in body.upper():
                body = body + "\n" + self.state.settings.default_footer_html
        return body

    def _save_draft(self) -> None:
        draft = Draft(
            name=self.subject.text() or "Untitled draft",
            subject=self.subject.text(),
            html_body=self.html_edit.toPlainText(),
            text_body=self.text_edit.toPlainText(),
            from_name=self.from_name.text(),
            reply_to=self.reply_to.text(),
            cc=self.cc_field.emails(),
            bcc=self.bcc_field.emails(),
            attachments=list(self._attachments),
        )
        self.state.drafts = [d for d in self.state.drafts if d.name != draft.name] + [draft]
        self.state_changed.emit()
        QMessageBox.information(self, "Draft", f"Saved draft “{draft.name}”.")

    def _load_draft(self) -> None:
        if not self.state.drafts:
            QMessageBox.information(self, "Drafts", "No drafts saved yet.")
            return
        names = [d.name for d in self.state.drafts]
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getItem(self, "Load draft", "Draft:", names, 0, False)
        if not ok:
            return
        draft = next(d for d in self.state.drafts if d.name == name)
        self._apply_draft(draft)

    def _apply_draft(self, draft: Draft) -> None:
        self.subject.setText(draft.subject)
        self.html_edit.setPlainText(draft.html_body)
        self.text_edit.setPlainText(draft.text_body)
        self.from_name.setText(draft.from_name)
        self.reply_to.setText(draft.reply_to)
        self.cc_field.set_emails(draft.cc)
        self.bcc_field.set_emails(draft.bcc)
        self._attachments = list(draft.attachments)
        self._update_att_label()

    def _save_template(self) -> None:
        tpl = Template(
            name=self.subject.text() or "Untitled template",
            subject=self.subject.text(),
            html_body=self.html_edit.toPlainText(),
            text_body=self.text_edit.toPlainText(),
        )
        self.state.templates = [t for t in self.state.templates if t.name != tpl.name] + [tpl]
        self.state_changed.emit()
        QMessageBox.information(self, "Template", f"Saved template “{tpl.name}”.")

    def _load_template(self) -> None:
        if not self.state.templates:
            QMessageBox.information(self, "Templates", "No templates saved yet.")
            return
        from PySide6.QtWidgets import QInputDialog

        names = [t.name for t in self.state.templates]
        name, ok = QInputDialog.getItem(self, "Load template", "Template:", names, 0, False)
        if not ok:
            return
        tpl = next(t for t in self.state.templates if t.name == name)
        self.subject.setText(tpl.subject)
        self.html_edit.setPlainText(tpl.html_body)
        self.text_edit.setPlainText(tpl.text_body)

    def _start_send(self, mode: str) -> None:
        if self._send_lock or (self._worker and self._worker.isRunning()):
            QMessageBox.warning(self, "Sending", "A send job is already running.")
            return
        if not self.auth.is_connected and not self.state.settings.dry_run:
            QMessageBox.warning(self, "Not connected", "Sign in on the Authentication tab first.")
            return
        subject = self.subject.text().strip()
        if not subject:
            QMessageBox.warning(self, "Subject", "Subject is required.")
            return
        html = self._compose_html()
        text = self.text_edit.toPlainText()
        if not html.strip() and not text.strip():
            QMessageBox.warning(self, "Body", "Write an HTML or plain-text body.")
            return
        if total_attachment_size(self._attachments) > GMAIL_ATTACHMENT_LIMIT - 100_000:
            QMessageBox.warning(self, "Attachments", "Attachments exceed Gmail’s ~25 MB limit.")
            return

        settings: AppSettings = self.state.settings
        if mode == "test":
            recipients = list(settings.test_audience)
            if not recipients:
                QMessageBox.warning(
                    self, "Test audience", "Add admin emails under Settings → Test audience."
                )
                return
            self._launch_queue(recipients, subject, html, text, job_label="test")
            return

        recipients = self.state.audiences.effective_recipients()
        if not recipients:
            QMessageBox.warning(self, "Audience", "No recipients after suppression.")
            return
        estimate = format_duration(
            estimate_send_seconds(len(recipients), settings.send_interval_seconds)
        )
        dlg = ConfirmSendDialog(
            count=len(recipients), subject=subject, estimate=estimate, parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if dlg.choice == "preview":
            sample = recipients[0]
            from courier.composer.merge import apply_merge_fields

            preview_html = apply_merge_fields(html, {"email": sample})
            QMessageBox.information(
                self,
                "Preview",
                f"To: {sample}\nSubject: {apply_merge_fields(subject, {'email': sample})}\n\n"
                f"{html_to_plain_text(preview_html)[:1500]}",
            )
            return
        if dlg.choice == "test":
            recipients = list(settings.test_audience)
            if not recipients:
                QMessageBox.warning(self, "Test audience", "No test audience configured.")
                return
            self._launch_queue(recipients, subject, html, text, job_label="test")
            return
        if dlg.choice == "all":
            self._launch_queue(recipients, subject, html, text, job_label="audience")

    def _launch_queue(
        self,
        recipients: list[str],
        subject: str,
        html: str,
        text: str,
        *,
        job_label: str,
        already_completed: list[str] | None = None,
        job_id: str | None = None,
    ) -> None:
        self._send_lock = True
        self.test_btn.setEnabled(False)
        self.send_btn.setEnabled(False)
        limiter = RateLimiter(
            interval_seconds=self.state.settings.send_interval_seconds,
            daily_cap=self.state.settings.daily_cap,
        )
        sender_email = self.auth.email or "me@example.com"
        self._queue = SendQueue(
            service_factory=self.auth.build_gmail_service,
            sender_email=sender_email,
            rate_limiter=limiter,
            dry_run=self.state.settings.dry_run,
        )
        jid = job_id or uuid4().hex
        self.state.send_job = SendJobState(
            active=True,
            job_id=jid,
            subject=subject,
            recipients=list(recipients),
            completed=list(already_completed or []),
            html_body=html,
            text_body=text,
            from_name=self.from_name.text(),
            reply_to=self.reply_to.text(),
            cc=self.cc_field.emails(),
            bcc=self.bcc_field.emails(),
            attachments=list(self._attachments),
            started_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        )
        self.state_changed.emit()
        self.progress.setMaximum(len(recipients))
        self.progress.setValue(len(already_completed or []))
        self.log.addItem(f"Starting {job_label} send to {len(recipients)} recipient(s)…")

        kwargs = {
            "recipients": recipients,
            "subject": subject,
            "html_body": html,
            "text_body": text,
            "from_name": self.from_name.text(),
            "reply_to": self.reply_to.text(),
            "cc": self.cc_field.emails(),
            "bcc": self.bcc_field.emails(),
            "attachments": list(self._attachments),
            "already_completed": already_completed,
            "job_id": jid,
        }
        self._worker = _SendWorker(self._queue, kwargs)
        self._worker.progress.connect(self._on_progress)
        self._worker.checkpoint.connect(self._on_checkpoint)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, done: int, total: int, result: object) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        if isinstance(result, SendResult):
            self.log.addItem(f"{result.status}: {result.email} ({result.detail})")
            self.log.scrollToBottom()

    def _on_checkpoint(self, data: dict) -> None:
        job = self.state.send_job
        job.completed = list(data.get("completed") or [])
        self.state_changed.emit()

    def _on_finished(self, results: list) -> None:
        self._results = list(results)
        self.state.send_log.extend(
            [{"email": r.email, "status": r.status, "detail": r.detail, "at": r.at} for r in results]
        )
        self.state.send_job.active = False
        self.state.send_job.completed = [r.email for r in results if r.status == "sent"]
        self._send_lock = False
        self.test_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.state_changed.emit()
        sent = sum(1 for r in results if r.status == "sent")
        QMessageBox.information(self, "Send complete", f"Finished. {sent} sent.")

    def _on_failed(self, message: str) -> None:
        self._send_lock = False
        self.test_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.state.send_job.active = False
        self.state_changed.emit()
        QMessageBox.warning(self, "Send failed", message)

    def _pause(self) -> None:
        if self._queue:
            self._queue.pause()
            self.state.send_job.paused = True
            self.log.addItem("Paused")

    def _resume(self) -> None:
        if self._queue:
            self._queue.resume()
            self.state.send_job.paused = False
            self.log.addItem("Resumed")

    def _cancel(self) -> None:
        if self._queue:
            self._queue.cancel()
            self.log.addItem("Cancel requested…")

    def _export_results(self) -> None:
        if not self._results and not self.state.send_log:
            QMessageBox.information(self, "Results", "No results yet.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export results", "send_results.csv", "CSV (*.csv)")
        if not path:
            return
        if self._results:
            export_results_csv(self._results, Path(path))
        else:
            import csv

            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=["email", "status", "detail", "at"])
                writer.writeheader()
                for row in self.state.send_log:
                    writer.writerow(row)
        QMessageBox.information(self, "Export", "Results exported.")

    def _maybe_resume_job(self) -> None:
        job = self.state.send_job
        if not job.active or not job.recipients:
            return
        remaining = [e for e in job.recipients if e.lower() not in {c.lower() for c in job.completed}]
        if not remaining:
            job.active = False
            return
        reply = QMessageBox.question(
            self,
            "Resume send?",
            f"A previous send was interrupted ({len(job.completed)} done, "
            f"{len(remaining)} remaining). Resume?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            job.active = False
            return
        self.subject.setText(job.subject)
        self.html_edit.setPlainText(job.html_body)
        self.text_edit.setPlainText(job.text_body)
        self.from_name.setText(job.from_name)
        self.reply_to.setText(job.reply_to)
        self.cc_field.set_emails(job.cc)
        self.bcc_field.set_emails(job.bcc)
        self._attachments = list(job.attachments)
        self._update_att_label()
        self._launch_queue(
            job.recipients,
            job.subject,
            job.html_body,
            job.text_body,
            job_label="resume",
            already_completed=job.completed,
            job_id=job.job_id,
        )
