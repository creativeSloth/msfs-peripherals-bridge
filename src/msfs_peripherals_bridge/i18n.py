"""Lightweight in-process translation layer for the GUI.

Every user-facing GUI string goes through :func:`tr`. Translations live in the
per-language ``_STRINGS`` table below. A missing key falls back to German (the
project's original language), then to the key itself, so *partial* coverage
never blanks a widget or raises — new tabs can be translated incrementally.

The active language is process-global: the GUI reads the persisted setting once
at startup (:func:`set_language`) and re-applies it on a language switch. The
module has no tkinter or filesystem dependency, so it is trivially testable.
"""

from __future__ import annotations

# Language code -> its own native name (shown verbatim in the Settings dropdown).
LANGUAGES: dict[str, str] = {
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
}
DEFAULT_LANG = "de"

_current = DEFAULT_LANG


def available_languages() -> dict[str, str]:
    """Ordered mapping of language code -> native name."""
    return dict(LANGUAGES)


def set_language(code: str | None) -> None:
    """Set the active language; unknown/None codes fall back to German."""
    global _current
    _current = code if code in LANGUAGES else DEFAULT_LANG


def get_language() -> str:
    return _current


def language_name(code: str) -> str:
    """Native name for a code (e.g. ``"de"`` -> ``"Deutsch"``)."""
    return LANGUAGES.get(code, code)


def code_for_name(name: str) -> str:
    """Inverse of :func:`language_name`; unknown names fall back to German."""
    for code, native in LANGUAGES.items():
        if native == name:
            return code
    return DEFAULT_LANG


def tr(key: str, /, **kwargs: object) -> str:
    """Translate ``key`` into the active language.

    Falls back to German, then to the raw key. ``kwargs`` are applied with
    ``str.format`` when present (a formatting error yields the unformatted
    string rather than raising).
    """
    entry = _STRINGS.get(key, {})
    text = entry.get(_current) or entry.get(DEFAULT_LANG) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


# --------------------------------------------------------------------------- #
# Translation table.  key -> {lang: text}.  Keep every key's four languages
# together; the test-suite enforces that each key defines all four.
# --------------------------------------------------------------------------- #
_STRINGS: dict[str, dict[str, str]] = {
    # ----- notebook tab titles -------------------------------------------- #
    "tab.connection": {"de": "Verbindung", "en": "Connection", "es": "Conexión", "fr": "Connexion"},
    "tab.variables": {"de": "Variablen", "en": "Variables", "es": "Variables", "fr": "Variables"},
    "tab.mapper": {"de": "Mapper", "en": "Mapper", "es": "Mapeo", "fr": "Mappage"},
    "tab.gauges": {"de": "Instrumente", "en": "Gauges", "es": "Instrumentos", "fr": "Instruments"},
    "tab.profile": {"de": "Profil", "en": "Profile", "es": "Perfil", "fr": "Profil"},
    "tab.settings": {"de": "Einstellungen", "en": "Settings", "es": "Ajustes", "fr": "Paramètres"},

    # ----- Connection tab: sub-tabs --------------------------------------- #
    "conn.subtab.control": {
        "de": "Steuerung & Status", "en": "Control & status",
        "es": "Control y estado", "fr": "Contrôle et état"},
    "conn.subtab.log": {
        "de": "Bridge-Protokoll", "en": "Bridge log",
        "es": "Registro del puente", "fr": "Journal du pont"},

    # ----- Connection tab: process group ---------------------------------- #
    "conn.group.processes": {
        "de": "Prozesse", "en": "Processes", "es": "Procesos", "fr": "Processus"},
    "conn.bridge": {"de": "Bridge", "en": "Bridge", "es": "Puente", "fr": "Pont"},
    "conn.mapper": {"de": "Mapper", "en": "Mapper", "es": "Mapeo", "fr": "Mappage"},
    "conn.start": {"de": "Starten", "en": "Start", "es": "Iniciar", "fr": "Démarrer"},
    "conn.stop": {"de": "Stoppen", "en": "Stop", "es": "Detener", "fr": "Arrêter"},
    "conn.stop_all": {
        "de": "Alles stoppen (Aufräumen)", "en": "Stop everything (clean up)",
        "es": "Detener todo (limpiar)", "fr": "Tout arrêter (nettoyer)"},
    "conn.single_client_note": {
        "de": "Die Bridge ist single-client — Mapper ODER ein Werkzeug.",
        "en": "The bridge is single-client — the mapper OR one tool.",
        "es": "El puente es de un solo cliente: el mapeo O una herramienta.",
        "fr": "Le pont est mono-client — le mappage OU un outil."},

    # ----- Connection tab: environment / prerequisites -------------------- #
    "conn.group.environment": {
        "de": "Umgebung & Voraussetzungen", "en": "Environment & prerequisites",
        "es": "Entorno y requisitos", "fr": "Environnement et prérequis"},
    "conn.prefix_label": {
        "de": "MSFS-Proton-Prefix", "en": "MSFS Proton prefix",
        "es": "Prefijo Proton de MSFS", "fr": "Préfixe Proton de MSFS"},
    "conn.prefix_hint": {
        "de": "Pfad zum Proton-Prefix (…/compatdata/<AppID>/pfx). Leer = Standard "
              "(automatische Steam-Erkennung).",
        "en": "Path to the Proton prefix (…/compatdata/<AppID>/pfx). Empty = default "
              "(automatic Steam detection).",
        "es": "Ruta al prefijo Proton (…/compatdata/<AppID>/pfx). Vacío = predeterminado "
              "(detección automática de Steam).",
        "fr": "Chemin du préfixe Proton (…/compatdata/<AppID>/pfx). Vide = défaut "
              "(détection automatique de Steam)."},
    "conn.browse": {"de": "Durchsuchen…", "en": "Browse…", "es": "Examinar…", "fr": "Parcourir…"},
    "conn.save": {"de": "Speichern", "en": "Save", "es": "Guardar", "fr": "Enregistrer"},
    "conn.recheck": {
        "de": "Erneut prüfen", "en": "Re-check",
        "es": "Volver a comprobar", "fr": "Revérifier"},
    "conn.setup_prefix": {
        "de": "Prefix einrichten…", "en": "Set up prefix…",
        "es": "Configurar prefijo…", "fr": "Configurer le préfixe…"},
    "conn.prereq_title": {
        "de": "Voraussetzungen", "en": "Prerequisites", "es": "Requisitos", "fr": "Prérequis"},
    "conn.prereq_all_ok": {
        "de": "Alle Voraussetzungen erfüllt.", "en": "All prerequisites met.",
        "es": "Todos los requisitos cumplidos.", "fr": "Tous les prérequis satisfaits."},
    "conn.prereq_problems": {
        "de": "{n} Problem(e) — Bridge kann so nicht starten.",
        "en": "{n} problem(s) — the bridge cannot start like this.",
        "es": "{n} problema(s): el puente no puede iniciarse así.",
        "fr": "{n} problème(s) — le pont ne peut pas démarrer ainsi."},
    "conn.log_label": {
        "de": "Bridge-Protokoll (Wine-Ebene, live)",
        "en": "Bridge log (Wine layer, live)",
        "es": "Registro del puente (capa Wine, en vivo)",
        "fr": "Journal du pont (couche Wine, en direct)"},

    # ----- prerequisite check item names (env_check.CheckItem.key) -------- #
    "check.prefix": {
        "de": "Proton-Prefix vorhanden", "en": "Proton prefix present",
        "es": "Prefijo Proton presente", "fr": "Préfixe Proton présent"},
    "check.drive_c": {
        "de": "Windows-Laufwerk (drive_c)", "en": "Windows drive (drive_c)",
        "es": "Unidad de Windows (drive_c)", "fr": "Lecteur Windows (drive_c)"},
    "check.pythonw": {
        "de": "Windows-Python (pythonw.exe)", "en": "Windows Python (pythonw.exe)",
        "es": "Python de Windows (pythonw.exe)", "fr": "Python Windows (pythonw.exe)"},
    "check.python": {
        "de": "Windows-Python (python.exe)", "en": "Windows Python (python.exe)",
        "es": "Python de Windows (python.exe)", "fr": "Python Windows (python.exe)"},
    "check.simconnect": {
        "de": "SimConnect.dll", "en": "SimConnect.dll",
        "es": "SimConnect.dll", "fr": "SimConnect.dll"},
    "check.proton": {
        "de": "Proton-Laufzeit", "en": "Proton runtime",
        "es": "Entorno de ejecución Proton", "fr": "Environnement Proton"},
    "check.run_bridge": {
        "de": "Bridge-Startskript (run-bridge.sh)", "en": "Bridge launcher (run-bridge.sh)",
        "es": "Lanzador del puente (run-bridge.sh)", "fr": "Lanceur du pont (run-bridge.sh)"},
    "check.bridge_py": {
        "de": "Bridge-Programm (bridge.py)", "en": "Bridge program (bridge.py)",
        "es": "Programa del puente (bridge.py)", "fr": "Programme du pont (bridge.py)"},

    # ----- Settings tab --------------------------------------------------- #
    "settings.title": {
        "de": "Einstellungen", "en": "Settings", "es": "Ajustes", "fr": "Paramètres"},
    "settings.language_group": {
        "de": "Sprache", "en": "Language", "es": "Idioma", "fr": "Langue"},
    "settings.language_label": {
        "de": "GUI-Sprache", "en": "GUI language",
        "es": "Idioma de la interfaz", "fr": "Langue de l'interface"},
    "settings.language_hint": {
        "de": "Die Auswahl wird sofort gespeichert und beim Neustart der GUI angewendet.",
        "en": "The choice is saved immediately and applied when the GUI restarts.",
        "es": "La elección se guarda al instante y se aplica al reiniciar la interfaz.",
        "fr": "Le choix est enregistré aussitôt et appliqué au redémarrage de l'interface."},
    "settings.apply_restart": {
        "de": "Anwenden & GUI neu starten", "en": "Apply & restart GUI",
        "es": "Aplicar y reiniciar la interfaz", "fr": "Appliquer et redémarrer l'interface"},
    "settings.restart_needed": {
        "de": "Neustart erforderlich, um die Sprache vollständig anzuwenden.",
        "en": "A restart is required to fully apply the language.",
        "es": "Se requiere reiniciar para aplicar el idioma por completo.",
        "fr": "Un redémarrage est nécessaire pour appliquer pleinement la langue."},

    # ----- status bar ----------------------------------------------------- #
    "status.label": {"de": "Status:", "en": "Status:", "es": "Estado:", "fr": "État :"},
    "status.profile": {"de": "Profil:", "en": "Profile:", "es": "Perfil:", "fr": "Profil :"},

    # ----- shared dialog strings ------------------------------------------ #
    "dialog.confirm": {
        "de": "Bestätigen", "en": "Confirm", "es": "Confirmar", "fr": "Confirmer"},
    "dialog.error": {"de": "Fehler", "en": "Error", "es": "Error", "fr": "Erreur"},
    "dialog.note": {"de": "Hinweis", "en": "Note", "es": "Aviso", "fr": "Remarque"},
    "conn.setup_confirm": {
        "de": "setup-prefix.sh richtet Windows-Python + SimConnect im Prefix ein "
              "(Download, dauert einige Minuten). Jetzt starten?",
        "en": "setup-prefix.sh installs Windows Python + SimConnect into the prefix "
              "(downloads, takes a few minutes). Start now?",
        "es": "setup-prefix.sh instala Python de Windows + SimConnect en el prefijo "
              "(descarga, tarda unos minutos). ¿Iniciar ahora?",
        "fr": "setup-prefix.sh installe Python Windows + SimConnect dans le préfixe "
              "(téléchargement, quelques minutes). Démarrer maintenant ?"},
    "conn.setup_running": {
        "de": "Prefix-Einrichtung läuft — Fortschritt im Fenster. Danach „Erneut prüfen“.",
        "en": "Prefix setup is running — see the window for progress. Then “Re-check”.",
        "es": "La configuración del prefijo está en curso; vea el progreso. Luego «Comprobar».",
        "fr": "Configuration du préfixe en cours — voir la fenêtre. Ensuite « Revérifier »."},
    "conn.setup_title": {
        "de": "Prefix-Einrichtung", "en": "Prefix setup",
        "es": "Configuración del prefijo", "fr": "Configuration du préfixe"},

    # ===================================================================== #
    # Bulk GUI strings, keyed by their German source text (gettext-msgid style):
    # a missing "de" entry means tr() returns the key itself. Only en/es/fr are
    # supplied. Grouped roughly by tab, but many are shared across tabs.
    # ===================================================================== #

    # ----- shared words --------------------------------------------------- #
    "Name": {"en": "Name", "es": "Nombre", "fr": "Nom"},
    "Startwert": {"en": "Initial value", "es": "Valor inicial", "fr": "Valeur initiale"},
    "Beschreibung": {"en": "Description", "es": "Descripción", "fr": "Description"},
    "Anlegen": {"en": "Create", "es": "Crear", "fr": "Créer"},
    "Entfernen": {"en": "Remove", "es": "Quitar", "fr": "Retirer"},
    "Hinzufügen": {"en": "Add", "es": "Añadir", "fr": "Ajouter"},
    "Duplizieren": {"en": "Duplicate", "es": "Duplicar", "fr": "Dupliquer"},
    "Übernehmen": {"en": "Apply", "es": "Aplicar", "fr": "Appliquer"},
    "Zurücksetzen": {"en": "Reset", "es": "Restablecer", "fr": "Réinitialiser"},
    "Schließen": {"en": "Close", "es": "Cerrar", "fr": "Fermer"},
    "Abbrechen": {"en": "Cancel", "es": "Cancelar", "fr": "Annuler"},
    "Wählen…": {"en": "Choose…", "es": "Elegir…", "fr": "Choisir…"},
    "Typ": {"en": "Type", "es": "Tipo", "fr": "Type"},
    "Variable": {"en": "Variable", "es": "Variable", "fr": "Variable"},
    "Wert": {"en": "Value", "es": "Valor", "fr": "Valeur"},
    "Einheit": {"en": "Unit", "es": "Unidad", "fr": "Unité"},
    "Gerät": {"en": "Device", "es": "Dispositivo", "fr": "Périphérique"},
    "Status": {"en": "Status", "es": "Estado", "fr": "État"},
    "Aktion": {"en": "Action", "es": "Acción", "fr": "Action"},
    "Gespeichert": {"en": "Saved", "es": "Guardado", "fr": "Enregistré"},
    "Suche": {"en": "Search", "es": "Buscar", "fr": "Rechercher"},

    # ----- Variables (Statistik) tab -------------------------------------- #
    "Live-Wertliste — Variablen zum Beobachten zusammenstellen:": {
        "en": "Live value list — assemble variables to watch:",
        "es": "Lista de valores en vivo: reúne variables para observar:",
        "fr": "Liste de valeurs en direct — rassemblez les variables à observer :"},
    "(Event)": {"en": "(event)", "es": "(evento)", "fr": "(événement)"},
    "Panel öffnen": {"en": "Open panel", "es": "Abrir panel", "fr": "Ouvrir le panneau"},
    "Panel schließen": {"en": "Close panel", "es": "Cerrar panel", "fr": "Fermer le panneau"},
    "Variablen in die Liste holen": {
        "en": "Add variables to the list", "es": "Añadir variables a la lista",
        "fr": "Ajouter des variables à la liste"},
    "Variablen aus Liste entfernen": {
        "en": "Remove variables from list", "es": "Quitar variables de la lista",
        "fr": "Retirer des variables de la liste"},
    "Popup: nach Typ (A:/K:/L:/V:) filtern + Namen suchen": {
        "en": "Popup: filter by type (A:/K:/L:/V:) + search names",
        "es": "Ventana: filtrar por tipo (A:/K:/L:/V:) + buscar nombres",
        "fr": "Fenêtre : filtrer par type (A:/K:/L:/V:) + rechercher des noms"},
    "Loslösbares Kachel-Panel öffnen/schließen (mit eigenem Picker)": {
        "en": "Open/close the detachable tile panel (with its own picker)",
        "es": "Abrir/cerrar el panel de mosaicos (con su propio selector)",
        "fr": "Ouvrir/fermer le panneau de tuiles détachable (avec son sélecteur)"},
    "Eigene V:-Variablen (Bridge-Hub, sim-unabhängig)": {
        "en": "Own V: variables (bridge hub, sim-independent)",
        "es": "Variables V: propias (concentrador del puente, independiente del sim)",
        "fr": "Variables V: propres (concentrateur du pont, indépendant du sim)"},
    "Name (V:…)": {"en": "Name (V:…)", "es": "Nombre (V:…)", "fr": "Nom (V:…)"},
    "Name fehlt.": {"en": "Name is missing.", "es": "Falta el nombre.", "fr": "Nom manquant."},
    "Startwert muss eine Zahl sein.": {
        "en": "Initial value must be a number.",
        "es": "El valor inicial debe ser un número.",
        "fr": "La valeur initiale doit être un nombre."},
    "Erst eine V:-Variable markieren.": {
        "en": "Select a V: variable first.",
        "es": "Primero seleccione una variable V:.",
        "fr": "Sélectionnez d'abord une variable V:."},
}
