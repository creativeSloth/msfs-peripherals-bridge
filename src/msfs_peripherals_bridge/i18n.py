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
    "tab.monitor": {"de": "Monitor", "en": "Monitor", "es": "Monitor", "fr": "Monitor"},
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

    # ----- shared / short labels (tabs: Mapper, Gauges, Profile, picker) --- #
    "Suche:": {"en": "Search:", "es": "Buscar:", "fr": "Recherche :"},
    "Typ:": {"en": "Type:", "es": "Tipo:", "fr": "Type :"},
    "Raster": {"en": "Grid", "es": "Cuadrícula", "fr": "Grille"},
    "Live": {"en": "Live", "es": "En vivo", "fr": "En direct"},
    "Quelle": {"en": "Source", "es": "Fuente", "fr": "Source"},
    "Event": {"en": "Event", "es": "Evento", "fr": "Événement"},
    "Read": {"de": "Lesen", "en": "Read", "es": "Leer", "fr": "Lire"},
    "Unit": {"de": "Einheit", "en": "Unit", "es": "Unidad", "fr": "Unité"},
    "invert": {"de": "invertieren", "en": "invert", "es": "invertir", "fr": "inverser"},
    "Kurve": {"en": "Curve", "es": "Curva", "fr": "Courbe"},
    "Faktor": {"en": "Factor", "es": "Factor", "fr": "Facteur"},
    "Richtungen": {"en": "Directions", "es": "Direcciones", "fr": "Directions"},
    "Verarbeitung": {"en": "Processing", "es": "Procesamiento", "fr": "Traitement"},
    "Mehrschritt": {"en": "Multi-step", "es": "Varios pasos", "fr": "Multi-étapes"},
    "+ Neu": {"en": "+ New", "es": "+ Nuevo", "fr": "+ Nouveau"},
    "+ Binding": {"en": "+ Binding", "es": "+ Asignación", "fr": "+ Liaison"},
    "+ Eintrag": {"en": "+ Entry", "es": "+ Entrada", "fr": "+ Entrée"},
    "+ Schritt": {"en": "+ Step", "es": "+ Paso", "fr": "+ Étape"},
    "+ Bedingung": {"en": "+ Condition", "es": "+ Condición", "fr": "+ Condition"},
    "+ Gauge": {"en": "+ Gauge", "es": "+ Instrumento", "fr": "+ Instrument"},
    "+ Variable": {"en": "+ Variable", "es": "+ Variable", "fr": "+ Variable"},
    "+ Saitek-Panel": {"en": "+ Saitek panel", "es": "+ Panel Saitek", "fr": "+ Panneau Saitek"},
    "✕ Entfernen": {"en": "✕ Remove", "es": "✕ Quitar", "fr": "✕ Retirer"},
    "✕ Eintrag entfernen": {
        "en": "✕ Remove entry", "es": "✕ Quitar entrada", "fr": "✕ Retirer l'entrée"},
    "✕ Panel-Block entfernen": {
        "en": "✕ Remove panel block", "es": "✕ Quitar bloque del panel",
        "fr": "✕ Retirer le bloc de panneau"},
    "✎ Mappen": {"en": "✎ Map", "es": "✎ Asignar", "fr": "✎ Mapper"},
    "Kachel entfernen": {"en": "Remove tile", "es": "Quitar mosaico", "fr": "Retirer la tuile"},

    # ----- Mapper tab ----------------------------------------------------- #
    "Geräte im Profil — was ist worauf gemappt:": {
        "en": "Devices in the profile — what is mapped where:",
        "es": "Dispositivos del perfil: qué está asignado a qué:",
        "fr": "Périphériques du profil — ce qui est mappé où :"},
    "Geräte neu erkennen": {
        "en": "Re-detect devices", "es": "Volver a detectar dispositivos",
        "fr": "Redétecter les périphériques"},
    "evdev + hidraw discovery — welche Geräte hängen jetzt dran": {
        "en": "evdev + hidraw discovery — which devices are connected now",
        "es": "detección evdev + hidraw: qué dispositivos están conectados ahora",
        "fr": "détection evdev + hidraw — quels périphériques sont connectés maintenant"},
    "Kein Gerät gewählt — links ein Gerät markieren.": {
        "en": "No device selected — select one on the left.",
        "es": "Ningún dispositivo seleccionado: elija uno a la izquierda.",
        "fr": "Aucun périphérique sélectionné — choisissez-en un à gauche."},
    "Doppelklick auf eine Zeile öffnet den Editor · Entfernen wirkt auf die markierte Zeile": {
        "en": "Double-click a row to open the editor · Remove acts on the selected row",
        "es": "Doble clic en una fila abre el editor · Quitar actúa sobre la fila seleccionada",
        "fr": "Double-clic sur une ligne ouvre l'éditeur · Retirer agit sur la ligne sélectionnée"},

    # ----- binding editor ------------------------------------------------- #
    "Eingang (roh)": {"en": "Input (raw)", "es": "Entrada (bruto)", "fr": "Entrée (brut)"},
    "Ausgang (out)": {"en": "Output (out)", "es": "Salida (out)", "fr": "Sortie (out)"},
    "Detent (roh)": {"en": "Detent (raw)", "es": "Retén (bruto)", "fr": "Cran (brut)"},
    "Achse am Detent teilen": {
        "en": "Split axis at the detent", "es": "Dividir el eje en el retén",
        "fr": "Diviser l'axe au cran"},
    "⬇ Unterhalb des Detents — eigene Aktion": {
        "en": "⬇ Below the detent — its own action",
        "es": "⬇ Por debajo del retén: su propia acción",
        "fr": "⬇ Sous le cran — sa propre action"},
    "→ als min": {"en": "→ as min", "es": "→ como mín", "fr": "→ comme min"},
    "→ als max": {"en": "→ as max", "es": "→ como máx", "fr": "→ comme max"},
    "→ als Detent": {"en": "→ as detent", "es": "→ como retén", "fr": "→ comme cran"},
    "Hat — vier Richtungen, ein Binding": {
        "en": "Hat — four directions, one binding",
        "es": "Hat: cuatro direcciones, una asignación",
        "fr": "Hat — quatre directions, une liaison"},
    "Hebel/Achse bewegen — aktueller Rohwert:": {
        "en": "Move the lever/axis — current raw value:",
        "es": "Mueva la palanca/eje: valor bruto actual:",
        "fr": "Déplacez le levier/axe — valeur brute actuelle :"},
    "Hebel an ein Ende / an die Raste fahren, Wert ablesen und übernehmen. „als Detent“ "
    "füllt die Split-Grenze (Achse teilen).": {
        "en": "Move the lever to an end / to the detent, read the value and apply it. "
              "“as detent” fills the split boundary (axis split).",
        "es": "Mueva la palanca a un extremo / al retén, lea el valor y aplíquelo. "
              "«como retén» rellena el límite de división (dividir eje).",
        "fr": "Amenez le levier à une extrémité / au cran, lisez la valeur et appliquez-la. "
              "« comme cran » remplit la limite de division (division de l'axe)."},
    "mehrere Schritte je Flanke — unten bearbeiten ↓": {
        "en": "several steps per edge — edit below ↓",
        "es": "varios pasos por flanco: editar abajo ↓",
        "fr": "plusieurs étapes par front — éditer ci-dessous ↓"},
    "Sequence — mehrere Schritte je Flanke (Event feuern / SimVar setzen):": {
        "en": "Sequence — several steps per edge (fire event / set SimVar):",
        "es": "Secuencia: varios pasos por flanco (disparar evento / fijar SimVar):",
        "fr": "Séquence — plusieurs étapes par front (déclencher un event / définir un SimVar) :"},
    "⚑ Bedingung — nur ausführen, wenn …": {
        "en": "⚑ Condition — only run when …",
        "es": "⚑ Condición: ejecutar solo cuando …",
        "fr": "⚑ Condition — exécuter seulement si …"},
    "keine — gilt immer": {
        "en": "none — always applies", "es": "ninguna: siempre se aplica",
        "fr": "aucune — s'applique toujours"},
    "Kein Binding gewählt — rechts eine Binding-Zeile markieren.": {
        "en": "No binding selected — select a binding row on the right.",
        "es": "Ninguna asignación seleccionada: elija una fila a la derecha.",
        "fr": "Aucune liaison sélectionnée — sélectionnez une ligne à droite."},
    "Binding dupliziert ✓": {
        "en": "Binding duplicated ✓", "es": "Asignación duplicada ✓",
        "fr": "Liaison dupliquée ✓"},
    "Binding entfernt ✓": {
        "en": "Binding removed ✓", "es": "Asignación quitada ✓", "fr": "Liaison retirée ✓"},
    "Bedienelement anlernen: lauscht live am angeschlossenen Gerät des Bindings — gewünschten "
    "Knopf/Schalter EINMAL betätigen oder den Hebel deutlich bewegen, dann werden Art "
    "(Taster/Schalter/Achse/Hat) und Code erkannt und oben eingetragen.\n\nFunktioniert für "
    "Achsen-Hardware (evdev) UND die Saitek-Panels (hidraw). Voraussetzung: das Gerät hängt am USB.": {
        "en": "Learn a control: listens live on the binding's connected device — press the desired "
              "button/switch ONCE or move the lever clearly, then the kind "
              "(button/switch/axis/hat) and code are detected and filled in above.\n\nWorks for "
              "axis hardware (evdev) AND the Saitek panels (hidraw). Requirement: the device is on USB.",
        "es": "Aprender un control: escucha en vivo el dispositivo conectado de la asignación: pulse "
              "UNA vez el botón/interruptor deseado o mueva la palanca con claridad; se detectan el "
              "tipo (botón/interruptor/eje/hat) y el código y se rellenan arriba.\n\nFunciona con "
              "hardware de ejes (evdev) Y los paneles Saitek (hidraw). Requisito: el dispositivo está en USB.",
        "fr": "Apprendre une commande : écoute en direct le périphérique connecté de la liaison — "
              "appuyez UNE fois sur le bouton/interrupteur voulu ou déplacez nettement le levier ; le "
              "type (bouton/interrupteur/axe/hat) et le code sont détectés et renseignés ci-dessus.\n\n"
              "Fonctionne pour le matériel d'axes (evdev) ET les panneaux Saitek (hidraw). "
              "Prérequis : le périphérique est branché en USB."},
    "Öffnet ein Live-Fenster, das den ROHWERT dieser Achse direkt vom angeschlossenen Gerät liest "
    "(evdev) — gelesen wird die Achse aus dem Code-Feld oben am Gerät dieses Bindings.\n\n"
    "Voraussetzung VORHER: Quelle = Achse, der Code stimmt und das Gerät hängt am USB. Dann Hebel "
    "bewegen: der aktuelle Rohwert erscheint live und lässt sich per Knopf als Eingang-min, "
    "Eingang-max oder Detent übernehmen. Es wird nichts gesendet — nur gelesen.": {
        "en": "Opens a live window that reads the RAW value of this axis directly from the connected "
              "device (evdev) — the axis is taken from the code field above on this binding's device."
              "\n\nRequirement FIRST: source = axis, the code is correct and the device is on USB. Then "
              "move the lever: the current raw value appears live and can be applied as input-min, "
              "input-max or detent with a button. Nothing is sent — only read.",
        "es": "Abre una ventana en vivo que lee el valor BRUTO de este eje directamente del "
              "dispositivo conectado (evdev): el eje se toma del campo de código de arriba del "
              "dispositivo de esta asignación.\n\nRequisito PREVIO: fuente = eje, el código es correcto "
              "y el dispositivo está en USB. Luego mueva la palanca: el valor bruto actual aparece en "
              "vivo y puede aplicarse como entrada-mín, entrada-máx o retén con un botón. No se envía "
              "nada, solo se lee.",
        "fr": "Ouvre une fenêtre en direct qui lit la valeur BRUTE de cet axe directement depuis le "
              "périphérique connecté (evdev) — l'axe provient du champ de code ci-dessus du "
              "périphérique de cette liaison.\n\nPrérequis D'ABORD : source = axe, le code est correct "
              "et le périphérique est en USB. Puis déplacez le levier : la valeur brute actuelle "
              "apparaît en direct et peut être appliquée comme entrée-min, entrée-max ou cran via un "
              "bouton. Rien n'est envoyé — seulement lu."},

    # ----- binding editor: detent learn tooltip --------------------------- #
    "Detent anlernen: liest den Rohwert der Achse live vom angeschlossenen Gerät (evdev, Achse = "
    "Code-Feld oben). Voraussetzung: Quelle = Achse, Code stimmt, Gerät angesteckt. Hebel an die "
    "Raste fahren und den angezeigten Wert mit „→ als Detent“ übernehmen.": {
        "en": "Learn a detent: reads the axis's raw value live from the connected device (evdev, axis "
              "= code field above). Requirement: source = axis, the code is correct, the device is "
              "plugged in. Move the lever to the detent and apply the shown value with “→ as detent”.",
        "es": "Aprender un retén: lee el valor bruto del eje en vivo desde el dispositivo conectado "
              "(evdev, eje = campo de código de arriba). Requisito: fuente = eje, el código es "
              "correcto, el dispositivo está conectado. Mueva la palanca al retén y aplique el valor "
              "mostrado con «→ como retén».",
        "fr": "Apprendre un cran : lit la valeur brute de l'axe en direct depuis le périphérique "
              "connecté (evdev, axe = champ de code ci-dessus). Prérequis : source = axe, le code est "
              "correct, le périphérique est branché. Amenez le levier au cran et appliquez la valeur "
              "affichée avec « → comme cran »."},

    # ----- output editor / panel blocks ----------------------------------- #
    "LED-Knopf:": {"en": "LED button:", "es": "Botón LED:", "fr": "Bouton LED :"},
    "alle LED-Knöpfe belegt": {
        "en": "all LED buttons assigned", "es": "todos los botones LED asignados",
        "fr": "tous les boutons LED attribués"},
    "Diese Gruppe hat keine direkten Felder — die Untergruppen stehen im Baum der Haupttabelle.": {
        "en": "This group has no direct fields — the sub-groups are in the main table's tree.",
        "es": "Este grupo no tiene campos directos: los subgrupos están en el árbol de la tabla principal.",
        "fr": "Ce groupe n'a pas de champs directs — les sous-groupes sont dans l'arbre du tableau principal."},
    "Diese Zeile lässt sich nicht entfernen — Einträge oder ganze Panel-Blöcke markieren.": {
        "en": "This row can't be removed — select entries or whole panel blocks.",
        "es": "Esta fila no se puede quitar: seleccione entradas o bloques de panel completos.",
        "fr": "Cette ligne ne peut pas être retirée — sélectionnez des entrées ou des blocs de panneau entiers."},
    "Diesen ganzen Panel-Block aus dem Profil entfernen?": {
        "en": "Remove this whole panel block from the profile?",
        "es": "¿Quitar todo este bloque de panel del perfil?",
        "fr": "Retirer tout ce bloc de panneau du profil ?"},
    "Panel-Block entfernen": {
        "en": "Remove panel block", "es": "Quitar bloque del panel",
        "fr": "Retirer le bloc de panneau"},
    "Neuen Panel-Controller anlegen — nur für Saitek-Panels (hidraw) und nur nötig, wenn das "
    "Profil das Panel noch gar nicht kennt. Details danach über die Baum-Zeilen einstellen.": {
        "en": "Create a new panel controller — only for Saitek panels (hidraw) and only needed when "
              "the profile doesn't know the panel yet. Set the details afterwards via the tree rows.",
        "es": "Crear un nuevo controlador de panel: solo para paneles Saitek (hidraw) y solo si el "
              "perfil aún no conoce el panel. Ajuste los detalles después mediante las filas del árbol.",
        "fr": "Créer un nouveau contrôleur de panneau — uniquement pour les panneaux Saitek (hidraw) "
              "et seulement si le profil ne connaît pas encore le panneau. Réglez ensuite les détails "
              "via les lignes de l'arbre."},

    # ----- panel window --------------------------------------------------- #
    "  ziehen = bewegen · Kacheln einrasten/tauschen · Rechtsklick = weg": {
        "en": "  drag = move · tiles snap/swap · right-click = remove",
        "es": "  arrastrar = mover · los mosaicos encajan/intercambian · clic derecho = quitar",
        "fr": "  glisser = déplacer · les tuiles s'alignent/s'échangent · clic droit = retirer"},

    # ----- Profile tab ---------------------------------------------------- #
    "Aktives Profil:": {
        "en": "Active profile:", "es": "Perfil activo:", "fr": "Profil actif :"},
    "Kein Profil": {"en": "No profile", "es": "Sin perfil", "fr": "Aucun profil"},
    "Auto-Auswahl": {"en": "Auto-select", "es": "Selección automática", "fr": "Sélection auto"},
    "Flugzeug-Titel (Komma-getrennt) — wählt dieses Profil automatisch, wenn der Titel passt.": {
        "en": "Aircraft titles (comma-separated) — auto-selects this profile when the title matches.",
        "es": "Títulos de aeronave (separados por comas): selecciona este perfil automáticamente si el título coincide.",
        "fr": "Titres d'avion (séparés par des virgules) — sélectionne ce profil automatiquement si le titre correspond."},
    "Beschreibung speichern": {
        "en": "Save description", "es": "Guardar descripción", "fr": "Enregistrer la description"},
    "Aktuelles Profil nicht gefunden.": {
        "en": "Current profile not found.", "es": "Perfil actual no encontrado.",
        "fr": "Profil actuel introuvable."},
    "Das letzte Profil kann nicht entfernt werden.": {
        "en": "The last profile can't be removed.", "es": "No se puede quitar el último perfil.",
        "fr": "Le dernier profil ne peut pas être retiré."},
    "Nicht möglich": {"en": "Not possible", "es": "No es posible", "fr": "Impossible"},
    "Ungültiger Name": {"en": "Invalid name", "es": "Nombre no válido", "fr": "Nom invalide"},
    "Nur Buchstaben, Ziffern, '_' und '-'.": {
        "en": "Only letters, digits, '_' and '-'.",
        "es": "Solo letras, dígitos, '_' y '-'.",
        "fr": "Uniquement lettres, chiffres, '_' et '-'."},
    "(leer = Standard)": {"en": "(empty = default)", "es": "(vacío = predeterminado)", "fr": "(vide = défaut)"},
    "Gespeichert ✓": {"en": "Saved ✓", "es": "Guardado ✓", "fr": "Enregistré ✓"},
    "Profil oder Geräte-Katalog nicht lesbar": {
        "en": "Profile or device catalog not readable",
        "es": "Perfil o catálogo de dispositivos ilegible",
        "fr": "Profil ou catalogue de périphériques illisible"},

    # ----- Gauges tab ----------------------------------------------------- #
    "Klick wählt · Doppelklick mappt": {
        "en": "Click selects · double-click maps",
        "es": "Clic selecciona · doble clic asigna",
        "fr": "Clic sélectionne · double-clic mappe"},
    "Aus Bibliothek löschen": {
        "en": "Delete from library", "es": "Eliminar de la biblioteca",
        "fr": "Supprimer de la bibliothèque"},
    "Erst ein Gauge anklicken.": {
        "en": "Click a gauge first.", "es": "Primero haga clic en un instrumento.",
        "fr": "Cliquez d'abord sur un instrument."},
    "Gauge vom Panel entfernt (Bibliothek unberührt).": {
        "en": "Gauge removed from the panel (library untouched).",
        "es": "Instrumento quitado del panel (biblioteca intacta).",
        "fr": "Instrument retiré du panneau (bibliothèque intacte)."},
    "Aus der Bibliothek gelöscht (Panel unberührt).": {
        "en": "Deleted from the library (panel untouched).",
        "es": "Eliminado de la biblioteca (panel intacto).",
        "fr": "Supprimé de la bibliothèque (panneau intact)."},
    "Erst rechts eine Zeile markieren.": {
        "en": "Select a row on the right first.",
        "es": "Primero seleccione una fila a la derecha.",
        "fr": "Sélectionnez d'abord une ligne à droite."},
    "Instrument hinzufügen: erst aus Bibliothek (bereits gemappte Gauges) oder Vorlage wählen, "
    "dann die Zeiger auf Variablen mappen — danach liegt es auf dem Panel.": {
        "en": "Add an instrument: first pick from the library (already-mapped gauges) or a template, "
              "then map its needles to variables — after that it sits on the panel.",
        "es": "Añadir un instrumento: elija primero de la biblioteca (instrumentos ya asignados) o una "
              "plantilla, luego asigne sus agujas a variables; después queda en el panel.",
        "fr": "Ajouter un instrument : choisissez d'abord dans la bibliothèque (instruments déjà "
              "mappés) ou un modèle, puis mappez ses aiguilles sur des variables — il se place ensuite sur le panneau."},
    "Noch keine Gauges.\n„+ Gauge“ → Vorlage/Bibliothek wählen → Zeiger auf Variablen mappen → aufs Panel.": {
        "en": "No gauges yet.\n“+ Gauge” → pick a template/library → map needles to variables → onto the panel.",
        "es": "Aún no hay instrumentos.\n«+ Instrumento» → elija plantilla/biblioteca → asigne agujas a variables → al panel.",
        "fr": "Pas encore d'instruments.\n« + Instrument » → choisir un modèle/bibliothèque → mapper les aiguilles → sur le panneau."},

    # ----- gui_mapper.py: device/detail tree labels (describe_* + kinds) --- #
    "Achse": {"en": "Axis", "es": "Eje", "fr": "Axe"},
    "Taste": {"en": "Button", "es": "Botón", "fr": "Bouton"},
    "Hat": {"en": "Hat", "es": "Hat", "fr": "Hat"},
    "Schalter": {"en": "Switch", "es": "Interruptor", "fr": "Interrupteur"},
    "verbunden": {"en": "connected", "es": "conectado", "fr": "connecté"},
    "nicht erkannt": {"en": "not detected", "es": "no detectado", "fr": "non détecté"},
    "unter": {"en": "below", "es": "debajo", "fr": "sous"},
    "Rad-LEDs": {"en": "Gear LEDs", "es": "LED de tren", "fr": "LED de train"},
    "grün ab Position": {
        "en": "green from position", "es": "verde desde posición",
        "fr": "vert à partir de la position"},
    "Power-Gate": {
        "en": "Power gate", "es": "Puerta de alimentación", "fr": "Porte d'alimentation"},
    "Schritt": {"en": "Step", "es": "Paso", "fr": "Pas"},
    "schnell": {"en": "fast", "es": "rápido", "fr": "rapide"},
    "SimVar-Write": {"en": "SimVar write", "es": "escritura de SimVar", "fr": "écriture SimVar"},
    "Selektor": {"en": "Selector", "es": "Selector", "fr": "Sélecteur"},
    "Zeile": {"en": "row", "es": "fila", "fr": "ligne"},
    "Alt-Quelle": {"en": "Alt source", "es": "Fuente alt.", "fr": "Source alt."},
    "AP-Master-LED": {"en": "AP master LED", "es": "LED maestro AP", "fr": "LED maître PA"},
    "Mode-Var": {"en": "Mode var", "es": "Variable de modo", "fr": "Variable de mode"},
    "Quellen-Umschalter": {
        "en": "Source toggle", "es": "Conmutador de fuente", "fr": "Bascule de source"},
    "Dimmer": {"en": "Dimmer", "es": "Regulador", "fr": "Variateur"},
    "nur Anzeige": {"en": "display only", "es": "solo lectura", "fr": "affichage seul"},
    "Quellen": {"en": "Sources", "es": "Fuentes", "fr": "Sources"},

    # ----- gui_mapper.py: editor field labels + help (OUTPUT_FIELD_HELP) --- #
    'Hardware-Code': {"en": 'Hardware code', "es": 'Código de hardware', "fr": 'Code matériel'},
    'Bit/Code des Schalters bzw. der Selektor-Position am Panel (gemessen, s. docs/memory/*-hid.md). Nur ändern, wenn die Hardware neu vermessen wurde.': {"en": 'Bit/code of the switch or selector position on the panel (measured, see docs/memory/*-hid.md). Only change when the hardware was re-measured.', "es": 'Bit/código del interruptor o de la posición del selector en el panel (medido, ver docs/memory/*-hid.md). Cámbielo solo si se volvió a medir el hardware.', "fr": "Bit/code de l'interrupteur ou de la position du sélecteur sur le panneau (mesuré, voir docs/memory/*-hid.md). À ne changer que si le matériel a été remesuré."},
    'Bezeichnung': {"en": 'Designation', "es": 'Denominación', "fr": 'Désignation'},
    'Menschenlesbarer Name, nur für Anzeige/Logs.': {"en": 'Human-readable name, for display/logs only.', "es": 'Nombre legible, solo para visualización/registros.', "fr": "Nom lisible, pour l'affichage/les journaux uniquement."},
    'Einheit für Lesen/Schreiben der Variable (meist number).': {"en": 'Unit for reading/writing the variable (usually number).', "es": 'Unidad para leer/escribir la variable (normalmente number).', "fr": 'Unité pour lire/écrire la variable (généralement number).'},
    'Die Sim-Variable, deren Wert angezeigt/editiert wird.': {"en": 'The sim variable whose value is shown/edited.', "es": 'La variable del sim cuyo valor se muestra/edita.', "fr": 'La variable du sim dont la valeur est affichée/éditée.'},
    'Setz-Event': {"en": 'Set event', "es": 'Evento de ajuste', "fr": 'Event de réglage'},
    'K:-Event zum Setzen des Werts; leer = Variable wird direkt geschrieben.': {"en": 'K: event to set the value; empty = the variable is written directly.', "es": 'Evento K: para fijar el valor; vacío = la variable se escribe directamente.', "fr": 'Event K: pour définir la valeur ; vide = la variable est écrite directement.'},
    'Wertänderung pro Encoder-Rastung.': {"en": 'Value change per encoder detent.', "es": 'Cambio de valor por muesca del codificador.', "fr": "Changement de valeur par cran de l'encodeur."},
    'Schnell-Schritt': {"en": 'Fast step', "es": 'Paso rápido', "fr": 'Pas rapide'},
    'Größerer Schritt, wenn der Drehknopf schnell gedreht wird. Leer = keine Beschleunigung.': {"en": 'Larger step when the dial is turned fast. Empty = no acceleration.', "es": 'Paso mayor cuando la rueda se gira rápido. Vacío = sin aceleración.', "fr": "Pas plus grand lorsque la molette tourne vite. Vide = pas d'accélération."},
    'Minimum': {"en": 'Minimum', "es": 'Mínimo', "fr": 'Minimum'},
    'Kleinster einstellbarer Wert.': {"en": 'Smallest settable value.', "es": 'Valor mínimo ajustable.', "fr": 'Plus petite valeur réglable.'},
    'Maximum': {"en": 'Maximum', "es": 'Máximo', "fr": 'Maximum'},
    'Größter einstellbarer Wert.': {"en": 'Largest settable value.', "es": 'Valor máximo ajustable.', "fr": 'Plus grande valeur réglable.'},
    'Umlauf': {"en": 'Wrap-around', "es": 'Vuelta al inicio', "fr": 'Bouclage'},
    'Am Ende zum Anfang weiterdrehen (z. B. Heading 359→0) statt anzuschlagen.': {"en": 'Wrap from the end back to the start (e.g. heading 359→0) instead of stopping.', "es": 'Al final vuelve al principio (p. ej. rumbo 359→0) en vez de detenerse.', "fr": 'Reboucle de la fin au début (p. ex. cap 359→0) au lieu de buter.'},
    'Encoder-eigen': {"en": 'Encoder-owned', "es": 'Propio del codificador', "fr": "Propre à l'encodeur"},
    'Anzeige behält den zuletzt gedrehten Wert, statt der Live-Variable zu folgen (gegen Gauges, die den Wert überschreiben).': {"en": 'The display keeps the last dialed value instead of following the live variable (against gauges that overwrite it).', "es": 'La indicación mantiene el último valor girado en vez de seguir la variable en vivo (contra instrumentos que la sobrescriben).', "fr": "L'affichage garde la dernière valeur tournée au lieu de suivre la variable en direct (contre les instruments qui l'écrasent)."},
    'Aus-Schwelle': {"en": 'Off threshold', "es": 'Umbral de apagado', "fr": "Seuil d'extinction"},
    'Live-Werte ab dieser Schwelle (oder fehlende) werden als 0 angezeigt — fängt „Aus“-Parkwerte wie 80000 ab.': {"en": "Live values at or above this threshold (or missing) show as 0 — catches 'off' park values like 80000.", "es": "Los valores en vivo iguales o mayores a este umbral (o ausentes) se muestran como 0 — atrapa valores de reposo 'apagado' como 80000.", "fr": "Les valeurs en direct au-dessus de ce seuil (ou absentes) s'affichent comme 0 — capture les valeurs de repos « éteint » comme 80000."},
    'Display-Zeile': {"en": 'Display row', "es": 'Fila del display', "fr": "Ligne d'affichage"},
    'Obere oder untere Zeile des Panel-Displays.': {"en": 'Upper or lower row of the panel display.', "es": 'Fila superior o inferior del display del panel.', "fr": "Ligne supérieure ou inférieure de l'affichage du panneau."},
    'AP-Master-Var': {"en": 'AP master var', "es": 'Variable maestra AP', "fr": 'Variable maître PA'},
    'Bool-Variable für die Autopilot-Master-LED.': {"en": 'Bool variable for the autopilot master LED.', "es": 'Variable booleana para el LED maestro del piloto automático.', "fr": 'Variable booléenne pour la LED maître du pilote automatique.'},
    'Modus-Var': {"en": 'Mode var', "es": 'Variable de modo', "fr": 'Variable de mode'},
    'Variable mit dem aktiven AP-Modus (steuert die Modus-LEDs).': {"en": 'Variable with the active AP mode (drives the mode LEDs).', "es": 'Variable con el modo AP activo (controla los LED de modo).', "fr": 'Variable du mode PA actif (pilote les LED de mode).'},
    'Bool-Variable: bei 0 bleiben Display/LEDs dunkel (z. B. Batterie aus). Leer = immer an.': {"en": 'Bool variable: at 0 the display/LEDs stay dark (e.g. battery off). Empty = always on.', "es": 'Variable booleana: en 0 el display/LED quedan apagados (p. ej. batería apagada). Vacío = siempre encendido.', "fr": "Variable booléenne : à 0 l'affichage/les LED restent éteints (p. ex. batterie coupée). Vide = toujours allumé."},
    'Geräte-ID aus config/devices.yaml (z. B. yoke).': {"en": 'Device ID from config/devices.yaml (e.g. yoke).', "es": 'ID de dispositivo de config/devices.yaml (p. ej. yoke).', "fr": 'ID de périphérique depuis config/devices.yaml (p. ex. yoke).'},
    'Code rechtsdrehen': {"en": 'Code turn right', "es": 'Código giro derecha', "fr": 'Code rotation droite'},
    'Eingabe-Code für eine Rastung im Uhrzeigersinn (heller).': {"en": 'Input code for one clockwise detent (brighter).', "es": 'Código de entrada para una muesca en sentido horario (más brillante).', "fr": "Code d'entrée pour un cran horaire (plus clair)."},
    'Code linksdrehen': {"en": 'Code turn left', "es": 'Código giro izquierda', "fr": 'Code rotation gauche'},
    'Eingabe-Code für eine Rastung gegen den Uhrzeigersinn (dunkler).': {"en": 'Input code for one counter-clockwise detent (dimmer).', "es": 'Código de entrada para una muesca antihoraria (más tenue).', "fr": "Code d'entrée pour un cran antihoraire (plus sombre)."},
    'Sim-/L-Variable, die auf den skalierten Wert gesetzt wird.': {"en": 'Sim/L variable that is set to the scaled value.', "es": 'Variable Sim/L que se fija al valor escalado.', "fr": "Variable Sim/L définie à la valeur mise à l'échelle."},
    'K:-Event, das mit dem skalierten Wert gefeuert wird.': {"en": 'K: event fired with the scaled value.', "es": 'Evento K: disparado con el valor escalado.', "fr": "Event K: déclenché avec la valeur mise à l'échelle."},
    'Vollwert': {"en": 'Full value', "es": 'Valor pleno', "fr": 'Valeur pleine'},
    'Wert der Lampe bei 100 % Helligkeit (Skala des Ziels).': {"en": "Value of the lamp at 100% brightness (target's scale).", "es": 'Valor de la lámpara al 100% de brillo (escala del objetivo).', "fr": 'Valeur de la lampe à 100 % de luminosité (échelle de la cible).'},
    'Folge-Event': {"en": 'Follow event', "es": 'Evento de seguimiento', "fr": 'Event de suivi'},
    'An/Aus-Licht, das mitschaltet, sobald der Dimmer über dem Minimum steht.': {"en": 'On/off light that switches along as soon as the dimmer is above the minimum.', "es": 'Luz de encendido/apagado que conmuta en cuanto el regulador supera el mínimo.', "fr": 'Lumière on/off qui commute dès que le variateur dépasse le minimum.'},
    'Bugrad-Var': {"en": 'Nose-gear var', "es": 'Variable tren de morro', "fr": 'Variable train avant'},
    'Positions-Variable des Bugfahrwerks (0=oben … 1=unten).': {"en": 'Position variable of the nose gear (0=up … 1=down).', "es": 'Variable de posición del tren de morro (0=arriba … 1=abajo).', "fr": 'Variable de position du train avant (0=rentré … 1=sorti).'},
    'Links-Var': {"en": 'Left var', "es": 'Variable izquierda', "fr": 'Variable gauche'},
    'Positions-Variable des linken Hauptfahrwerks.': {"en": 'Position variable of the left main gear.', "es": 'Variable de posición del tren principal izquierdo.', "fr": 'Variable de position du train principal gauche.'},
    'Rechts-Var': {"en": 'Right var', "es": 'Variable derecha', "fr": 'Variable droite'},
    'Positions-Variable des rechten Hauptfahrwerks.': {"en": 'Position variable of the right main gear.', "es": 'Variable de posición del tren principal derecho.', "fr": 'Variable de position du train principal droit.'},
    'Grün ab': {"en": 'Green from', "es": 'Verde desde', "fr": 'Vert à partir de'},
    'Ab dieser Position gilt das Rad als ausgefahren (grüne LED).': {"en": 'From this position the wheel counts as extended (green LED).', "es": 'Desde esta posición la rueda cuenta como extendida (LED verde).', "fr": 'À partir de cette position la roue compte comme sortie (LED verte).'},
    'Bezeichnung, nur für Anzeige/Logs.': {"en": 'Designation, for display/logs only.', "es": 'Denominación, solo para visualización/registros.', "fr": "Désignation, pour l'affichage/les journaux uniquement."},
    'Display-Hälfte': {"en": 'Display half', "es": 'Mitad del display', "fr": "Moitié d'affichage"},
    'Obere oder untere Hälfte des Radio-Panel-Displays.': {"en": 'Upper or lower half of the radio panel display.', "es": 'Mitad superior o inferior del display del panel de radio.', "fr": "Moitié supérieure ou inférieure de l'affichage du panneau radio."},
    'Äußerer Knopf rechts': {"en": 'Outer knob right', "es": 'Botón exterior derecha', "fr": 'Bouton extérieur droite'},
    'Eingabe-Code: äußerer (grober) Drehknopf im UZS.': {"en": 'Input code: outer (coarse) dial clockwise.', "es": 'Código de entrada: rueda exterior (gruesa) en sentido horario.', "fr": "Code d'entrée : molette extérieure (grossière) sens horaire."},
    'Äußerer Knopf links': {"en": 'Outer knob left', "es": 'Botón exterior izquierda', "fr": 'Bouton extérieur gauche'},
    'Eingabe-Code: äußerer Drehknopf gegen den UZS.': {"en": 'Input code: outer dial counter-clockwise.', "es": 'Código de entrada: rueda exterior en sentido antihorario.', "fr": "Code d'entrée : molette extérieure sens antihoraire."},
    'Innerer Knopf rechts': {"en": 'Inner knob right', "es": 'Botón interior derecha', "fr": 'Bouton intérieur droite'},
    'Eingabe-Code: innerer (feiner) Drehknopf im UZS.': {"en": 'Input code: inner (fine) dial clockwise.', "es": 'Código de entrada: rueda interior (fina) en sentido horario.', "fr": "Code d'entrée : molette intérieure (fine) sens horaire."},
    'Innerer Knopf links': {"en": 'Inner knob left', "es": 'Botón interior izquierda', "fr": 'Bouton intérieur gauche'},
    'Eingabe-Code: innerer Drehknopf gegen den UZS.': {"en": 'Input code: inner dial counter-clockwise.', "es": 'Código de entrada: rueda interior en sentido antihorario.', "fr": "Code d'entrée : molette intérieure sens antihoraire."},
    'Tausch-Knopf': {"en": 'Swap button', "es": 'Botón de intercambio', "fr": "Bouton d'échange"},
    'Eingabe-Code des Drückens (ACT↔STBY-Tausch).': {"en": 'Input code of the press (ACT↔STBY swap).', "es": 'Código de entrada de la pulsación (intercambio ACT↔STBY).', "fr": "Code d'entrée de l'appui (échange ACT↔STBY)."},
    'Aktiv-Frequenz': {"en": 'Active frequency', "es": 'Frecuencia activa', "fr": 'Fréquence active'},
    'Variable der ACTIVE-Frequenz (obere Display-Zeile).': {"en": 'Variable of the ACTIVE frequency (upper display row).', "es": 'Variable de la frecuencia ACTIVA (fila superior del display).', "fr": "Variable de la fréquence ACTIVE (ligne d'affichage supérieure)."},
    'Standby-Frequenz': {"en": 'Standby frequency', "es": 'Frecuencia standby', "fr": 'Fréquence standby'},
    'Variable der STANDBY-Frequenz (wird getunt, untere Zeile).': {"en": 'Variable of the STANDBY frequency (being tuned, lower row).', "es": 'Variable de la frecuencia STANDBY (que se sintoniza, fila inferior).', "fr": 'Variable de la fréquence STANDBY (en cours de réglage, ligne inférieure).'},
    'Tausch-Event': {"en": 'Swap event', "es": 'Evento de intercambio', "fr": "Event d'échange"},
    'Event, das ACTIVE und STANDBY tauscht.': {"en": 'Event that swaps ACTIVE and STANDBY.', "es": 'Evento que intercambia ACTIVA y STANDBY.', "fr": 'Event qui échange ACTIVE et STANDBY.'},
    'MHz hoch': {"en": 'MHz up', "es": 'MHz arriba', "fr": 'MHz haut'},
    'Event des äußeren Knopfs: ganze MHz aufwärts.': {"en": 'Outer knob event: whole MHz upward.', "es": 'Evento de la rueda exterior: MHz enteros hacia arriba.', "fr": 'Event de la molette extérieure : MHz entiers vers le haut.'},
    'MHz runter': {"en": 'MHz down', "es": 'MHz abajo', "fr": 'MHz bas'},
    'Event des äußeren Knopfs: ganze MHz abwärts.': {"en": 'Outer knob event: whole MHz downward.', "es": 'Evento de la rueda exterior: MHz enteros hacia abajo.', "fr": 'Event de la molette extérieure : MHz entiers vers le bas.'},
    'kHz hoch': {"en": 'kHz up', "es": 'kHz arriba', "fr": 'kHz haut'},
    'Event des inneren Knopfs: Fein-Schritt aufwärts.': {"en": 'Inner knob event: fine step upward.', "es": 'Evento de la rueda interior: paso fino hacia arriba.', "fr": 'Event de la molette intérieure : pas fin vers le haut.'},
    'kHz runter': {"en": 'kHz down', "es": 'kHz abajo', "fr": 'kHz bas'},
    'Event des inneren Knopfs: Fein-Schritt abwärts.': {"en": 'Inner knob event: fine step downward.', "es": 'Evento de la rueda interior: paso fino hacia abajo.', "fr": 'Event de la molette intérieure : pas fin vers le bas.'},
    'kHz hoch (schnell)': {"en": 'kHz up (fast)', "es": 'kHz arriba (rápido)', "fr": 'kHz haut (rapide)'},
    'Event bei schnellem Drehen (gröberer Schritt). Leer = wie kHz hoch.': {"en": 'Event on fast turn (coarser step). Empty = same as kHz up.', "es": 'Evento al girar rápido (paso más grueso). Vacío = igual que kHz arriba.', "fr": "Event lors d'une rotation rapide (pas plus grossier). Vide = comme kHz haut."},
    'kHz runter (schnell)': {"en": 'kHz down (fast)', "es": 'kHz abajo (rápido)', "fr": 'kHz bas (rapide)'},
    'Event bei schnellem Drehen abwärts. Leer = wie kHz runter.': {"en": 'Event on fast turn downward. Empty = same as kHz down.', "es": 'Evento al girar rápido hacia abajo. Vacío = igual que kHz abajo.', "fr": "Event lors d'une rotation rapide vers le bas. Vide = comme kHz bas."},
    'Fein-Anzeige': {"en": 'Fine view', "es": 'Vista fina', "fr": 'Vue fine'},
    'Innerer Knopf schaltet die Standby-Zeile auf 3 Nachkommastellen (nur COM 8.33 sinnvoll).': {"en": 'Inner knob switches the standby row to 3 decimals (only useful for COM 8.33).', "es": 'La rueda interior cambia la fila standby a 3 decimales (solo útil para COM 8.33).', "fr": 'La molette intérieure passe la ligne standby à 3 décimales (utile seulement pour COM 8.33).'},
    'Distanz-Var': {"en": 'Distance var', "es": 'Variable de distancia', "fr": 'Variable de distance'},
    'DME-Entfernungs-Variable (nautische Meilen).': {"en": 'DME distance variable (nautical miles).', "es": 'Variable de distancia DME (millas náuticas).', "fr": 'Variable de distance DME (milles nautiques).'},
    'Geschw.-Var': {"en": 'Speed var', "es": 'Variable de velocidad', "fr": 'Variable de vitesse'},
    'DME-Geschwindigkeits-Variable (Knoten).': {"en": 'DME speed variable (knots).', "es": 'Variable de velocidad DME (nudos).', "fr": 'Variable de vitesse DME (nœuds).'},
    'Quellen-Var': {"en": 'Source var', "es": 'Variable de fuente', "fr": 'Variable de source'},
    'LVar mit der DME-Quelle (0=NAV1, 1=NAV2) — bidirektional mit dem Cockpit-Schalter. Leer = nur lokal durchschalten.': {"en": 'LVar with the DME source (0=NAV1, 1=NAV2) — bidirectional with the cockpit switch. Empty = switch locally only.', "es": 'LVar con la fuente DME (0=NAV1, 1=NAV2) — bidireccional con el interruptor de cabina. Vacío = conmutar solo localmente.', "fr": "LVar avec la source DME (0=NAV1, 1=NAV2) — bidirectionnel avec l'interrupteur du cockpit. Vide = commuter localement seulement."},
    'Squawk-Var': {"en": 'Squawk var', "es": 'Variable de squawk', "fr": 'Variable de squawk'},
    'Variable des Transponder-Codes (BCD16).': {"en": 'Variable of the transponder code (BCD16).', "es": 'Variable del código del transpondedor (BCD16).', "fr": 'Variable du code transpondeur (BCD16).'},
    'Hunderter-Var': {"en": 'Hundreds var', "es": 'Variable de centenas', "fr": 'Variable des centaines'},
    'KR-85-Zähler der Hunderter-Gruppe (0-16).': {"en": 'KR-85 counter of the hundreds group (0-16).', "es": 'Contador KR-85 del grupo de centenas (0-16).', "fr": 'Compteur KR-85 du groupe des centaines (0-16).'},
    'Zehner-Var': {"en": 'Tens var', "es": 'Variable de decenas', "fr": 'Variable des dizaines'},
    'KR-85-Zähler der Zehnerstelle (0-9).': {"en": 'KR-85 counter of the tens digit (0-9).', "es": 'Contador KR-85 de la cifra de decenas (0-9).', "fr": 'Compteur KR-85 du chiffre des dizaines (0-9).'},
    'Einer-Var': {"en": 'Ones var', "es": 'Variable de unidades', "fr": 'Variable des unités'},
    'KR-85-Zähler der Einerstelle (0-9).': {"en": 'KR-85 counter of the ones digit (0-9).', "es": 'Contador KR-85 de la cifra de unidades (0-9).', "fr": 'Compteur KR-85 du chiffre des unités (0-9).'},
    'kHz-Minimum': {"en": 'kHz minimum', "es": 'Mínimo kHz', "fr": 'Minimum kHz'},
    'Kleinste einstellbare ADF-Frequenz.': {"en": 'Smallest settable ADF frequency.', "es": 'Frecuencia ADF mínima ajustable.', "fr": 'Plus petite fréquence ADF réglable.'},
    'kHz-Maximum': {"en": 'kHz maximum', "es": 'Máximo kHz', "fr": 'Maximum kHz'},
    'Größte einstellbare ADF-Frequenz.': {"en": 'Largest settable ADF frequency.', "es": 'Frecuencia ADF máxima ajustable.', "fr": 'Plus grande fréquence ADF réglable.'},
    'QNH-Var': {"en": 'QNH var', "es": 'Variable QNH', "fr": 'Variable QNH'},
    'Variable des Luftdrucks für die untere Zeile (inHg). Leer = Zeile bleibt dunkel.': {"en": 'Variable of the air pressure for the lower row (inHg). Empty = row stays dark.', "es": 'Variable de la presión atmosférica para la fila inferior (inHg). Vacío = la fila queda apagada.', "fr": 'Variable de la pression pour la ligne inférieure (inHg). Vide = la ligne reste éteinte.'},
    'QNH-Faktor': {"en": 'QNH factor', "es": 'Factor QNH', "fr": 'Facteur QNH'},
    'Multiplikator der QNH-Var nach inHg (schon inHg = 1).': {"en": 'Multiplier of the QNH var to inHg (already inHg = 1).', "es": 'Multiplicador de la variable QNH a inHg (ya en inHg = 1).', "fr": 'Multiplicateur de la variable QNH vers inHg (déjà en inHg = 1).'},
    'QNH hoch': {"en": 'QNH up', "es": 'QNH arriba', "fr": 'QNH haut'},
    'Event des äußeren Knopfs: Luftdruck aufwärts.': {"en": 'Outer knob event: air pressure upward.', "es": 'Evento de la rueda exterior: presión hacia arriba.', "fr": 'Event de la molette extérieure : pression vers le haut.'},
    'QNH runter': {"en": 'QNH down', "es": 'QNH abajo', "fr": 'QNH bas'},
    'Event des äußeren Knopfs: Luftdruck abwärts.': {"en": 'Outer knob event: air pressure downward.', "es": 'Evento de la rueda exterior: presión hacia abajo.', "fr": 'Event de la molette extérieure : pression vers le bas.'},
    'Selektor-Positionen': {"en": 'Selector positions', "es": 'Posiciones del selector', "fr": 'Positions du sélecteur'},
    'Alternativ-Quellen': {"en": 'Alternative sources', "es": 'Fuentes alternativas', "fr": 'Sources alternatives'},
    'LEDs (Var-gesteuert)': {"en": 'LEDs (variable-driven)', "es": 'LED (controlados por variable)', "fr": 'LED (pilotées par variable)'},
    'Dimmer-Ziele': {"en": 'Dimmer targets', "es": 'Objetivos del regulador', "fr": 'Cibles du variateur'},
    'Radio-Einheiten': {"en": 'Radio units', "es": 'Unidades de radio', "fr": 'Unités radio'},
    'Bänke (Selektor)': {"en": 'Banks (selector)', "es": 'Bancos (selector)', "fr": 'Bancs (sélecteur)'},
    'DME-Quellen': {"en": 'DME sources', "es": 'Fuentes DME', "fr": 'Sources DME'},
    'Position': {"en": 'Position', "es": 'Posición', "fr": 'Position'},
    'Bank': {"en": 'Bank', "es": 'Banco', "fr": 'Banc'},
    'Ziel': {"en": 'Target', "es": 'Objetivo', "fr": 'Cible'},
    'LED Bugrad': {"en": 'LED nose gear', "es": 'LED tren de morro', "fr": 'LED train avant'},
    'LED links': {"en": 'LED left', "es": 'LED izquierda', "fr": 'LED gauche'},
    'LED rechts': {"en": 'LED right', "es": 'LED derecha', "fr": 'LED droite'},
    'Anzeige (LED)': {"en": 'Display (LED)', "es": 'Indicación (LED)', "fr": 'Affichage (LED)'},
    'Eingabe→Anzeige': {"en": 'Input→display', "es": 'Entrada→indicación', "fr": 'Entrée→affichage'},
    'Anzeige-Quelle': {"en": 'Display source', "es": 'Fuente de indicación', "fr": "Source d'affichage"},
    'Eingabe (Drehrad)': {"en": 'Input (dial)', "es": 'Entrada (rueda)', "fr": 'Entrée (molette)'},
    'Anzeige (Licht)': {"en": 'Display (light)', "es": 'Indicación (luz)', "fr": 'Affichage (lumière)'},
    'Eingabe': {"en": 'Input', "es": 'Entrada', "fr": 'Entrée'},
    'Anzeige': {"en": 'Display', "es": 'Indicación', "fr": 'Affichage'},

    # ----- gui_mapper.py: editor validation messages --------------------- #
    "{label} muss eine ganze Zahl sein.": {"en": "{label} must be a whole number.", "es": "{label} debe ser un número entero.", "fr": "{label} doit être un entier."},
    "{label} muss eine Zahl sein.": {"en": "{label} must be a number.", "es": "{label} debe ser un número.", "fr": "{label} doit être un nombre."},
    "Sequence-Schritt: Name fehlt.": {"en": "Sequence step: name is missing.", "es": "Paso de secuencia: falta el nombre.", "fr": "Étape de séquence : nom manquant."},
    "Sequence braucht mindestens einen on-Schritt.": {"en": "A sequence needs at least one on-step.", "es": "Una secuencia necesita al menos un paso 'on'.", "fr": "Une séquence nécessite au moins une étape « on »."},
    "Hat: mindestens eine Richtung (▲▼◀▶) belegen.": {"en": "Hat: assign at least one direction (▲▼◀▶).", "es": "Hat: asigne al menos una dirección (▲▼◀▶).", "fr": "Hat : attribuez au moins une direction (▲▼◀▶)."},
    "Event-Name fehlt.": {"en": "Event name is missing.", "es": "Falta el nombre del evento.", "fr": "Nom de l'event manquant."},
    "SimVar-Name fehlt.": {"en": "SimVar name is missing.", "es": "Falta el nombre del SimVar.", "fr": "Nom du SimVar manquant."},
    "event_from_var braucht 'read' und 'event'.": {"en": "event_from_var needs 'read' and 'event'.", "es": "event_from_var necesita 'read' y 'event'.", "fr": "event_from_var nécessite « read » et « event »."},
    "RPN-Ausdruck fehlt.": {"en": "RPN expression is missing.", "es": "Falta la expresión RPN.", "fr": "Expression RPN manquante."},
    "Sequence kann inline (noch) nicht angelegt werden.": {"en": "A sequence can't (yet) be created inline.", "es": "Una secuencia no se puede crear en línea (todavía).", "fr": "Une séquence ne peut pas (encore) être créée en ligne."},
    "Unbekannter Aktions-Typ: {atype}": {"en": "Unknown action type: {atype}", "es": "Tipo de acción desconocido: {atype}", "fr": "Type d'action inconnu : {atype}"},
    "Name darf nicht leer sein.": {"en": "Name must not be empty.", "es": "El nombre no puede estar vacío.", "fr": "Le nom ne doit pas être vide."},
    "Unbekannte Quell-Art: {kind}": {"en": "Unknown source kind: {kind}", "es": "Tipo de fuente desconocido: {kind}", "fr": "Type de source inconnu : {kind}"},
    "Split: Aktions-Typ '{atype}' geht unterhalb des Detents nicht.": {"en": "Split: action type '{atype}' isn't allowed below the detent.", "es": "División: el tipo de acción '{atype}' no es posible por debajo del retén.", "fr": "Division : le type d'action « {atype} » n'est pas possible sous le cran."},
    "{name}: Wert fehlt.": {"en": "{name}: value is missing.", "es": "{name}: falta el valor.", "fr": "{name} : valeur manquante."},
    "{name}: muss eins von {choices} sein.": {"en": "{name}: must be one of {choices}.", "es": "{name}: debe ser uno de {choices}.", "fr": "{name} : doit être l'un de {choices}."},
    "{name}: ja/nein erwartet.": {"en": "{name}: yes/no expected.", "es": "{name}: se esperaba sí/no.", "fr": "{name} : oui/non attendu."},
    "Bedingung: Variable fehlt (über Wählen… setzen).": {"en": "Condition: variable is missing (set it via Choose…).", "es": "Condición: falta la variable (defínala con Elegir…).", "fr": "Condition : variable manquante (définissez-la via Choisir…)."},
    "Bedingung: unbekannter Vergleich '{op}'.": {"en": "Condition: unknown comparison '{op}'.", "es": "Condición: comparación desconocida '{op}'.", "fr": "Condition : comparaison inconnue « {op} »."},
}
