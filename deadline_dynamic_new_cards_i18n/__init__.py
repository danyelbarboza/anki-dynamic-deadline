# Dynamic Deadline New Cards
# Add-on for Anki Desktop.
# Automatically adjusts a deck's new cards/day limit based on a deadline.

from __future__ import annotations

import math
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from anki.utils import ids2str
from aqt import gui_hooks, mw
from aqt.qt import *
from aqt.utils import qconnect, showInfo, showWarning, tooltip

try:
    from anki import hooks as anki_hooks
except Exception:  # pragma: no cover - fallback for uncommon versions
    anki_hooks = None

ADDON_NAME = "Dynamic Deadline New Cards"

DEFAULT_CONFIG = {
    "decks": {},
    "language": "en",
    "rounding": "ceil",
    "minimum_new_per_day": 0,
    "show_tooltips_on_auto_update": False,
}

LANGUAGES = [
    ("en", "English"),
    ("pt_BR", "Português"),
]

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "addon_title": "Dynamic Deadline New Cards",
        "menu_configure": "Dynamic Deadline: Configure...",
        "menu_recalculate": "Dynamic Deadline: Recalculate now",
        "intro": (
            "Configure a deadline for each deck. The add-on calculates: "
            "remaining new cards ÷ remaining days, then updates New cards/day."
        ),
        "language_label": "Language:",
        "deck_label": "Deck:",
        "status_label": "Status:",
        "deadline_label": "Deadline:",
        "adjustment_label": "Margin above/below exact pace:",
        "counting_label": "Counting:",
        "preview_label": "Preview:",
        "enable_checkbox": "Enable dynamic deadline for this deck",
        "include_subdecks_checkbox": "Include subdecks in the count",
        "adjustment_tooltip": (
            "0% = exact pace to clear the deck by the deadline. "
            "+20% = do 20% more per day and likely finish earlier. "
            "-10% = do 10% less per day and likely finish later."
        ),
        "save_button": "Save and recalculate",
        "recalculate_button": "Recalculate all",
        "disable_button": "Disable for this deck",
        "close_button": "Close",
        "note": (
            "Note: this add-on does not create or rename presets. It changes the "
            "'New cards/day' limit in the selected deck's 'This deck' section."
        ),
        "no_deck_selected": "No deck selected.",
        "preview_no_estimate": "Estimate: cannot estimate completion with a daily limit of 0.",
        "preview_already_clear": "Estimate: this deck already has no remaining new cards.",
        "preview_finish": "Estimate: finishes in about {days_to_finish} {day_word}, around {finish_date} ({relation}).",
        "preview_text": (
            "Remaining new cards: {new_cards}.\n"
            "Exact pace: {exact_daily:.2f} cards/day for {days} {day_word}.\n"
            "Margin: {adjustment}.\n"
            "Limit that will be saved: {limit} new cards per day.\n"
            "{finish_line}"
        ),
        "preview_error": "Could not calculate the preview: {error}",
        "select_deck_warning": "Select a deck.",
        "saved_info": (
            "Saved.\n\n"
            "{deck_name}\n"
            "Remaining new cards: {new_cards}\n"
            "Remaining days: {days}\n"
            "Exact pace: {exact_daily:.2f} cards/day\n"
            "Margin: {adjustment}\n"
            "New daily limit in 'This deck': {new_limit}"
            "{finish_text}"
        ),
        "finish_text": "\nEstimated completion: {finish_date} ({relation})",
        "saved_but_problem": "Configuration saved, but there was a problem recalculating: {result}",
        "disabled_info": "Deadline disabled for this deck.",
        "disabled_keep_limit": (
            "Disabled for this deck. The current 'This deck' limit was kept; "
            "change it manually in Deck Options if you want another value."
        ),
        "open_profile_warning": "Open a profile/collection before configuring the add-on.",
        "no_active_deadlines": "No deck with an active deadline was found.",
        "tooltip_updated": "{addon_title}: limits updated.",
        "recalc_error": "Error while recalculating deadlines:\n{error}",
        "manual_result_line": (
            "{deck_name}: {new_cards} new / {days} {day_word}, margin {adjustment} "
            "= {new_limit} new cards per day{finish_text}"
        ),
        "manual_finish_suffix": "; estimate: {finish_date} ({relation})",
        "error_invalid_deadline": "invalid deadline",
        "error_deck_not_found": "deck not found",
        "error_filtered_deck": "filtered deck or unavailable deck",
        "fallback_deck_name": "Deck {deck_id}",
        "before_deadline": "{n} {day_word} before the deadline",
        "after_deadline": "{n} {day_word} after the deadline",
        "on_deadline": "on the deadline",
    },
    "pt_BR": {
        "addon_title": "Deadline Dinâmico - Novos por Dia",
        "menu_configure": "Deadline dinâmico: configurar...",
        "menu_recalculate": "Deadline dinâmico: recalcular agora",
        "intro": (
            "Configure um deadline por baralho. O add-on calcula: "
            "cards novos restantes ÷ dias restantes, e atualiza Novos/dia."
        ),
        "language_label": "Idioma:",
        "deck_label": "Baralho:",
        "status_label": "Status:",
        "deadline_label": "Deadline:",
        "adjustment_label": "Margem acima/abaixo do ritmo exato:",
        "counting_label": "Contagem:",
        "preview_label": "Prévia:",
        "enable_checkbox": "Ativar deadline dinâmico para este baralho",
        "include_subdecks_checkbox": "Incluir subbaralhos na contagem",
        "adjustment_tooltip": (
            "0% = ritmo exato para zerar no deadline. "
            "+20% = fazer 20% a mais por dia e provavelmente terminar antes. "
            "-10% = fazer 10% a menos por dia e provavelmente terminar depois."
        ),
        "save_button": "Salvar e recalcular",
        "recalculate_button": "Recalcular todos",
        "disable_button": "Desativar neste baralho",
        "close_button": "Fechar",
        "note": (
            "Observação: o add-on não cria nem renomeia presets. Ele altera o limite "
            "'Novos cartões/dia' na aba 'Esse baralho' do baralho selecionado."
        ),
        "no_deck_selected": "Nenhum baralho selecionado.",
        "preview_no_estimate": "Previsão: não dá para estimar término com limite diário 0.",
        "preview_already_clear": "Previsão: este baralho já está zerado em cards novos.",
        "preview_finish": "Previsão: termina em aproximadamente {days_to_finish} {day_word}, por volta de {finish_date} ({relation}).",
        "preview_text": (
            "Novos restantes: {new_cards}.\n"
            "Ritmo exato: {exact_daily:.2f} cards/dia por {days} {day_word}.\n"
            "Margem: {adjustment}.\n"
            "Limite que será gravado: {limit} cards novos por dia.\n"
            "{finish_line}"
        ),
        "preview_error": "Não consegui calcular a prévia: {error}",
        "select_deck_warning": "Selecione um baralho.",
        "saved_info": (
            "Salvo.\n\n"
            "{deck_name}\n"
            "Novos restantes: {new_cards}\n"
            "Dias restantes: {days}\n"
            "Ritmo exato: {exact_daily:.2f} cards/dia\n"
            "Margem: {adjustment}\n"
            "Novo limite diário em 'Esse baralho': {new_limit}"
            "{finish_text}"
        ),
        "finish_text": "\nPrevisão de término: {finish_date} ({relation})",
        "saved_but_problem": "Configuração salva, mas houve problema ao recalcular: {result}",
        "disabled_info": "Deadline desativado para este baralho.",
        "disabled_keep_limit": (
            "Desativado para este baralho. O limite atual em 'Esse baralho' foi mantido; "
            "altere manualmente nas Opções do baralho se quiser outro valor."
        ),
        "open_profile_warning": "Abra um perfil/coleção antes de configurar o add-on.",
        "no_active_deadlines": "Nenhum baralho com deadline ativo foi encontrado.",
        "tooltip_updated": "{addon_title}: limites atualizados.",
        "recalc_error": "Erro ao recalcular deadlines:\n{error}",
        "manual_result_line": (
            "{deck_name}: {new_cards} novos / {days} {day_word}, margem {adjustment} "
            "= {new_limit} novos por dia{finish_text}"
        ),
        "manual_finish_suffix": "; previsão: {finish_date} ({relation})",
        "error_invalid_deadline": "deadline inválido",
        "error_deck_not_found": "baralho não encontrado",
        "error_filtered_deck": "baralho filtrado ou indisponível",
        "fallback_deck_name": "Baralho {deck_id}",
        "before_deadline": "{n} {day_word} antes do deadline",
        "after_deadline": "{n} {day_word} depois do deadline",
        "on_deadline": "no próprio deadline",
    },
}

_update_timer: Optional[QTimer] = None
_hourly_timer: Optional[QTimer] = None
_updating_now = False
setup_action: Optional[QAction] = None
recalc_action: Optional[QAction] = None


def _col_available() -> bool:
    return bool(mw and getattr(mw, "col", None))


def _normalize_language(value: Any) -> str:
    lang = str(value or "en")
    return lang if lang in TRANSLATIONS else "en"


def _config_language(cfg: Optional[Dict[str, Any]] = None) -> str:
    if cfg is None:
        cfg = _load_config()
    return _normalize_language(cfg.get("language", "en"))


def _t(key: str, cfg: Optional[Dict[str, Any]] = None, lang: Optional[str] = None, **kwargs: Any) -> str:
    active_lang = _normalize_language(lang) if lang is not None else _config_language(cfg)
    text = TRANSLATIONS.get(active_lang, TRANSLATIONS["en"]).get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    try:
        return text.format(**kwargs)
    except Exception:
        return text


def _addon_title(cfg: Optional[Dict[str, Any]] = None, lang: Optional[str] = None) -> str:
    return _t("addon_title", cfg=cfg, lang=lang)


def _day_word(n: int, lang: Optional[str] = None, cfg: Optional[Dict[str, Any]] = None) -> str:
    active_lang = _normalize_language(lang) if lang is not None else _config_language(cfg)
    if active_lang == "pt_BR":
        return "dia" if int(n) == 1 else "dias"
    return "day" if int(n) == 1 else "days"


def _load_config() -> Dict[str, Any]:
    cfg = mw.addonManager.getConfig(__name__) if mw and mw.addonManager else None
    if not isinstance(cfg, dict):
        cfg = deepcopy(DEFAULT_CONFIG)
    cfg.setdefault("decks", {})
    cfg.setdefault("language", "en")
    cfg["language"] = _normalize_language(cfg.get("language", "en"))
    cfg.setdefault("rounding", "ceil")
    cfg.setdefault("minimum_new_per_day", 0)
    cfg.setdefault("show_tooltips_on_auto_update", False)
    return cfg


def _save_config(cfg: Dict[str, Any]) -> None:
    cfg["language"] = _normalize_language(cfg.get("language", "en"))
    mw.addonManager.writeConfig(__name__, cfg)


def _today() -> date:
    return date.today()


def _parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _format_date(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def _days_remaining(deadline: date) -> int:
    # If the deadline is tomorrow, 1 day remains. If it is today or already passed,
    # force 1 day so all remaining cards are put into the daily limit.
    return max(1, (deadline - _today()).days)


def _all_regular_decks() -> List[Tuple[str, int]]:
    if not _col_available():
        return []

    try:
        rows = mw.col.decks.all_names_and_ids(
            skip_empty_default=False,
            include_filtered=False,
        )
        return sorted([(row.name, int(row.id)) for row in rows], key=lambda x: x[0].lower())
    except TypeError:
        # Fallback for older versions.
        decks = []
        for deck in mw.col.decks.all():
            if not deck.get("dyn", False):
                decks.append((deck["name"], int(deck["id"])))
        return sorted(decks, key=lambda x: x[0].lower())


def _deck_name(deck_id: int) -> str:
    deck = mw.col.decks.get(deck_id, default=False)
    return deck["name"] if deck else _t("fallback_deck_name", deck_id=deck_id)


def _deck_ids_for_count(deck_id: int, include_subdecks: bool) -> List[int]:
    if include_subdecks:
        try:
            return [int(did) for did in mw.col.decks.deck_and_child_ids(deck_id)]
        except Exception:
            ids = [deck_id]
            ids.extend([int(child_id) for _name, child_id in mw.col.decks.children(deck_id)])
            return ids
    return [deck_id]


def _new_card_count(deck_id: int, include_subdecks: bool) -> int:
    dids = _deck_ids_for_count(deck_id, include_subdecks)
    if not dids:
        return 0

    # type=0 => cards never studied. queue=-1 => suspended; by default they do not
    # count toward the plan because they will not be shown while suspended.
    sql = f"""
        SELECT COUNT()
        FROM cards
        WHERE type = 0
          AND queue != -1
          AND did IN {ids2str(dids)}
    """
    return int(mw.col.db.scalar(sql) or 0)


def _adjustment_percent(entry: Dict[str, Any]) -> float:
    try:
        return float(entry.get("daily_adjustment_percent", 0) or 0)
    except Exception:
        return 0.0


def _exact_daily_cards(new_cards: int, days: int) -> float:
    if new_cards <= 0:
        return 0.0
    return float(new_cards) / max(1, days)


def _calculate_limit(
    new_cards: int,
    days: int,
    cfg: Dict[str, Any],
    adjustment_percent: float = 0.0,
) -> int:
    minimum = int(cfg.get("minimum_new_per_day", 0) or 0)
    if new_cards <= 0:
        return 0

    rounding = str(cfg.get("rounding", "ceil")).lower()
    multiplier = max(0.0, 1.0 + (float(adjustment_percent) / 100.0))
    raw = _exact_daily_cards(new_cards, days) * multiplier

    if rounding == "floor":
        limit = math.floor(raw)
    elif rounding == "round":
        limit = round(raw)
    else:
        limit = math.ceil(raw)

    return max(minimum, int(limit))


def _estimate_completion(new_cards: int, daily_limit: int) -> Optional[Tuple[int, date]]:
    if new_cards <= 0:
        return (0, _today())
    if daily_limit <= 0:
        return None

    days_to_finish = int(math.ceil(new_cards / max(1, daily_limit)))
    finish_date = date.fromordinal(_today().toordinal() + max(0, days_to_finish - 1))
    return days_to_finish, finish_date


def _finish_relation_text(
    finish_date: date,
    deadline: date,
    cfg: Optional[Dict[str, Any]] = None,
    lang: Optional[str] = None,
) -> str:
    active_lang = _normalize_language(lang) if lang is not None else _config_language(cfg)
    diff = (finish_date - deadline).days
    if diff < 0:
        n = abs(diff)
        return _t("before_deadline", cfg=cfg, lang=active_lang, n=n, day_word=_day_word(n, lang=active_lang))
    if diff > 0:
        return _t("after_deadline", cfg=cfg, lang=active_lang, n=diff, day_word=_day_word(diff, lang=active_lang))
    return _t("on_deadline", cfg=cfg, lang=active_lang)


def _format_percent(value: float) -> str:
    text = f"{value:+.1f}%"
    return text.replace(".0%", "%")


def _set_this_deck_new_limit(deck: Dict[str, Any], new_limit: int) -> None:
    """Set the New cards/day limit in the "This deck" section.

    In current Anki versions, the permanent per-deck daily limit is stored on
    the deck as `newLimit`, corresponding to `Deck.Normal.new_limit` in the
    backend. `newLimitToday` is the temporary "Today only" override.

    We clear `newLimitToday` so an old temporary override does not mask the
    permanent "This deck" value on another client after sync.

    Prefer `update_dict()` on current Anki builds because it calls the backend
    deck update operation and returns normal change metadata. Fall back to
    `save()` / `update(..., preserve_usn=False)` on older or unusual builds.
    """
    limit = int(max(0, new_limit))
    deck["newLimit"] = limit
    deck["newLimitToday"] = None

    try:
        # Current Anki API: records a normal deck update via the backend.
        mw.col.decks.update_dict(deck)
    except Exception:
        try:
            # Legacy-compatible path; save() calls update(..., preserve_usn=False).
            mw.col.decks.save(deck)
        except Exception:
            # Last-resort fallback for unusual builds/versions.
            mw.col.decks.update(deck, preserve_usn=False)

    # Be conservative: make sure pending changes are flushed before a sync can run.
    try:
        mw.col.save()
    except Exception:
        pass


def _current_this_deck_new_limit(deck: Dict[str, Any]) -> Optional[int]:
    value = deck.get("newLimit", None)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _apply_limit_to_deck(deck_id: int, entry: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not _col_available():
        return None

    if not entry.get("enabled", False):
        return None

    deadline = _parse_date(str(entry.get("deadline", "")))
    if deadline is None:
        return {"deck_id": deck_id, "error": _t("error_invalid_deadline", cfg=cfg)}

    deck = mw.col.decks.get(deck_id, default=False)
    if not deck:
        return {"deck_id": deck_id, "error": _t("error_deck_not_found", cfg=cfg)}

    include_subdecks = bool(entry.get("include_subdecks", True))
    adjustment = _adjustment_percent(entry)
    days = _days_remaining(deadline)
    new_cards = _new_card_count(deck_id, include_subdecks)
    exact_daily = _exact_daily_cards(new_cards, days)
    new_limit = _calculate_limit(new_cards, days, cfg, adjustment)
    estimate = _estimate_completion(new_cards, new_limit)

    if deck.get("dyn", False):
        return {"deck_id": deck_id, "error": _t("error_filtered_deck", cfg=cfg)}

    old_limit = _current_this_deck_new_limit(deck)
    _set_this_deck_new_limit(deck, new_limit)

    entry["last_new_count"] = new_cards
    entry["last_days_remaining"] = days
    entry["last_exact_daily"] = round(exact_daily, 4)
    entry["last_daily_adjustment_percent"] = adjustment
    entry["last_limit"] = new_limit
    if estimate is not None:
        entry["last_days_to_finish"] = estimate[0]
        entry["last_estimated_finish_date"] = _format_date(estimate[1])
    else:
        entry["last_days_to_finish"] = None
        entry["last_estimated_finish_date"] = None
    entry["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = {
        "deck_id": deck_id,
        "deck_name": deck.get("name", str(deck_id)),
        "deadline": _format_date(deadline),
        "days": days,
        "new_cards": new_cards,
        "exact_daily": exact_daily,
        "adjustment_percent": adjustment,
        "old_limit": old_limit,
        "new_limit": new_limit,
    }
    if estimate is not None:
        result["days_to_finish"] = estimate[0]
        result["estimated_finish_date"] = _format_date(estimate[1])
        result["finish_relation"] = _finish_relation_text(estimate[1], deadline, cfg=cfg)
    return result


def update_all_deadline_decks(silent: bool = True, refresh: bool = True) -> List[Dict[str, Any]]:
    global _updating_now

    if _updating_now or not _col_available():
        return []

    _updating_now = True
    cfg = _load_config()
    results: List[Dict[str, Any]] = []

    try:
        changed = False
        decks_cfg = cfg.get("decks", {})
        for deck_id_str, entry in list(decks_cfg.items()):
            try:
                deck_id = int(deck_id_str)
            except Exception:
                continue

            if not isinstance(entry, dict) or not entry.get("enabled", False):
                continue

            result = _apply_limit_to_deck(deck_id, entry, cfg)
            if result:
                results.append(result)
                changed = True

        if changed:
            _save_config(cfg)
            if refresh:
                try:
                    mw.reset()
                except Exception:
                    pass

        if (not silent) and results:
            lines = []
            for item in results:
                if "error" in item:
                    lines.append(f"{item.get('deck_id')}: {item['error']}")
                else:
                    finish_text = ""
                    if item.get("estimated_finish_date"):
                        finish_text = _t(
                            "manual_finish_suffix",
                            cfg=cfg,
                            finish_date=item["estimated_finish_date"],
                            relation=item.get("finish_relation", ""),
                        )
                    lines.append(
                        _t(
                            "manual_result_line",
                            cfg=cfg,
                            deck_name=item["deck_name"],
                            new_cards=item["new_cards"],
                            days=item["days"],
                            day_word=_day_word(int(item["days"]), cfg=cfg),
                            adjustment=_format_percent(float(item.get("adjustment_percent", 0))),
                            new_limit=item["new_limit"],
                            finish_text=finish_text,
                        )
                    )
            showInfo("\n".join(lines), title=_addon_title(cfg))
        elif (not silent) and not results:
            showInfo(_t("no_active_deadlines", cfg=cfg), title=_addon_title(cfg))
        elif silent and results and cfg.get("show_tooltips_on_auto_update", False):
            tooltip(_t("tooltip_updated", cfg=cfg, addon_title=_addon_title(cfg)))

        return results
    except Exception as exc:
        if not silent:
            showWarning(_t("recalc_error", cfg=cfg, error=exc), title=_addon_title(cfg))
        return results
    finally:
        _updating_now = False


def _schedule_update_after_card_addition(*_args: Any, **_kwargs: Any) -> None:
    global _update_timer
    if not _col_available():
        return

    if _update_timer is None:
        _update_timer = QTimer(mw)
        _update_timer.setSingleShot(True)
        _update_timer.setInterval(2000)
        qconnect(_update_timer.timeout, lambda: update_all_deadline_decks(silent=True, refresh=True))

    _update_timer.stop()
    _update_timer.start()


class DeadlineDialog(QDialog):
    def __init__(self) -> None:
        super().__init__(mw)
        self.cfg = _load_config()
        self.form_labels: Dict[str, QLabel] = {}
        self._setup_ui()
        self._populate_decks()
        self._load_selected_deck_config()
        self._set_static_texts()

    def _lang(self) -> str:
        try:
            return _normalize_language(self.language_combo.currentData())
        except Exception:
            return _config_language(self.cfg)

    def _tr(self, key: str, **kwargs: Any) -> str:
        return _t(key, cfg=self.cfg, lang=self._lang(), **kwargs)

    def _add_form_row(self, key: str, widget: QWidget) -> None:
        label = QLabel("")
        self.form_labels[key] = label
        self.form.addRow(label, widget)

    def _setup_ui(self) -> None:
        self.setMinimumWidth(600)
        layout = QVBoxLayout()

        self.intro_label = QLabel("")
        self.intro_label.setWordWrap(True)
        layout.addWidget(self.intro_label)

        self.form = QFormLayout()

        self.language_combo = QComboBox()
        for code, label in LANGUAGES:
            self.language_combo.addItem(label, code)
        current_lang = _config_language(self.cfg)
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break
        self._add_form_row("language_label", self.language_combo)

        self.deck_combo = QComboBox()
        qconnect(self.deck_combo.currentIndexChanged, self._load_selected_deck_config)
        self._add_form_row("deck_label", self.deck_combo)

        self.enabled_checkbox = QCheckBox("")
        self._add_form_row("status_label", self.enabled_checkbox)

        self.deadline_edit = QDateEdit()
        self.deadline_edit.setDisplayFormat("yyyy-MM-dd")
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDate(QDate.currentDate().addDays(30))
        qconnect(self.deadline_edit.dateChanged, self._update_preview)
        self._add_form_row("deadline_label", self.deadline_edit)

        self.adjustment_spin = QDoubleSpinBox()
        self.adjustment_spin.setRange(-95.0, 500.0)
        self.adjustment_spin.setDecimals(1)
        self.adjustment_spin.setSingleStep(5.0)
        self.adjustment_spin.setSuffix(" %")
        qconnect(self.adjustment_spin.valueChanged, self._update_preview)
        self._add_form_row("adjustment_label", self.adjustment_spin)

        self.include_subdecks_checkbox = QCheckBox("")
        self.include_subdecks_checkbox.setChecked(True)
        qconnect(self.include_subdecks_checkbox.stateChanged, self._update_preview)
        self._add_form_row("counting_label", self.include_subdecks_checkbox)

        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self._add_form_row("preview_label", self.preview_label)

        layout.addLayout(self.form)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("")
        self.recalc_button = QPushButton("")
        self.disable_button = QPushButton("")
        self.close_button = QPushButton("")

        qconnect(self.save_button.clicked, self._save_current)
        qconnect(self.recalc_button.clicked, self._recalculate_all)
        qconnect(self.disable_button.clicked, self._disable_current)
        qconnect(self.close_button.clicked, self.close)

        button_row.addWidget(self.save_button)
        button_row.addWidget(self.recalc_button)
        button_row.addWidget(self.disable_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self.note_label = QLabel("")
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)

        self.setLayout(layout)
        qconnect(self.language_combo.currentIndexChanged, self._on_language_changed)

    def _set_static_texts(self) -> None:
        self.setWindowTitle(self._tr("addon_title"))
        self.intro_label.setText(self._tr("intro"))
        for key, label in self.form_labels.items():
            label.setText(self._tr(key))
        self.enabled_checkbox.setText(self._tr("enable_checkbox"))
        self.include_subdecks_checkbox.setText(self._tr("include_subdecks_checkbox"))
        self.adjustment_spin.setToolTip(self._tr("adjustment_tooltip"))
        self.save_button.setText(self._tr("save_button"))
        self.recalc_button.setText(self._tr("recalculate_button"))
        self.disable_button.setText(self._tr("disable_button"))
        self.close_button.setText(self._tr("close_button"))
        self.note_label.setText(self._tr("note"))

    def _on_language_changed(self, *_args: Any) -> None:
        self.cfg = _load_config()
        self.cfg["language"] = self._lang()
        _save_config(self.cfg)
        self._set_static_texts()
        _refresh_menu_texts(self.cfg)
        self._update_preview()

    def _populate_decks(self) -> None:
        self.deck_combo.clear()
        current_id = 0
        try:
            current_id = int(mw.col.decks.get_current_id())
        except Exception:
            pass

        selected_index = 0
        for index, (name, did) in enumerate(_all_regular_decks()):
            self.deck_combo.addItem(name, did)
            if did == current_id:
                selected_index = index

        if self.deck_combo.count() > 0:
            self.deck_combo.setCurrentIndex(selected_index)

    def _current_deck_id(self) -> Optional[int]:
        value = self.deck_combo.currentData()
        try:
            return int(value)
        except Exception:
            return None

    def _current_deadline(self) -> date:
        qdate = self.deadline_edit.date()
        return date(qdate.year(), qdate.month(), qdate.day())

    def _load_selected_deck_config(self, *_args: Any) -> None:
        did = self._current_deck_id()
        if did is None:
            return

        entry = self.cfg.get("decks", {}).get(str(did), {})
        self.enabled_checkbox.setChecked(bool(entry.get("enabled", False)))
        self.include_subdecks_checkbox.setChecked(bool(entry.get("include_subdecks", True)))
        self.adjustment_spin.setValue(_adjustment_percent(entry))

        deadline = _parse_date(str(entry.get("deadline", "")))
        if deadline is None:
            # Practical default: 30 days from today.
            deadline = date.fromordinal(_today().toordinal() + 30)

        self.deadline_edit.setDate(QDate(deadline.year, deadline.month, deadline.day))
        self._update_preview()

    def _update_preview(self, *_args: Any) -> None:
        did = self._current_deck_id()
        if did is None or not _col_available():
            self.preview_label.setText(self._tr("no_deck_selected"))
            return

        try:
            deadline = self._current_deadline()
            include_subdecks = self.include_subdecks_checkbox.isChecked()
            adjustment = float(self.adjustment_spin.value())
            new_cards = _new_card_count(did, include_subdecks)
            days = _days_remaining(deadline)
            exact_daily = _exact_daily_cards(new_cards, days)
            limit = _calculate_limit(new_cards, days, self.cfg, adjustment)
            estimate = _estimate_completion(new_cards, limit)

            if estimate is None:
                finish_line = self._tr("preview_no_estimate")
            else:
                days_to_finish, finish_date = estimate
                if new_cards <= 0:
                    finish_line = self._tr("preview_already_clear")
                else:
                    finish_line = self._tr(
                        "preview_finish",
                        days_to_finish=days_to_finish,
                        day_word=_day_word(days_to_finish, lang=self._lang()),
                        finish_date=_format_date(finish_date),
                        relation=_finish_relation_text(finish_date, deadline, cfg=self.cfg, lang=self._lang()),
                    )

            self.preview_label.setText(
                self._tr(
                    "preview_text",
                    new_cards=new_cards,
                    exact_daily=exact_daily,
                    days=days,
                    day_word=_day_word(days, lang=self._lang()),
                    adjustment=_format_percent(adjustment),
                    limit=limit,
                    finish_line=finish_line,
                )
            )
        except Exception as exc:
            self.preview_label.setText(self._tr("preview_error", error=exc))

    def _save_current(self) -> None:
        did = self._current_deck_id()
        if did is None:
            showWarning(self._tr("select_deck_warning"), title=self._tr("addon_title"))
            return

        self.cfg = _load_config()
        self.cfg["language"] = self._lang()
        self.cfg.setdefault("decks", {})
        entry = self.cfg["decks"].setdefault(str(did), {})
        entry["enabled"] = self.enabled_checkbox.isChecked()
        entry["deadline"] = _format_date(self._current_deadline())
        entry["include_subdecks"] = self.include_subdecks_checkbox.isChecked()
        entry["daily_adjustment_percent"] = float(self.adjustment_spin.value())
        _save_config(self.cfg)
        _refresh_menu_texts(self.cfg)

        result = _apply_limit_to_deck(did, entry, self.cfg) if entry["enabled"] else None
        _save_config(self.cfg)
        try:
            mw.reset()
        except Exception:
            pass

        self._update_preview()

        if result and "error" not in result:
            finish_text = ""
            if result.get("estimated_finish_date"):
                finish_text = self._tr(
                    "finish_text",
                    finish_date=result["estimated_finish_date"],
                    relation=result.get("finish_relation", ""),
                )
            showInfo(
                self._tr(
                    "saved_info",
                    deck_name=result["deck_name"],
                    new_cards=result["new_cards"],
                    days=result["days"],
                    exact_daily=result["exact_daily"],
                    adjustment=_format_percent(float(result.get("adjustment_percent", 0))),
                    new_limit=result["new_limit"],
                    finish_text=finish_text,
                ),
                title=self._tr("addon_title"),
            )
        elif entry["enabled"]:
            showWarning(self._tr("saved_but_problem", result=result), title=self._tr("addon_title"))
        else:
            showInfo(self._tr("disabled_info"), title=self._tr("addon_title"))

    def _disable_current(self) -> None:
        did = self._current_deck_id()
        if did is None:
            return

        self.cfg = _load_config()
        self.cfg["language"] = self._lang()
        entry = self.cfg.setdefault("decks", {}).setdefault(str(did), {})
        entry["enabled"] = False
        _save_config(self.cfg)
        _refresh_menu_texts(self.cfg)
        self.enabled_checkbox.setChecked(False)
        showInfo(self._tr("disabled_keep_limit"), title=self._tr("addon_title"))

    def _recalculate_all(self) -> None:
        self.cfg = _load_config()
        self.cfg["language"] = self._lang()
        _save_config(self.cfg)
        _refresh_menu_texts(self.cfg)
        update_all_deadline_decks(silent=False, refresh=True)
        self._update_preview()


def open_deadline_dialog() -> None:
    cfg = _load_config()
    if not _col_available():
        showWarning(_t("open_profile_warning", cfg=cfg), title=_addon_title(cfg))
        return
    dialog = DeadlineDialog()
    dialog.exec()


def recalculate_now() -> None:
    update_all_deadline_decks(silent=False, refresh=True)


def _on_profile_opened() -> None:
    update_all_deadline_decks(silent=True, refresh=True)


def _start_hourly_timer() -> None:
    global _hourly_timer
    if _hourly_timer is None:
        _hourly_timer = QTimer(mw)
        _hourly_timer.setInterval(60 * 60 * 1000)  # if Anki stays open across day changes
        qconnect(_hourly_timer.timeout, lambda: update_all_deadline_decks(silent=True, refresh=True))
        _hourly_timer.start()


def _refresh_menu_texts(cfg: Optional[Dict[str, Any]] = None) -> None:
    if cfg is None:
        cfg = _load_config()
    if setup_action is not None:
        setup_action.setText(_t("menu_configure", cfg=cfg))
    if recalc_action is not None:
        recalc_action.setText(_t("menu_recalculate", cfg=cfg))


# Tools menu
_initial_cfg = _load_config()
setup_action = QAction(_t("menu_configure", cfg=_initial_cfg), mw)
qconnect(setup_action.triggered, open_deadline_dialog)
mw.form.menuTools.addAction(setup_action)

recalc_action = QAction(_t("menu_recalculate", cfg=_initial_cfg), mw)
qconnect(recalc_action.triggered, recalculate_now)
mw.form.menuTools.addAction(recalc_action)

# Automatic hooks
gui_hooks.profile_did_open.append(_on_profile_opened)
# Recalculate before sync so the updated deck limit is included in the sync upload.
if hasattr(gui_hooks, "sync_will_start"):
    gui_hooks.sync_will_start.append(lambda: update_all_deadline_decks(silent=True, refresh=True))
else:
    gui_hooks.sync_did_finish.append(lambda: update_all_deadline_decks(silent=True, refresh=True))

# After adding notes through the Add screen/AnkiConnect, schedule a short recalculation.
# The timer avoids recalculating dozens of times during batch additions.
if anki_hooks is not None and hasattr(anki_hooks, "note_will_be_added"):
    anki_hooks.note_will_be_added.append(_schedule_update_after_card_addition)

_start_hourly_timer()
