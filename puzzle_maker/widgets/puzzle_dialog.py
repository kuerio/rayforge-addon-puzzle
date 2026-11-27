"""The "Create Puzzle" dialog.

Collects the parameters, keeps a live cairo preview in sync, and hands
the result to a callback. Validation lives in
:class:`~puzzle_maker.core.jigsaw.PuzzleParams`, so out-of-range values
are reported instead of silently clamped.
"""

from __future__ import annotations

from gettext import gettext as _
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from .. import preferences  # noqa: E402
from ..core.jigsaw import PuzzleParams  # noqa: E402
from ..core.svg import write_puzzle_svg  # noqa: E402
from .preview import PuzzlePreview  # noqa: E402

__all__ = ["PuzzleDialog"]

#: ``on_accept(params, with_contour)``
AcceptCallback = Callable[[PuzzleParams, bool], None]


def _spin_row(
    title: str,
    subtitle: str,
    value: float,
    lower: float,
    upper: float,
    step: float,
    digits: int,
) -> Adw.SpinRow:
    adjustment = Gtk.Adjustment(
        value=value,
        lower=lower,
        upper=upper,
        step_increment=step,
        page_increment=step * 10.0,
    )
    row = Adw.SpinRow.new(adjustment, step, digits)
    row.set_title(title)
    row.set_subtitle(subtitle)
    row.set_numeric(True)
    return row


class PuzzleDialog(Adw.Window):
    """Parameter dialog with a live preview."""

    def __init__(
        self,
        parent: Gtk.Window,
        on_accept: AcceptCallback,
        params: PuzzleParams | None = None,
    ) -> None:
        super().__init__()
        self._on_accept = on_accept
        # Start from the last used values so the dialog does not reset to
        # the built-in defaults every time.
        self._build(params or preferences.load())

        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title(_("Create Puzzle"))
        self.set_default_size(620, 820)

    # -- construction -------------------------------------------------
    def _build(self, params: PuzzleParams) -> None:
        self._preview = PuzzlePreview(params)

        self._width = _spin_row(
            _("Width"), _("in mm"), params.width_mm, 5, 3000, 5, 1
        )
        self._height = _spin_row(
            _("Height"), _("in mm"), params.height_mm, 5, 3000, 5, 1
        )
        self._columns = _spin_row(
            _("Columns"), _("pieces across"), params.columns, 1, 40, 1, 0
        )
        self._rows = _spin_row(
            _("Rows"), _("pieces up"), params.rows, 1, 40, 1, 0
        )
        self._seed = _spin_row(
            _("Seed"),
            _("same seed, same puzzle"),
            params.seed,
            0,
            999999,
            1,
            0,
        )
        self._tab_size = _spin_row(
            _("Tab size"),
            _("percent of a cell edge"),
            params.tab_size_percent,
            5,
            60,
            1,
            0,
        )
        self._jitter = _spin_row(
            _("Jitter"),
            _("randomness, in percent"),
            params.jitter_percent,
            0,
            45,
            1,
            0,
        )
        self._radius = _spin_row(
            _("Corner radius"),
            _("rounded outer corners, in mm"),
            params.border_radius_mm,
            0,
            100,
            1,
            1,
        )
        self._with_contour = Adw.SwitchRow(
            title=_("Add a Contour step"),
            subtitle=_("so the puzzle is directly cuttable"),
        )
        self._with_contour.set_active(True)

        self._error = Gtk.Label(wrap=True, xalign=0)
        self._error.add_css_class("error")
        self._error.set_visible(False)

        page = Adw.PreferencesPage()

        size_group = Adw.PreferencesGroup(
            title=_("Puzzle"),
            description=_("Size on the material and the number of pieces."),
        )
        for row in (
            self._width,
            self._height,
            self._columns,
            self._rows,
            self._seed,
        ):
            size_group.add(row)

        tab_group = Adw.PreferencesGroup(
            title=_("Tabs"),
            description=_("Shape of the interlocking tabs."),
        )
        for row in (self._tab_size, self._jitter, self._radius):
            tab_group.add(row)

        option_group = Adw.PreferencesGroup(title=_("Workflow"))
        option_group.add(self._with_contour)
        option_group.add(self._error)

        preview_group = Adw.PreferencesGroup(title=_("Preview"))
        frame = Gtk.Frame()
        frame.set_child(self._preview)
        frame.set_vexpand(True)
        preview_group.add(frame)

        page.add(size_group)
        page.add(tab_group)
        page.add(option_group)
        page.add(preview_group)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(self._header_bar())
        toolbar.set_content(page)
        self.set_content(toolbar)

        for row in self._parameter_rows():
            row.connect("notify::value", self._on_changed)
        self.connect("close-request", self._on_close_request)

    def _header_bar(self) -> Adw.HeaderBar:
        bar = Adw.HeaderBar()
        reset = Gtk.Button(label=_("Reset"))
        reset.set_tooltip_text(_("Back to the built-in defaults"))
        reset.connect("clicked", self._on_reset_clicked)
        bar.pack_start(reset)

        save = Gtk.Button(label=_("Save SVG…"))
        save.connect("clicked", self._on_save_clicked)
        bar.pack_start(save)

        accept = Gtk.Button(label=_("Add to Document"))
        accept.add_css_class("suggested-action")
        accept.connect("clicked", self._on_accept_clicked)
        bar.pack_end(accept)
        return bar

    def _parameter_rows(self) -> list[Adw.SpinRow]:
        return [
            self._width,
            self._height,
            self._columns,
            self._rows,
            self._seed,
            self._tab_size,
            self._jitter,
            self._radius,
        ]

    def _apply_params(self, params: PuzzleParams) -> None:
        """Write *params* into the rows (used by Reset)."""
        self._width.set_value(params.width_mm)
        self._height.set_value(params.height_mm)
        self._columns.set_value(params.columns)
        self._rows.set_value(params.rows)
        self._seed.set_value(params.seed)
        self._tab_size.set_value(params.tab_size_percent)
        self._jitter.set_value(params.jitter_percent)
        self._radius.set_value(params.border_radius_mm)
        self._preview.set_params(params)

    def _remember(self) -> None:
        """Store the current values for the next time the dialog opens."""
        params = self.current_params()
        if params is not None:
            preferences.save(params)

    # -- state --------------------------------------------------------
    def current_params(self) -> PuzzleParams | None:
        """The parameters, or None (and an error shown) when invalid."""
        try:
            params = PuzzleParams(
                width_mm=self._width.get_value(),
                height_mm=self._height.get_value(),
                columns=int(self._columns.get_value()),
                rows=int(self._rows.get_value()),
                tab_size_percent=self._tab_size.get_value(),
                jitter_percent=self._jitter.get_value(),
                seed=int(self._seed.get_value()),
                border_radius_mm=self._radius.get_value(),
            )
        except ValueError as error:
            self._show_error(str(error))
            return None
        self._clear_error()
        return params

    def _on_changed(self, *_args) -> None:
        params = self.current_params()
        if params is not None:
            self._preview.set_params(params)

    def _show_error(self, message: str) -> None:
        self._error.set_text(message)
        self._error.set_visible(True)

    def _clear_error(self) -> None:
        if self._error.get_visible():
            self._error.set_visible(False)

    # -- callbacks ----------------------------------------------------
    def _on_accept_clicked(self, _button: Gtk.Button) -> None:
        params = self.current_params()
        if params is None:
            return
        self._remember()
        self._on_accept(params, self._with_contour.get_active())

    def _on_reset_clicked(self, _button: Gtk.Button) -> None:
        """Back to the built-in defaults, and forget the stored ones."""
        preferences.clear()
        self._apply_params(PuzzleParams())
        self._on_changed()

    def _on_close_request(self, _window) -> bool:
        """Remember what was on screen, even without adding a puzzle."""
        self._remember()
        return False

    def _on_save_clicked(self, _button: Gtk.Button) -> None:
        params = self.current_params()
        if params is None:
            return
        self._remember()
        if not hasattr(Gtk, "FileDialog"):
            self._show_error(_("Saving needs GTK 4.10 or newer."))
            return
        dialog = Gtk.FileDialog()
        dialog.set_title(_("Save puzzle as SVG"))
        dialog.set_initial_name(f"puzzle-{params.columns}x{params.rows}.svg")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        svg_filter = Gtk.FileFilter()
        svg_filter.set_name(_("SVG files"))
        svg_filter.add_suffix("svg")
        filters.append(svg_filter)
        dialog.set_filters(filters)
        dialog.save(self, None, self._on_save_finished, params)

    def _on_save_finished(
        self, dialog: Gtk.FileDialog, result, params: PuzzleParams
    ) -> None:
        try:
            file = dialog.save_finish(result)
        except Exception:  # user cancelled or no portal available
            return
        if file is None:
            return
        target = file.get_path()
        if not target:
            return
        try:
            write_puzzle_svg(target, params)
        except OSError as error:
            self._show_error(str(error))
            return
        self._clear_error()
