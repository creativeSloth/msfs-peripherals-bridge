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
        "de": "Steuerung & Status",
        "en": "Control & status",
        "es": "Control y estado",
        "fr": "Contrôle et état",
    },
    "conn.subtab.log": {
        "de": "Bridge-Protokoll",
        "en": "Bridge log",
        "es": "Registro del puente",
        "fr": "Journal du pont",
    },
    # ----- Connection tab: process group ---------------------------------- #
    "conn.group.processes": {
        "de": "Prozesse",
        "en": "Processes",
        "es": "Procesos",
        "fr": "Processus",
    },
    "conn.bridge": {"de": "Bridge", "en": "Bridge", "es": "Puente", "fr": "Pont"},
    "conn.mapper": {"de": "Mapper", "en": "Mapper", "es": "Mapeo", "fr": "Mappage"},
    "conn.start": {"de": "Starten", "en": "Start", "es": "Iniciar", "fr": "Démarrer"},
    "conn.stop": {"de": "Stoppen", "en": "Stop", "es": "Detener", "fr": "Arrêter"},
    "conn.stop_all": {
        "de": "Alles stoppen (Aufräumen)",
        "en": "Stop everything (clean up)",
        "es": "Detener todo (limpiar)",
        "fr": "Tout arrêter (nettoyer)",
    },
    "conn.start_all": {
        "de": "Alles starten (Bridge + Mapper)",
        "en": "Start everything (bridge + mapper)",
        "es": "Iniciar todo (puente + mapeo)",
        "fr": "Tout démarrer (pont + mappage)",
    },
    "conn.start_all_no_port": {
        "de": "Die Bridge lauscht noch nicht auf Port 7842 — der Mapper wurde NICHT "
        "gestartet. Läuft MSFS mit geladenem Flug? Dann „Alles starten“ erneut klicken "
        "(oder nur den Mapper starten).",
        "en": "The bridge is not listening on port 7842 yet — the mapper was NOT "
        "started. Is MSFS running with a flight loaded? Then click “Start everything” "
        "again (or start just the mapper).",
        "es": "El puente aún no escucha en el puerto 7842: el mapeo NO se inició. "
        "¿MSFS está en marcha con un vuelo cargado? Pulsa «Iniciar todo» de nuevo.",
        "fr": "Le pont n'écoute pas encore sur le port 7842 — le mappage n'a PAS "
        "démarré. MSFS tourne-t-il avec un vol chargé ? Recliquez « Tout démarrer ».",
    },
    "conn.single_client_note": {
        "de": "Die Bridge ist single-client — Mapper ODER ein Werkzeug.",
        "en": "The bridge is single-client — the mapper OR one tool.",
        "es": "El puente es de un solo cliente: el mapeo O una herramienta.",
        "fr": "Le pont est mono-client — le mappage OU un outil.",
    },
    # ----- Connection tab: environment / prerequisites -------------------- #
    "conn.group.environment": {
        "de": "Umgebung & Voraussetzungen",
        "en": "Environment & prerequisites",
        "es": "Entorno y requisitos",
        "fr": "Environnement et prérequis",
    },
    "conn.prefix_label": {
        "de": "MSFS-Proton-Prefix",
        "en": "MSFS Proton prefix",
        "es": "Prefijo Proton de MSFS",
        "fr": "Préfixe Proton de MSFS",
    },
    "conn.prefix_hint": {
        "de": "Pfad zum Proton-Prefix (…/compatdata/<AppID>/pfx). Leer = Standard "
        "(automatische Steam-Erkennung).",
        "en": "Path to the Proton prefix (…/compatdata/<AppID>/pfx). Empty = default "
        "(automatic Steam detection).",
        "es": "Ruta al prefijo Proton (…/compatdata/<AppID>/pfx). Vacío = predeterminado "
        "(detección automática de Steam).",
        "fr": "Chemin du préfixe Proton (…/compatdata/<AppID>/pfx). Vide = défaut "
        "(détection automatique de Steam).",
    },
    "conn.browse": {"de": "Durchsuchen…", "en": "Browse…", "es": "Examinar…", "fr": "Parcourir…"},
    "conn.detect": {"de": "Suchen…", "en": "Detect…", "es": "Detectar…", "fr": "Détecter…"},
    "conn.detect_title": {
        "de": "Prefix suchen",
        "en": "Detect prefix",
        "es": "Detectar prefijo",
        "fr": "Détecter le préfixe",
    },
    "conn.detect_none": {
        "de": "Kein MSFS-Prefix gefunden. Wurde MSFS über Steam+Proton schon einmal "
        "gestartet? Sonst den Pfad per „Durchsuchen…“ wählen.",
        "en": "No MSFS prefix found. Has MSFS been started once via Steam+Proton? "
        "Otherwise pick the path via “Browse…”.",
        "es": "No se encontró prefijo de MSFS. ¿Se inició MSFS con Steam+Proton? "
        "Si no, elige la ruta con «Examinar…».",
        "fr": "Aucun préfixe MSFS trouvé. MSFS a-t-il été lancé via Steam+Proton ? "
        "Sinon, choisissez le chemin via « Parcourir… ».",
    },
    "conn.detect_multi": {
        "de": "Mehrere Prefixe gefunden — wähle das richtige:",
        "en": "Several prefixes found — pick the right one:",
        "es": "Varios prefijos encontrados: elige el correcto:",
        "fr": "Plusieurs préfixes trouvés — choisissez le bon :",
    },
    "conn.detect_found": {
        "de": "Prefix gesetzt: {path}",
        "en": "Prefix set: {path}",
        "es": "Prefijo establecido: {path}",
        "fr": "Préfixe défini : {path}",
    },
    "conn.save": {"de": "Speichern", "en": "Save", "es": "Guardar", "fr": "Enregistrer"},
    "conn.recheck": {
        "de": "Erneut prüfen",
        "en": "Re-check",
        "es": "Volver a comprobar",
        "fr": "Revérifier",
    },
    "conn.setup_prefix": {
        "de": "Prefix einrichten…",
        "en": "Set up prefix…",
        "es": "Configurar prefijo…",
        "fr": "Configurer le préfixe…",
    },
    "conn.prereq_title": {
        "de": "Voraussetzungen",
        "en": "Prerequisites",
        "es": "Requisitos",
        "fr": "Prérequis",
    },
    "conn.prereq_all_ok": {
        "de": "Alle Voraussetzungen erfüllt.",
        "en": "All prerequisites met.",
        "es": "Todos los requisitos cumplidos.",
        "fr": "Tous les prérequis satisfaits.",
    },
    "conn.prereq_problems": {
        "de": "{n} Problem(e) — Bridge kann so nicht starten.",
        "en": "{n} problem(s) — the bridge cannot start like this.",
        "es": "{n} problema(s): el puente no puede iniciarse así.",
        "fr": "{n} problème(s) — le pont ne peut pas démarrer ainsi.",
    },
    "conn.log_label": {
        "de": "Bridge-Protokoll (Wine-Ebene, live)",
        "en": "Bridge log (Wine layer, live)",
        "es": "Registro del puente (capa Wine, en vivo)",
        "fr": "Journal du pont (couche Wine, en direct)",
    },
    # ----- prerequisite check item names (env_check.CheckItem.key) -------- #
    "check.prefix": {
        "de": "Proton-Prefix vorhanden",
        "en": "Proton prefix present",
        "es": "Prefijo Proton presente",
        "fr": "Préfixe Proton présent",
    },
    "check.drive_c": {
        "de": "Windows-Laufwerk (drive_c)",
        "en": "Windows drive (drive_c)",
        "es": "Unidad de Windows (drive_c)",
        "fr": "Lecteur Windows (drive_c)",
    },
    "check.pythonw": {
        "de": "Windows-Python (pythonw.exe)",
        "en": "Windows Python (pythonw.exe)",
        "es": "Python de Windows (pythonw.exe)",
        "fr": "Python Windows (pythonw.exe)",
    },
    "check.python": {
        "de": "Windows-Python (python.exe)",
        "en": "Windows Python (python.exe)",
        "es": "Python de Windows (python.exe)",
        "fr": "Python Windows (python.exe)",
    },
    "check.simconnect": {
        "de": "SimConnect.dll",
        "en": "SimConnect.dll",
        "es": "SimConnect.dll",
        "fr": "SimConnect.dll",
    },
    "check.proton": {
        "de": "Proton-Laufzeit",
        "en": "Proton runtime",
        "es": "Entorno de ejecución Proton",
        "fr": "Environnement Proton",
    },
    "check.run_bridge": {
        "de": "Bridge-Startskript (run-bridge.sh)",
        "en": "Bridge launcher (run-bridge.sh)",
        "es": "Lanzador del puente (run-bridge.sh)",
        "fr": "Lanceur du pont (run-bridge.sh)",
    },
    "check.bridge_py": {
        "de": "Bridge-Programm (bridge.py)",
        "en": "Bridge program (bridge.py)",
        "es": "Programa del puente (bridge.py)",
        "fr": "Programme du pont (bridge.py)",
    },
    # ----- Settings tab --------------------------------------------------- #
    "settings.title": {
        "de": "Einstellungen",
        "en": "Settings",
        "es": "Ajustes",
        "fr": "Paramètres",
    },
    "settings.language_group": {"de": "Sprache", "en": "Language", "es": "Idioma", "fr": "Langue"},
    "settings.language_label": {
        "de": "GUI-Sprache",
        "en": "GUI language",
        "es": "Idioma de la interfaz",
        "fr": "Langue de l'interface",
    },
    "settings.language_hint": {
        "de": "Die Auswahl wird sofort gespeichert und beim Neustart der GUI angewendet.",
        "en": "The choice is saved immediately and applied when the GUI restarts.",
        "es": "La elección se guarda al instante y se aplica al reiniciar la interfaz.",
        "fr": "Le choix est enregistré aussitôt et appliqué au redémarrage de l'interface.",
    },
    "settings.apply_restart": {
        "de": "Anwenden & GUI neu starten",
        "en": "Apply & restart GUI",
        "es": "Aplicar y reiniciar la interfaz",
        "fr": "Appliquer et redémarrer l'interface",
    },
    "settings.restart_needed": {
        "de": "Neustart erforderlich, um die Sprache vollständig anzuwenden.",
        "en": "A restart is required to fully apply the language.",
        "es": "Se requiere reiniciar para aplicar el idioma por completo.",
        "fr": "Un redémarrage est nécessaire pour appliquer pleinement la langue.",
    },
    # ----- Settings: which tabs are shown --------------------------------- #
    "settings.tabs_group": {
        "de": "Angezeigte Tabs",
        "en": "Shown tabs",
        "es": "Pestañas mostradas",
        "fr": "Onglets affichés",
    },
    "settings.tab_gauges": {
        "de": "Instrumente-Tab (Gauges)",
        "en": "Instruments tab (Gauges)",
        "es": "Pestaña de instrumentos (Gauges)",
        "fr": "Onglet instruments (Gauges)",
    },
    "settings.tab_gauges_hint": {
        "de": "Zeigt die aus Air Manager übernommenen Rundinstrumente. Standard: aus.",
        "en": "Shows the round instruments ported from Air Manager. Default: off.",
        "es": "Muestra los instrumentos redondos portados de Air Manager. Predet.: apagado.",
        "fr": "Affiche les instruments ronds portés d'Air Manager. Défaut : désactivé.",
    },
    # ----- Settings: backup / restore ------------------------------------- #
    "settings.backup_group": {
        "de": "Sichern & Wiederherstellen",
        "en": "Backup & restore",
        "es": "Copia de seguridad y restauración",
        "fr": "Sauvegarde et restauration",
    },
    "settings.backup_hint": {
        "de": "Bündelt deine Mappings (profiles/), die Kalibrierung und alle "
        "GUI-Daten (Anordnung, eigene Geräte, Vorlagen) in eine .zip — für "
        "Neu-Clone, Rechnerwechsel oder als Sicherung.",
        "en": "Bundles your mappings (profiles/), calibration and all GUI data "
        "(arrangement, registered devices, templates) into one .zip — for a "
        "re-clone, a machine move, or a plain backup.",
        "es": "Agrupa tus asignaciones (profiles/), la calibración y todos los datos "
        "de la interfaz en un .zip: para reclonar, cambiar de equipo o respaldar.",
        "fr": "Regroupe vos mappings (profiles/), la calibration et toutes les données "
        "de l'interface dans un .zip — reclonage, changement de machine ou sauvegarde.",
    },
    "settings.backup_export": {
        "de": "Exportieren…",
        "en": "Export…",
        "es": "Exportar…",
        "fr": "Exporter…",
    },
    "settings.backup_import": {
        "de": "Importieren…",
        "en": "Import…",
        "es": "Importar…",
        "fr": "Importer…",
    },
    "settings.backup_export_done": {
        "de": "Backup gespeichert: {path}\n({n} Profile, {u} GUI-Dateien).",
        "en": "Backup saved: {path}\n({n} profiles, {u} GUI files).",
        "es": "Copia guardada: {path}\n({n} perfiles, {u} archivos de interfaz).",
        "fr": "Sauvegarde enregistrée : {path}\n({n} profils, {u} fichiers d'interface).",
    },
    "settings.backup_import_confirm": {
        "de": "Backup wiederherstellen? Passende Profile und GUI-Daten werden überschrieben.",
        "en": "Restore the backup? Matching profiles and GUI data will be overwritten.",
        "es": "¿Restaurar la copia? Se sobrescribirán los perfiles y datos coincidentes.",
        "fr": "Restaurer la sauvegarde ? Les profils et données correspondants seront écrasés.",
    },
    "settings.backup_import_done": {
        "de": "Wiederhergestellt: {n} Profile, {u} GUI-Dateien.",
        "en": "Restored: {n} profiles, {u} GUI files.",
        "es": "Restaurado: {n} perfiles, {u} archivos de interfaz.",
        "fr": "Restauré : {n} profils, {u} fichiers d'interface.",
    },
    # ----- status bar ----------------------------------------------------- #
    "status.label": {"de": "Status:", "en": "Status:", "es": "Estado:", "fr": "État :"},
    "status.profile": {"de": "Profil:", "en": "Profile:", "es": "Perfil:", "fr": "Profil :"},
    # ----- shared dialog strings ------------------------------------------ #
    "dialog.confirm": {"de": "Bestätigen", "en": "Confirm", "es": "Confirmar", "fr": "Confirmer"},
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
        "(téléchargement, quelques minutes). Démarrer maintenant ?",
    },
    "conn.setup_running": {
        "de": "Prefix-Einrichtung läuft — Fortschritt im Fenster. Danach „Erneut prüfen“.",
        "en": "Prefix setup is running — see the window for progress. Then “Re-check”.",
        "es": "La configuración del prefijo está en curso; vea el progreso. Luego «Comprobar».",
        "fr": "Configuration du préfixe en cours — voir la fenêtre. Ensuite « Revérifier ».",
    },
    "conn.setup_title": {
        "de": "Prefix-Einrichtung",
        "en": "Prefix setup",
        "es": "Configuración del prefijo",
        "fr": "Configuration du préfixe",
    },
    # ----- device access (udev) rules installer --------------------------- #
    "udev.label": {
        "de": "Geräte lesbar (udev):",
        "en": "Devices readable (udev):",
        "es": "Dispositivos legibles (udev):",
        "fr": "Périphériques lisibles (udev) :",
    },
    "udev.button": {
        "de": "Geräte freischalten…",
        "en": "Enable devices…",
        "es": "Habilitar dispositivos…",
        "fr": "Activer les périphériques…",
    },
    "udev.installed": {
        "de": "✓ installiert",
        "en": "✓ installed",
        "es": "✓ instalado",
        "fr": "✓ installé",
    },
    "udev.not_installed": {
        "de": "✗ nicht installiert",
        "en": "✗ not installed",
        "es": "✗ no instalado",
        "fr": "✗ non installé",
    },
    "udev.title": {
        "de": "Geräte freischalten (udev)",
        "en": "Enable devices (udev)",
        "es": "Habilitar dispositivos (udev)",
        "fr": "Activer les périphériques (udev)",
    },
    "udev.confirm": {
        "de": "Die udev-Regeln installieren, damit die App deine Panels/den Yoke "
        "lesen darf? Es erscheint eine Passwort-Abfrage.",
        "en": "Install the udev rules so the app may read your panels/yoke? "
        "A password prompt will appear.",
        "es": "¿Instalar las reglas udev para que la app pueda leer tus paneles/yugo? "
        "Aparecerá una solicitud de contraseña.",
        "fr": "Installer les règles udev pour que l'app puisse lire vos panneaux/yoke ? "
        "Une demande de mot de passe apparaîtra.",
    },
    "udev.running": {
        "de": "Geräte-Regeln werden installiert — eine grafische Passwort-Abfrage "
        "sollte erscheinen. Danach die Geräte einmal ab- und anstecken.",
        "en": "Installing device rules — a graphical password prompt should appear. "
        "Afterwards, unplug and replug your devices once.",
        "es": "Instalando reglas de dispositivos — debería aparecer una solicitud de "
        "contraseña. Después, desconecta y reconecta los dispositivos una vez.",
        "fr": "Installation des règles — une demande de mot de passe devrait apparaître. "
        "Ensuite, débranchez puis rebranchez vos périphériques une fois.",
    },
    "udev.no_pkexec": {
        "de": "Keine grafische Rechte-Abfrage (pkexec) gefunden. Bitte im Terminal "
        "ausführen:\n\n    sudo ./tools/install-udev-rules.sh",
        "en": "No graphical privilege prompt (pkexec) found. Please run this in a "
        "terminal instead:\n\n    sudo ./tools/install-udev-rules.sh",
        "es": "No se encontró pkexec. Ejecuta esto en una terminal:\n\n"
        "    sudo ./tools/install-udev-rules.sh",
        "fr": "pkexec introuvable. Exécutez ceci dans un terminal :\n\n"
        "    sudo ./tools/install-udev-rules.sh",
    },
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
        "fr": "Liste de valeurs en direct — rassemblez les variables à observer :",
    },
    "(Event)": {"en": "(event)", "es": "(evento)", "fr": "(événement)"},
    "Panel öffnen": {"en": "Open panel", "es": "Abrir panel", "fr": "Ouvrir le panneau"},
    "Panel schließen": {"en": "Close panel", "es": "Cerrar panel", "fr": "Fermer le panneau"},
    "Variablen in die Liste holen": {
        "en": "Add variables to the list",
        "es": "Añadir variables a la lista",
        "fr": "Ajouter des variables à la liste",
    },
    "Variablen aus Liste entfernen": {
        "en": "Remove variables from list",
        "es": "Quitar variables de la lista",
        "fr": "Retirer des variables de la liste",
    },
    "Popup: nach Typ (A:/K:/L:/V:) filtern + Namen suchen": {
        "en": "Popup: filter by type (A:/K:/L:/V:) + search names",
        "es": "Ventana: filtrar por tipo (A:/K:/L:/V:) + buscar nombres",
        "fr": "Fenêtre : filtrer par type (A:/K:/L:/V:) + rechercher des noms",
    },
    "Loslösbares Kachel-Panel öffnen/schließen (mit eigenem Picker)": {
        "en": "Open/close the detachable tile panel (with its own picker)",
        "es": "Abrir/cerrar el panel de mosaicos (con su propio selector)",
        "fr": "Ouvrir/fermer le panneau de tuiles détachable (avec son sélecteur)",
    },
    "Eigene V:-Variablen (Bridge-Hub, sim-unabhängig)": {
        "en": "Own V: variables (bridge hub, sim-independent)",
        "es": "Variables V: propias (concentrador del puente, independiente del sim)",
        "fr": "Variables V: propres (concentrateur du pont, indépendant du sim)",
    },
    "Name (V:…)": {"en": "Name (V:…)", "es": "Nombre (V:…)", "fr": "Nom (V:…)"},
    "Name fehlt.": {"en": "Name is missing.", "es": "Falta el nombre.", "fr": "Nom manquant."},
    "Startwert muss eine Zahl sein.": {
        "en": "Initial value must be a number.",
        "es": "El valor inicial debe ser un número.",
        "fr": "La valeur initiale doit être un nombre.",
    },
    "Erst eine V:-Variable markieren.": {
        "en": "Select a V: variable first.",
        "es": "Primero seleccione una variable V:.",
        "fr": "Sélectionnez d'abord une variable V:.",
    },
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
        "en": "✕ Remove entry",
        "es": "✕ Quitar entrada",
        "fr": "✕ Retirer l'entrée",
    },
    "✕ Panel-Block entfernen": {
        "en": "✕ Remove panel block",
        "es": "✕ Quitar bloque del panel",
        "fr": "✕ Retirer le bloc de panneau",
    },
    "✎ Mappen": {"en": "✎ Map", "es": "✎ Asignar", "fr": "✎ Mapper"},
    "Kachel entfernen": {"en": "Remove tile", "es": "Quitar mosaico", "fr": "Retirer la tuile"},
    # ----- Mapper tab ----------------------------------------------------- #
    "Geräte im Profil — was ist worauf gemappt:": {
        "en": "Devices in the profile — what is mapped where:",
        "es": "Dispositivos del perfil: qué está asignado a qué:",
        "fr": "Périphériques du profil — ce qui est mappé où :",
    },
    "Geräte neu erkennen": {
        "en": "Re-detect devices",
        "es": "Volver a detectar dispositivos",
        "fr": "Redétecter les périphériques",
    },
    "evdev + hidraw discovery — welche Geräte hängen jetzt dran": {
        "en": "evdev + hidraw discovery — which devices are connected now",
        "es": "detección evdev + hidraw: qué dispositivos están conectados ahora",
        "fr": "détection evdev + hidraw — quels périphériques sont connectés maintenant",
    },
    "Kein Gerät gewählt — links ein Gerät markieren.": {
        "en": "No device selected — select one on the left.",
        "es": "Ningún dispositivo seleccionado: elija uno a la izquierda.",
        "fr": "Aucun périphérique sélectionné — choisissez-en un à gauche.",
    },
    "Doppelklick auf eine Zeile öffnet den Editor · Entfernen wirkt auf die markierte Zeile": {
        "en": "Double-click a row to open the editor · Remove acts on the selected row",
        "es": "Doble clic en una fila abre el editor · Quitar actúa sobre la fila seleccionada",
        "fr": "Double-clic sur une ligne ouvre l'éditeur · Retirer agit sur la ligne sélectionnée",
    },
    # ----- binding editor ------------------------------------------------- #
    "Eingang (roh)": {"en": "Input (raw)", "es": "Entrada (bruto)", "fr": "Entrée (brut)"},
    "Ausgang (out)": {"en": "Output (out)", "es": "Salida (out)", "fr": "Sortie (out)"},
    "Detent (roh)": {"en": "Detent (raw)", "es": "Retén (bruto)", "fr": "Cran (brut)"},
    "Achse am Detent teilen": {
        "en": "Split axis at the detent",
        "es": "Dividir el eje en el retén",
        "fr": "Diviser l'axe au cran",
    },
    "⬇ Unterhalb des Detents — eigene Aktion": {
        "en": "⬇ Below the detent — its own action",
        "es": "⬇ Por debajo del retén: su propia acción",
        "fr": "⬇ Sous le cran — sa propre action",
    },
    "→ als min": {"en": "→ as min", "es": "→ como mín", "fr": "→ comme min"},
    "→ als max": {"en": "→ as max", "es": "→ como máx", "fr": "→ comme max"},
    "→ als Detent": {"en": "→ as detent", "es": "→ como retén", "fr": "→ comme cran"},
    "Hat — vier Richtungen, ein Binding": {
        "en": "Hat — four directions, one binding",
        "es": "Hat: cuatro direcciones, una asignación",
        "fr": "Hat — quatre directions, une liaison",
    },
    "Hebel/Achse bewegen — aktueller Rohwert:": {
        "en": "Move the lever/axis — current raw value:",
        "es": "Mueva la palanca/eje: valor bruto actual:",
        "fr": "Déplacez le levier/axe — valeur brute actuelle :",
    },
    "Hebel an ein Ende / an die Raste fahren, Wert ablesen und übernehmen. „als Detent“ "
    "füllt die Split-Grenze (Achse teilen).": {
        "en": "Move the lever to an end / to the detent, read the value and apply it. "
        "“as detent” fills the split boundary (axis split).",
        "es": "Mueva la palanca a un extremo / al retén, lea el valor y aplíquelo. "
        "«como retén» rellena el límite de división (dividir eje).",
        "fr": "Amenez le levier à une extrémité / au cran, lisez la valeur et appliquez-la. "
        "« comme cran » remplit la limite de division (division de l'axe).",
    },
    "mehrere Schritte je Flanke — unten bearbeiten ↓": {
        "en": "several steps per edge — edit below ↓",
        "es": "varios pasos por flanco: editar abajo ↓",
        "fr": "plusieurs étapes par front — éditer ci-dessous ↓",
    },
    "Sequence — mehrere Schritte je Flanke (Event feuern / SimVar setzen):": {
        "en": "Sequence — several steps per edge (fire event / set SimVar):",
        "es": "Secuencia: varios pasos por flanco (disparar evento / fijar SimVar):",
        "fr": "Séquence — plusieurs étapes par front (déclencher un event / définir un SimVar) :",
    },
    "⚑ Bedingung — nur ausführen, wenn …": {
        "en": "⚑ Condition — only run when …",
        "es": "⚑ Condición: ejecutar solo cuando …",
        "fr": "⚑ Condition — exécuter seulement si …",
    },
    "keine — gilt immer": {
        "en": "none — always applies",
        "es": "ninguna: siempre se aplica",
        "fr": "aucune — s'applique toujours",
    },
    "Kein Binding gewählt — rechts eine Binding-Zeile markieren.": {
        "en": "No binding selected — select a binding row on the right.",
        "es": "Ninguna asignación seleccionada: elija una fila a la derecha.",
        "fr": "Aucune liaison sélectionnée — sélectionnez une ligne à droite.",
    },
    "Binding dupliziert ✓": {
        "en": "Binding duplicated ✓",
        "es": "Asignación duplicada ✓",
        "fr": "Liaison dupliquée ✓",
    },
    "Binding entfernt ✓": {
        "en": "Binding removed ✓",
        "es": "Asignación quitada ✓",
        "fr": "Liaison retirée ✓",
    },
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
        "Prérequis : le périphérique est branché en USB.",
    },
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
        "bouton. Rien n'est envoyé — seulement lu.",
    },
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
        "affichée avec « → comme cran ».",
    },
    # ----- output editor / panel blocks ----------------------------------- #
    "LED-Knopf:": {"en": "LED button:", "es": "Botón LED:", "fr": "Bouton LED :"},
    "alle LED-Knöpfe belegt": {
        "en": "all LED buttons assigned",
        "es": "todos los botones LED asignados",
        "fr": "tous les boutons LED attribués",
    },
    "Diese Gruppe hat keine direkten Felder — die Untergruppen stehen im Baum der Haupttabelle.": {
        "en": "This group has no direct fields — the sub-groups are in the main table's tree.",
        "es": "Este grupo no tiene campos directos: los subgrupos están en el árbol de la tabla principal.",
        "fr": "Ce groupe n'a pas de champs directs — les sous-groupes sont dans l'arbre du tableau principal.",
    },
    "Diese Zeile lässt sich nicht entfernen — Einträge oder ganze Panel-Blöcke markieren.": {
        "en": "This row can't be removed — select entries or whole panel blocks.",
        "es": "Esta fila no se puede quitar: seleccione entradas o bloques de panel completos.",
        "fr": "Cette ligne ne peut pas être retirée — sélectionnez des entrées ou des blocs de panneau entiers.",
    },
    "Diesen ganzen Panel-Block aus dem Profil entfernen?": {
        "en": "Remove this whole panel block from the profile?",
        "es": "¿Quitar todo este bloque de panel del perfil?",
        "fr": "Retirer tout ce bloc de panneau du profil ?",
    },
    "Panel-Block entfernen": {
        "en": "Remove panel block",
        "es": "Quitar bloque del panel",
        "fr": "Retirer le bloc de panneau",
    },
    "Neuen Panel-Controller anlegen — nur für Saitek-Panels (hidraw) und nur nötig, wenn das "
    "Profil das Panel noch gar nicht kennt. Details danach über die Baum-Zeilen einstellen.": {
        "en": "Create a new panel controller — only for Saitek panels (hidraw) and only needed when "
        "the profile doesn't know the panel yet. Set the details afterwards via the tree rows.",
        "es": "Crear un nuevo controlador de panel: solo para paneles Saitek (hidraw) y solo si el "
        "perfil aún no conoce el panel. Ajuste los detalles después mediante las filas del árbol.",
        "fr": "Créer un nouveau contrôleur de panneau — uniquement pour les panneaux Saitek (hidraw) "
        "et seulement si le profil ne connaît pas encore le panneau. Réglez ensuite les détails "
        "via les lignes de l'arbre.",
    },
    # ----- panel window --------------------------------------------------- #
    "  ziehen = bewegen · Kacheln einrasten/tauschen · Rechtsklick = weg": {
        "en": "  drag = move · tiles snap/swap · right-click = remove",
        "es": "  arrastrar = mover · los mosaicos encajan/intercambian · clic derecho = quitar",
        "fr": "  glisser = déplacer · les tuiles s'alignent/s'échangent · clic droit = retirer",
    },
    # ----- Profile tab ---------------------------------------------------- #
    "Aktives Profil:": {"en": "Active profile:", "es": "Perfil activo:", "fr": "Profil actif :"},
    "Kein Profil": {"en": "No profile", "es": "Sin perfil", "fr": "Aucun profil"},
    "Auto-Auswahl": {"en": "Auto-select", "es": "Selección automática", "fr": "Sélection auto"},
    "Flugzeug-Titel (Komma-getrennt) — wählt dieses Profil automatisch, wenn der Titel passt.": {
        "en": "Aircraft titles (comma-separated) — auto-selects this profile when the title matches.",
        "es": "Títulos de aeronave (separados por comas): selecciona este perfil automáticamente si el título coincide.",
        "fr": "Titres d'avion (séparés par des virgules) — sélectionne ce profil automatiquement si le titre correspond.",
    },
    "Beschreibung speichern": {
        "en": "Save description",
        "es": "Guardar descripción",
        "fr": "Enregistrer la description",
    },
    "Aktuelles Profil nicht gefunden.": {
        "en": "Current profile not found.",
        "es": "Perfil actual no encontrado.",
        "fr": "Profil actuel introuvable.",
    },
    "Das letzte Profil kann nicht entfernt werden.": {
        "en": "The last profile can't be removed.",
        "es": "No se puede quitar el último perfil.",
        "fr": "Le dernier profil ne peut pas être retiré.",
    },
    "Nicht möglich": {"en": "Not possible", "es": "No es posible", "fr": "Impossible"},
    "Ungültiger Name": {"en": "Invalid name", "es": "Nombre no válido", "fr": "Nom invalide"},
    "Nur Buchstaben, Ziffern, '_' und '-'.": {
        "en": "Only letters, digits, '_' and '-'.",
        "es": "Solo letras, dígitos, '_' y '-'.",
        "fr": "Uniquement lettres, chiffres, '_' et '-'.",
    },
    "(leer = Standard)": {
        "en": "(empty = default)",
        "es": "(vacío = predeterminado)",
        "fr": "(vide = défaut)",
    },
    "Gespeichert ✓": {"en": "Saved ✓", "es": "Guardado ✓", "fr": "Enregistré ✓"},
    "Profil oder Geräte-Katalog nicht lesbar": {
        "en": "Profile or device catalog not readable",
        "es": "Perfil o catálogo de dispositivos ilegible",
        "fr": "Profil ou catalogue de périphériques illisible",
    },
    # ----- Gauges tab ----------------------------------------------------- #
    "Klick wählt · Doppelklick mappt": {
        "en": "Click selects · double-click maps",
        "es": "Clic selecciona · doble clic asigna",
        "fr": "Clic sélectionne · double-clic mappe",
    },
    "Aus Bibliothek löschen": {
        "en": "Delete from library",
        "es": "Eliminar de la biblioteca",
        "fr": "Supprimer de la bibliothèque",
    },
    "Erst ein Gauge anklicken.": {
        "en": "Click a gauge first.",
        "es": "Primero haga clic en un instrumento.",
        "fr": "Cliquez d'abord sur un instrument.",
    },
    "Gauge vom Panel entfernt (Bibliothek unberührt).": {
        "en": "Gauge removed from the panel (library untouched).",
        "es": "Instrumento quitado del panel (biblioteca intacta).",
        "fr": "Instrument retiré du panneau (bibliothèque intacte).",
    },
    "Aus der Bibliothek gelöscht (Panel unberührt).": {
        "en": "Deleted from the library (panel untouched).",
        "es": "Eliminado de la biblioteca (panel intacto).",
        "fr": "Supprimé de la bibliothèque (panneau intact).",
    },
    "Erst rechts eine Zeile markieren.": {
        "en": "Select a row on the right first.",
        "es": "Primero seleccione una fila a la derecha.",
        "fr": "Sélectionnez d'abord une ligne à droite.",
    },
    "Instrument hinzufügen: erst aus Bibliothek (bereits gemappte Gauges) oder Vorlage wählen, "
    "dann die Zeiger auf Variablen mappen — danach liegt es auf dem Panel.": {
        "en": "Add an instrument: first pick from the library (already-mapped gauges) or a template, "
        "then map its needles to variables — after that it sits on the panel.",
        "es": "Añadir un instrumento: elija primero de la biblioteca (instrumentos ya asignados) o una "
        "plantilla, luego asigne sus agujas a variables; después queda en el panel.",
        "fr": "Ajouter un instrument : choisissez d'abord dans la bibliothèque (instruments déjà "
        "mappés) ou un modèle, puis mappez ses aiguilles sur des variables — il se place ensuite sur le panneau.",
    },
    "Noch keine Gauges.\n„+ Gauge“ → Vorlage/Bibliothek wählen → Zeiger auf Variablen mappen → aufs Panel.": {
        "en": "No gauges yet.\n“+ Gauge” → pick a template/library → map needles to variables → onto the panel.",
        "es": "Aún no hay instrumentos.\n«+ Instrumento» → elija plantilla/biblioteca → asigne agujas a variables → al panel.",
        "fr": "Pas encore d'instruments.\n« + Instrument » → choisir un modèle/bibliothèque → mapper les aiguilles → sur le panneau.",
    },
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
        "en": "green from position",
        "es": "verde desde posición",
        "fr": "vert à partir de la position",
    },
    "Power-Gate": {
        "en": "Power gate",
        "es": "Puerta de alimentación",
        "fr": "Porte d'alimentation",
    },
    "Schritt": {"en": "Step", "es": "Paso", "fr": "Pas"},
    "schnell": {"en": "fast", "es": "rápido", "fr": "rapide"},
    "SimVar-Write": {"en": "SimVar write", "es": "escritura de SimVar", "fr": "écriture SimVar"},
    "Selektor": {"en": "Selector", "es": "Selector", "fr": "Sélecteur"},
    "Zeile": {"en": "row", "es": "fila", "fr": "ligne"},
    "Alt-Quelle": {"en": "Alt source", "es": "Fuente alt.", "fr": "Source alt."},
    "AP-Master-LED": {"en": "AP master LED", "es": "LED maestro AP", "fr": "LED maître PA"},
    "Mode-Var": {"en": "Mode var", "es": "Variable de modo", "fr": "Variable de mode"},
    "Quellen-Umschalter": {
        "en": "Source toggle",
        "es": "Conmutador de fuente",
        "fr": "Bascule de source",
    },
    "Dimmer": {"en": "Dimmer", "es": "Regulador", "fr": "Variateur"},
    "nur Anzeige": {"en": "display only", "es": "solo lectura", "fr": "affichage seul"},
    "Quellen": {"en": "Sources", "es": "Fuentes", "fr": "Sources"},
    # ----- gui_mapper.py: editor field labels + help (OUTPUT_FIELD_HELP) --- #
    "Hardware-Code": {"en": "Hardware code", "es": "Código de hardware", "fr": "Code matériel"},
    "Bit/Code des Schalters bzw. der Selektor-Position am Panel (gemessen, s. docs/memory/*-hid.md). Nur ändern, wenn die Hardware neu vermessen wurde.": {
        "en": "Bit/code of the switch or selector position on the panel (measured, see docs/memory/*-hid.md). Only change when the hardware was re-measured.",
        "es": "Bit/código del interruptor o de la posición del selector en el panel (medido, ver docs/memory/*-hid.md). Cámbielo solo si se volvió a medir el hardware.",
        "fr": "Bit/code de l'interrupteur ou de la position du sélecteur sur le panneau (mesuré, voir docs/memory/*-hid.md). À ne changer que si le matériel a été remesuré.",
    },
    "Bezeichnung": {"en": "Designation", "es": "Denominación", "fr": "Désignation"},
    "Menschenlesbarer Name, nur für Anzeige/Logs.": {
        "en": "Human-readable name, for display/logs only.",
        "es": "Nombre legible, solo para visualización/registros.",
        "fr": "Nom lisible, pour l'affichage/les journaux uniquement.",
    },
    "Einheit für Lesen/Schreiben der Variable (meist number).": {
        "en": "Unit for reading/writing the variable (usually number).",
        "es": "Unidad para leer/escribir la variable (normalmente number).",
        "fr": "Unité pour lire/écrire la variable (généralement number).",
    },
    "Die Sim-Variable, deren Wert angezeigt/editiert wird.": {
        "en": "The sim variable whose value is shown/edited.",
        "es": "La variable del sim cuyo valor se muestra/edita.",
        "fr": "La variable du sim dont la valeur est affichée/éditée.",
    },
    "Setz-Event": {"en": "Set event", "es": "Evento de ajuste", "fr": "Event de réglage"},
    "K:-Event zum Setzen des Werts; leer = Variable wird direkt geschrieben.": {
        "en": "K: event to set the value; empty = the variable is written directly.",
        "es": "Evento K: para fijar el valor; vacío = la variable se escribe directamente.",
        "fr": "Event K: pour définir la valeur ; vide = la variable est écrite directement.",
    },
    "Wertänderung pro Encoder-Rastung.": {
        "en": "Value change per encoder detent.",
        "es": "Cambio de valor por muesca del codificador.",
        "fr": "Changement de valeur par cran de l'encodeur.",
    },
    "Schnell-Schritt": {"en": "Fast step", "es": "Paso rápido", "fr": "Pas rapide"},
    "Größerer Schritt, wenn der Drehknopf schnell gedreht wird. Leer = keine Beschleunigung.": {
        "en": "Larger step when the dial is turned fast. Empty = no acceleration.",
        "es": "Paso mayor cuando la rueda se gira rápido. Vacío = sin aceleración.",
        "fr": "Pas plus grand lorsque la molette tourne vite. Vide = pas d'accélération.",
    },
    "Minimum": {"en": "Minimum", "es": "Mínimo", "fr": "Minimum"},
    "Kleinster einstellbarer Wert.": {
        "en": "Smallest settable value.",
        "es": "Valor mínimo ajustable.",
        "fr": "Plus petite valeur réglable.",
    },
    "Maximum": {"en": "Maximum", "es": "Máximo", "fr": "Maximum"},
    "Größter einstellbarer Wert.": {
        "en": "Largest settable value.",
        "es": "Valor máximo ajustable.",
        "fr": "Plus grande valeur réglable.",
    },
    "Umlauf": {"en": "Wrap-around", "es": "Vuelta al inicio", "fr": "Bouclage"},
    "Am Ende zum Anfang weiterdrehen (z. B. Heading 359→0) statt anzuschlagen.": {
        "en": "Wrap from the end back to the start (e.g. heading 359→0) instead of stopping.",
        "es": "Al final vuelve al principio (p. ej. rumbo 359→0) en vez de detenerse.",
        "fr": "Reboucle de la fin au début (p. ex. cap 359→0) au lieu de buter.",
    },
    "Encoder-eigen": {
        "en": "Encoder-owned",
        "es": "Propio del codificador",
        "fr": "Propre à l'encodeur",
    },
    "Anzeige behält den zuletzt gedrehten Wert, statt der Live-Variable zu folgen (gegen Gauges, die den Wert überschreiben).": {
        "en": "The display keeps the last dialed value instead of following the live variable (against gauges that overwrite it).",
        "es": "La indicación mantiene el último valor girado en vez de seguir la variable en vivo (contra instrumentos que la sobrescriben).",
        "fr": "L'affichage garde la dernière valeur tournée au lieu de suivre la variable en direct (contre les instruments qui l'écrasent).",
    },
    "Aus-Schwelle": {"en": "Off threshold", "es": "Umbral de apagado", "fr": "Seuil d'extinction"},
    "Live-Werte ab dieser Schwelle (oder fehlende) werden als 0 angezeigt — fängt „Aus“-Parkwerte wie 80000 ab.": {
        "en": "Live values at or above this threshold (or missing) show as 0 — catches 'off' park values like 80000.",
        "es": "Los valores en vivo iguales o mayores a este umbral (o ausentes) se muestran como 0 — atrapa valores de reposo 'apagado' como 80000.",
        "fr": "Les valeurs en direct au-dessus de ce seuil (ou absentes) s'affichent comme 0 — capture les valeurs de repos « éteint » comme 80000.",
    },
    "Display-Zeile": {"en": "Display row", "es": "Fila del display", "fr": "Ligne d'affichage"},
    "Obere oder untere Zeile des Panel-Displays.": {
        "en": "Upper or lower row of the panel display.",
        "es": "Fila superior o inferior del display del panel.",
        "fr": "Ligne supérieure ou inférieure de l'affichage du panneau.",
    },
    "AP-Master-Var": {
        "en": "AP master var",
        "es": "Variable maestra AP",
        "fr": "Variable maître PA",
    },
    "Bool-Variable für die Autopilot-Master-LED.": {
        "en": "Bool variable for the autopilot master LED.",
        "es": "Variable booleana para el LED maestro del piloto automático.",
        "fr": "Variable booléenne pour la LED maître du pilote automatique.",
    },
    "Modus-Var": {"en": "Mode var", "es": "Variable de modo", "fr": "Variable de mode"},
    "Variable mit dem aktiven AP-Modus (steuert die Modus-LEDs).": {
        "en": "Variable with the active AP mode (drives the mode LEDs).",
        "es": "Variable con el modo AP activo (controla los LED de modo).",
        "fr": "Variable du mode PA actif (pilote les LED de mode).",
    },
    "Bool-Variable: bei 0 bleiben Display/LEDs dunkel (z. B. Batterie aus). Leer = immer an.": {
        "en": "Bool variable: at 0 the display/LEDs stay dark (e.g. battery off). Empty = always on.",
        "es": "Variable booleana: en 0 el display/LED quedan apagados (p. ej. batería apagada). Vacío = siempre encendido.",
        "fr": "Variable booléenne : à 0 l'affichage/les LED restent éteints (p. ex. batterie coupée). Vide = toujours allumé.",
    },
    "Geräte-ID aus config/devices.yaml (z. B. yoke).": {
        "en": "Device ID from config/devices.yaml (e.g. yoke).",
        "es": "ID de dispositivo de config/devices.yaml (p. ej. yoke).",
        "fr": "ID de périphérique depuis config/devices.yaml (p. ex. yoke).",
    },
    "Code rechtsdrehen": {
        "en": "Code turn right",
        "es": "Código giro derecha",
        "fr": "Code rotation droite",
    },
    "Eingabe-Code für eine Rastung im Uhrzeigersinn (heller).": {
        "en": "Input code for one clockwise detent (brighter).",
        "es": "Código de entrada para una muesca en sentido horario (más brillante).",
        "fr": "Code d'entrée pour un cran horaire (plus clair).",
    },
    "Code linksdrehen": {
        "en": "Code turn left",
        "es": "Código giro izquierda",
        "fr": "Code rotation gauche",
    },
    "Eingabe-Code für eine Rastung gegen den Uhrzeigersinn (dunkler).": {
        "en": "Input code for one counter-clockwise detent (dimmer).",
        "es": "Código de entrada para una muesca antihoraria (más tenue).",
        "fr": "Code d'entrée pour un cran antihoraire (plus sombre).",
    },
    "Sim-/L-Variable, die auf den skalierten Wert gesetzt wird.": {
        "en": "Sim/L variable that is set to the scaled value.",
        "es": "Variable Sim/L que se fija al valor escalado.",
        "fr": "Variable Sim/L définie à la valeur mise à l'échelle.",
    },
    "K:-Event, das mit dem skalierten Wert gefeuert wird.": {
        "en": "K: event fired with the scaled value.",
        "es": "Evento K: disparado con el valor escalado.",
        "fr": "Event K: déclenché avec la valeur mise à l'échelle.",
    },
    "Vollwert": {"en": "Full value", "es": "Valor pleno", "fr": "Valeur pleine"},
    "Wert der Lampe bei 100 % Helligkeit (Skala des Ziels).": {
        "en": "Value of the lamp at 100% brightness (target's scale).",
        "es": "Valor de la lámpara al 100% de brillo (escala del objetivo).",
        "fr": "Valeur de la lampe à 100 % de luminosité (échelle de la cible).",
    },
    "Folge-Event": {"en": "Follow event", "es": "Evento de seguimiento", "fr": "Event de suivi"},
    "An/Aus-Licht, das mitschaltet, sobald der Dimmer über dem Minimum steht.": {
        "en": "On/off light that switches along as soon as the dimmer is above the minimum.",
        "es": "Luz de encendido/apagado que conmuta en cuanto el regulador supera el mínimo.",
        "fr": "Lumière on/off qui commute dès que le variateur dépasse le minimum.",
    },
    "Bugrad-Var": {
        "en": "Nose-gear var",
        "es": "Variable tren de morro",
        "fr": "Variable train avant",
    },
    "Positions-Variable des Bugfahrwerks (0=oben … 1=unten).": {
        "en": "Position variable of the nose gear (0=up … 1=down).",
        "es": "Variable de posición del tren de morro (0=arriba … 1=abajo).",
        "fr": "Variable de position du train avant (0=rentré … 1=sorti).",
    },
    "Links-Var": {"en": "Left var", "es": "Variable izquierda", "fr": "Variable gauche"},
    "Positions-Variable des linken Hauptfahrwerks.": {
        "en": "Position variable of the left main gear.",
        "es": "Variable de posición del tren principal izquierdo.",
        "fr": "Variable de position du train principal gauche.",
    },
    "Rechts-Var": {"en": "Right var", "es": "Variable derecha", "fr": "Variable droite"},
    "Positions-Variable des rechten Hauptfahrwerks.": {
        "en": "Position variable of the right main gear.",
        "es": "Variable de posición del tren principal derecho.",
        "fr": "Variable de position du train principal droit.",
    },
    "Grün ab": {"en": "Green from", "es": "Verde desde", "fr": "Vert à partir de"},
    "Ab dieser Position gilt das Rad als ausgefahren (grüne LED).": {
        "en": "From this position the wheel counts as extended (green LED).",
        "es": "Desde esta posición la rueda cuenta como extendida (LED verde).",
        "fr": "À partir de cette position la roue compte comme sortie (LED verte).",
    },
    "Bezeichnung, nur für Anzeige/Logs.": {
        "en": "Designation, for display/logs only.",
        "es": "Denominación, solo para visualización/registros.",
        "fr": "Désignation, pour l'affichage/les journaux uniquement.",
    },
    "Display-Hälfte": {"en": "Display half", "es": "Mitad del display", "fr": "Moitié d'affichage"},
    "Obere oder untere Hälfte des Radio-Panel-Displays.": {
        "en": "Upper or lower half of the radio panel display.",
        "es": "Mitad superior o inferior del display del panel de radio.",
        "fr": "Moitié supérieure ou inférieure de l'affichage du panneau radio.",
    },
    "Äußerer Knopf rechts": {
        "en": "Outer knob right",
        "es": "Botón exterior derecha",
        "fr": "Bouton extérieur droite",
    },
    "Eingabe-Code: äußerer (grober) Drehknopf im UZS.": {
        "en": "Input code: outer (coarse) dial clockwise.",
        "es": "Código de entrada: rueda exterior (gruesa) en sentido horario.",
        "fr": "Code d'entrée : molette extérieure (grossière) sens horaire.",
    },
    "Äußerer Knopf links": {
        "en": "Outer knob left",
        "es": "Botón exterior izquierda",
        "fr": "Bouton extérieur gauche",
    },
    "Eingabe-Code: äußerer Drehknopf gegen den UZS.": {
        "en": "Input code: outer dial counter-clockwise.",
        "es": "Código de entrada: rueda exterior en sentido antihorario.",
        "fr": "Code d'entrée : molette extérieure sens antihoraire.",
    },
    "Innerer Knopf rechts": {
        "en": "Inner knob right",
        "es": "Botón interior derecha",
        "fr": "Bouton intérieur droite",
    },
    "Eingabe-Code: innerer (feiner) Drehknopf im UZS.": {
        "en": "Input code: inner (fine) dial clockwise.",
        "es": "Código de entrada: rueda interior (fina) en sentido horario.",
        "fr": "Code d'entrée : molette intérieure (fine) sens horaire.",
    },
    "Innerer Knopf links": {
        "en": "Inner knob left",
        "es": "Botón interior izquierda",
        "fr": "Bouton intérieur gauche",
    },
    "Eingabe-Code: innerer Drehknopf gegen den UZS.": {
        "en": "Input code: inner dial counter-clockwise.",
        "es": "Código de entrada: rueda interior en sentido antihorario.",
        "fr": "Code d'entrée : molette intérieure sens antihoraire.",
    },
    "Tausch-Knopf": {"en": "Swap button", "es": "Botón de intercambio", "fr": "Bouton d'échange"},
    "Eingabe-Code des Drückens (ACT↔STBY-Tausch).": {
        "en": "Input code of the press (ACT↔STBY swap).",
        "es": "Código de entrada de la pulsación (intercambio ACT↔STBY).",
        "fr": "Code d'entrée de l'appui (échange ACT↔STBY).",
    },
    "Aktiv-Frequenz": {
        "en": "Active frequency",
        "es": "Frecuencia activa",
        "fr": "Fréquence active",
    },
    "Variable der ACTIVE-Frequenz (obere Display-Zeile).": {
        "en": "Variable of the ACTIVE frequency (upper display row).",
        "es": "Variable de la frecuencia ACTIVA (fila superior del display).",
        "fr": "Variable de la fréquence ACTIVE (ligne d'affichage supérieure).",
    },
    "Standby-Frequenz": {
        "en": "Standby frequency",
        "es": "Frecuencia standby",
        "fr": "Fréquence standby",
    },
    "Variable der STANDBY-Frequenz (wird getunt, untere Zeile).": {
        "en": "Variable of the STANDBY frequency (being tuned, lower row).",
        "es": "Variable de la frecuencia STANDBY (que se sintoniza, fila inferior).",
        "fr": "Variable de la fréquence STANDBY (en cours de réglage, ligne inférieure).",
    },
    "Tausch-Event": {"en": "Swap event", "es": "Evento de intercambio", "fr": "Event d'échange"},
    "Event, das ACTIVE und STANDBY tauscht.": {
        "en": "Event that swaps ACTIVE and STANDBY.",
        "es": "Evento que intercambia ACTIVA y STANDBY.",
        "fr": "Event qui échange ACTIVE et STANDBY.",
    },
    "MHz hoch": {"en": "MHz up", "es": "MHz arriba", "fr": "MHz haut"},
    "Event des äußeren Knopfs: ganze MHz aufwärts.": {
        "en": "Outer knob event: whole MHz upward.",
        "es": "Evento de la rueda exterior: MHz enteros hacia arriba.",
        "fr": "Event de la molette extérieure : MHz entiers vers le haut.",
    },
    "MHz runter": {"en": "MHz down", "es": "MHz abajo", "fr": "MHz bas"},
    "Event des äußeren Knopfs: ganze MHz abwärts.": {
        "en": "Outer knob event: whole MHz downward.",
        "es": "Evento de la rueda exterior: MHz enteros hacia abajo.",
        "fr": "Event de la molette extérieure : MHz entiers vers le bas.",
    },
    "kHz hoch": {"en": "kHz up", "es": "kHz arriba", "fr": "kHz haut"},
    "Event des inneren Knopfs: Fein-Schritt aufwärts.": {
        "en": "Inner knob event: fine step upward.",
        "es": "Evento de la rueda interior: paso fino hacia arriba.",
        "fr": "Event de la molette intérieure : pas fin vers le haut.",
    },
    "kHz runter": {"en": "kHz down", "es": "kHz abajo", "fr": "kHz bas"},
    "Event des inneren Knopfs: Fein-Schritt abwärts.": {
        "en": "Inner knob event: fine step downward.",
        "es": "Evento de la rueda interior: paso fino hacia abajo.",
        "fr": "Event de la molette intérieure : pas fin vers le bas.",
    },
    "kHz hoch (schnell)": {
        "en": "kHz up (fast)",
        "es": "kHz arriba (rápido)",
        "fr": "kHz haut (rapide)",
    },
    "Event bei schnellem Drehen (gröberer Schritt). Leer = wie kHz hoch.": {
        "en": "Event on fast turn (coarser step). Empty = same as kHz up.",
        "es": "Evento al girar rápido (paso más grueso). Vacío = igual que kHz arriba.",
        "fr": "Event lors d'une rotation rapide (pas plus grossier). Vide = comme kHz haut.",
    },
    "kHz runter (schnell)": {
        "en": "kHz down (fast)",
        "es": "kHz abajo (rápido)",
        "fr": "kHz bas (rapide)",
    },
    "Event bei schnellem Drehen abwärts. Leer = wie kHz runter.": {
        "en": "Event on fast turn downward. Empty = same as kHz down.",
        "es": "Evento al girar rápido hacia abajo. Vacío = igual que kHz abajo.",
        "fr": "Event lors d'une rotation rapide vers le bas. Vide = comme kHz bas.",
    },
    "Fein-Anzeige": {"en": "Fine view", "es": "Vista fina", "fr": "Vue fine"},
    "Innerer Knopf schaltet die Standby-Zeile auf 3 Nachkommastellen (nur COM 8.33 sinnvoll).": {
        "en": "Inner knob switches the standby row to 3 decimals (only useful for COM 8.33).",
        "es": "La rueda interior cambia la fila standby a 3 decimales (solo útil para COM 8.33).",
        "fr": "La molette intérieure passe la ligne standby à 3 décimales (utile seulement pour COM 8.33).",
    },
    "Distanz-Var": {
        "en": "Distance var",
        "es": "Variable de distancia",
        "fr": "Variable de distance",
    },
    "DME-Entfernungs-Variable (nautische Meilen).": {
        "en": "DME distance variable (nautical miles).",
        "es": "Variable de distancia DME (millas náuticas).",
        "fr": "Variable de distance DME (milles nautiques).",
    },
    "Geschw.-Var": {"en": "Speed var", "es": "Variable de velocidad", "fr": "Variable de vitesse"},
    "DME-Geschwindigkeits-Variable (Knoten).": {
        "en": "DME speed variable (knots).",
        "es": "Variable de velocidad DME (nudos).",
        "fr": "Variable de vitesse DME (nœuds).",
    },
    "Quellen-Var": {"en": "Source var", "es": "Variable de fuente", "fr": "Variable de source"},
    "LVar mit der DME-Quelle (0=NAV1, 1=NAV2) — bidirektional mit dem Cockpit-Schalter. Leer = nur lokal durchschalten.": {
        "en": "LVar with the DME source (0=NAV1, 1=NAV2) — bidirectional with the cockpit switch. Empty = switch locally only.",
        "es": "LVar con la fuente DME (0=NAV1, 1=NAV2) — bidireccional con el interruptor de cabina. Vacío = conmutar solo localmente.",
        "fr": "LVar avec la source DME (0=NAV1, 1=NAV2) — bidirectionnel avec l'interrupteur du cockpit. Vide = commuter localement seulement.",
    },
    "Squawk-Var": {"en": "Squawk var", "es": "Variable de squawk", "fr": "Variable de squawk"},
    "Variable des Transponder-Codes (BCD16).": {
        "en": "Variable of the transponder code (BCD16).",
        "es": "Variable del código del transpondedor (BCD16).",
        "fr": "Variable du code transpondeur (BCD16).",
    },
    "Hunderter-Var": {
        "en": "Hundreds var",
        "es": "Variable de centenas",
        "fr": "Variable des centaines",
    },
    "KR-85-Zähler der Hunderter-Gruppe (0-16).": {
        "en": "KR-85 counter of the hundreds group (0-16).",
        "es": "Contador KR-85 del grupo de centenas (0-16).",
        "fr": "Compteur KR-85 du groupe des centaines (0-16).",
    },
    "Zehner-Var": {"en": "Tens var", "es": "Variable de decenas", "fr": "Variable des dizaines"},
    "KR-85-Zähler der Zehnerstelle (0-9).": {
        "en": "KR-85 counter of the tens digit (0-9).",
        "es": "Contador KR-85 de la cifra de decenas (0-9).",
        "fr": "Compteur KR-85 du chiffre des dizaines (0-9).",
    },
    "Einer-Var": {"en": "Ones var", "es": "Variable de unidades", "fr": "Variable des unités"},
    "KR-85-Zähler der Einerstelle (0-9).": {
        "en": "KR-85 counter of the ones digit (0-9).",
        "es": "Contador KR-85 de la cifra de unidades (0-9).",
        "fr": "Compteur KR-85 du chiffre des unités (0-9).",
    },
    "kHz-Minimum": {"en": "kHz minimum", "es": "Mínimo kHz", "fr": "Minimum kHz"},
    "Kleinste einstellbare ADF-Frequenz.": {
        "en": "Smallest settable ADF frequency.",
        "es": "Frecuencia ADF mínima ajustable.",
        "fr": "Plus petite fréquence ADF réglable.",
    },
    "kHz-Maximum": {"en": "kHz maximum", "es": "Máximo kHz", "fr": "Maximum kHz"},
    "Größte einstellbare ADF-Frequenz.": {
        "en": "Largest settable ADF frequency.",
        "es": "Frecuencia ADF máxima ajustable.",
        "fr": "Plus grande fréquence ADF réglable.",
    },
    "QNH-Var": {"en": "QNH var", "es": "Variable QNH", "fr": "Variable QNH"},
    "Variable des Luftdrucks für die untere Zeile (inHg). Leer = Zeile bleibt dunkel.": {
        "en": "Variable of the air pressure for the lower row (inHg). Empty = row stays dark.",
        "es": "Variable de la presión atmosférica para la fila inferior (inHg). Vacío = la fila queda apagada.",
        "fr": "Variable de la pression pour la ligne inférieure (inHg). Vide = la ligne reste éteinte.",
    },
    "QNH-Faktor": {"en": "QNH factor", "es": "Factor QNH", "fr": "Facteur QNH"},
    "Multiplikator der QNH-Var nach inHg (schon inHg = 1).": {
        "en": "Multiplier of the QNH var to inHg (already inHg = 1).",
        "es": "Multiplicador de la variable QNH a inHg (ya en inHg = 1).",
        "fr": "Multiplicateur de la variable QNH vers inHg (déjà en inHg = 1).",
    },
    "QNH hoch": {"en": "QNH up", "es": "QNH arriba", "fr": "QNH haut"},
    "Event des äußeren Knopfs: Luftdruck aufwärts.": {
        "en": "Outer knob event: air pressure upward.",
        "es": "Evento de la rueda exterior: presión hacia arriba.",
        "fr": "Event de la molette extérieure : pression vers le haut.",
    },
    "QNH runter": {"en": "QNH down", "es": "QNH abajo", "fr": "QNH bas"},
    "Event des äußeren Knopfs: Luftdruck abwärts.": {
        "en": "Outer knob event: air pressure downward.",
        "es": "Evento de la rueda exterior: presión hacia abajo.",
        "fr": "Event de la molette extérieure : pression vers le bas.",
    },
    "Selektor-Positionen": {
        "en": "Selector positions",
        "es": "Posiciones del selector",
        "fr": "Positions du sélecteur",
    },
    "Alternativ-Quellen": {
        "en": "Alternative sources",
        "es": "Fuentes alternativas",
        "fr": "Sources alternatives",
    },
    "LEDs (Var-gesteuert)": {
        "en": "LEDs (variable-driven)",
        "es": "LED (controlados por variable)",
        "fr": "LED (pilotées par variable)",
    },
    "Dimmer-Ziele": {
        "en": "Dimmer targets",
        "es": "Objetivos del regulador",
        "fr": "Cibles du variateur",
    },
    "Radio-Einheiten": {"en": "Radio units", "es": "Unidades de radio", "fr": "Unités radio"},
    "Bänke (Selektor)": {
        "en": "Banks (selector)",
        "es": "Bancos (selector)",
        "fr": "Bancs (sélecteur)",
    },
    "DME-Quellen": {"en": "DME sources", "es": "Fuentes DME", "fr": "Sources DME"},
    "Position": {"en": "Position", "es": "Posición", "fr": "Position"},
    "Bank": {"en": "Bank", "es": "Banco", "fr": "Banc"},
    "Ziel": {"en": "Target", "es": "Objetivo", "fr": "Cible"},
    "LED Bugrad": {"en": "LED nose gear", "es": "LED tren de morro", "fr": "LED train avant"},
    "LED links": {"en": "LED left", "es": "LED izquierda", "fr": "LED gauche"},
    "LED rechts": {"en": "LED right", "es": "LED derecha", "fr": "LED droite"},
    "Anzeige (LED)": {"en": "Display (LED)", "es": "Indicación (LED)", "fr": "Affichage (LED)"},
    "Eingabe→Anzeige": {
        "en": "Input→display",
        "es": "Entrada→indicación",
        "fr": "Entrée→affichage",
    },
    "Anzeige-Quelle": {
        "en": "Display source",
        "es": "Fuente de indicación",
        "fr": "Source d'affichage",
    },
    "Eingabe (Drehrad)": {"en": "Input (dial)", "es": "Entrada (rueda)", "fr": "Entrée (molette)"},
    "Anzeige (Licht)": {
        "en": "Display (light)",
        "es": "Indicación (luz)",
        "fr": "Affichage (lumière)",
    },
    "Eingabe": {"en": "Input", "es": "Entrada", "fr": "Entrée"},
    "Anzeige": {"en": "Display", "es": "Indicación", "fr": "Affichage"},
    # ----- gui_mapper.py: editor validation messages --------------------- #
    "{label} muss eine ganze Zahl sein.": {
        "en": "{label} must be a whole number.",
        "es": "{label} debe ser un número entero.",
        "fr": "{label} doit être un entier.",
    },
    "{label} muss eine Zahl sein.": {
        "en": "{label} must be a number.",
        "es": "{label} debe ser un número.",
        "fr": "{label} doit être un nombre.",
    },
    "Sequence-Schritt: Name fehlt.": {
        "en": "Sequence step: name is missing.",
        "es": "Paso de secuencia: falta el nombre.",
        "fr": "Étape de séquence : nom manquant.",
    },
    "Sequence braucht mindestens einen on-Schritt.": {
        "en": "A sequence needs at least one on-step.",
        "es": "Una secuencia necesita al menos un paso 'on'.",
        "fr": "Une séquence nécessite au moins une étape « on ».",
    },
    "Hat: mindestens eine Richtung (▲▼◀▶) belegen.": {
        "en": "Hat: assign at least one direction (▲▼◀▶).",
        "es": "Hat: asigne al menos una dirección (▲▼◀▶).",
        "fr": "Hat : attribuez au moins une direction (▲▼◀▶).",
    },
    "Event-Name fehlt.": {
        "en": "Event name is missing.",
        "es": "Falta el nombre del evento.",
        "fr": "Nom de l'event manquant.",
    },
    "SimVar-Name fehlt.": {
        "en": "SimVar name is missing.",
        "es": "Falta el nombre del SimVar.",
        "fr": "Nom du SimVar manquant.",
    },
    "event_from_var braucht 'read' und 'event'.": {
        "en": "event_from_var needs 'read' and 'event'.",
        "es": "event_from_var necesita 'read' y 'event'.",
        "fr": "event_from_var nécessite « read » et « event ».",
    },
    "RPN-Ausdruck fehlt.": {
        "en": "RPN expression is missing.",
        "es": "Falta la expresión RPN.",
        "fr": "Expression RPN manquante.",
    },
    "Sequence kann inline (noch) nicht angelegt werden.": {
        "en": "A sequence can't (yet) be created inline.",
        "es": "Una secuencia no se puede crear en línea (todavía).",
        "fr": "Une séquence ne peut pas (encore) être créée en ligne.",
    },
    "Unbekannter Aktions-Typ: {atype}": {
        "en": "Unknown action type: {atype}",
        "es": "Tipo de acción desconocido: {atype}",
        "fr": "Type d'action inconnu : {atype}",
    },
    "Name darf nicht leer sein.": {
        "en": "Name must not be empty.",
        "es": "El nombre no puede estar vacío.",
        "fr": "Le nom ne doit pas être vide.",
    },
    "Unbekannte Quell-Art: {kind}": {
        "en": "Unknown source kind: {kind}",
        "es": "Tipo de fuente desconocido: {kind}",
        "fr": "Type de source inconnu : {kind}",
    },
    "Split: Aktions-Typ '{atype}' geht unterhalb des Detents nicht.": {
        "en": "Split: action type '{atype}' isn't allowed below the detent.",
        "es": "División: el tipo de acción '{atype}' no es posible por debajo del retén.",
        "fr": "Division : le type d'action « {atype} » n'est pas possible sous le cran.",
    },
    "{name}: Wert fehlt.": {
        "en": "{name}: value is missing.",
        "es": "{name}: falta el valor.",
        "fr": "{name} : valeur manquante.",
    },
    "{name}: muss eins von {choices} sein.": {
        "en": "{name}: must be one of {choices}.",
        "es": "{name}: debe ser uno de {choices}.",
        "fr": "{name} : doit être l'un de {choices}.",
    },
    "{name}: ja/nein erwartet.": {
        "en": "{name}: yes/no expected.",
        "es": "{name}: se esperaba sí/no.",
        "fr": "{name} : oui/non attendu.",
    },
    "Bedingung: Variable fehlt (über Wählen… setzen).": {
        "en": "Condition: variable is missing (set it via Choose…).",
        "es": "Condición: falta la variable (defínala con Elegir…).",
        "fr": "Condition : variable manquante (définissez-la via Choisir…).",
    },
    "Bedingung: unbekannter Vergleich '{op}'.": {
        "en": "Condition: unknown comparison '{op}'.",
        "es": "Condición: comparación desconocida '{op}'.",
        "fr": "Condition : comparaison inconnue « {op} ».",
    },
    # ----- Nachbau: banner headings (group titles) ------------------------ #
    "Magnetos": {"en": "Magnetos", "es": "Magnetos", "fr": "Magnétos"},
    "Fahrwerk": {"en": "Landing gear", "es": "Tren de aterrizaje", "fr": "Train"},
    "Weitere Anzeigen": {
        "en": "More displays",
        "es": "Más indicadores",
        "fr": "Autres affichages",
    },
    # ----- arrange mode: toolbar, decorations, size dialog, menus --------- #
    "Raster ignorieren": {
        "en": "Ignore grid",
        "es": "Ignorar cuadrícula",
        "fr": "Ignorer la grille",
    },
    "Frei platzieren, ohne am Raster einzurasten (wird gemerkt).": {
        "en": "Place freely, without snapping to the grid (remembered).",
        "es": "Colocar libremente, sin ajustar a la cuadrícula (se recuerda).",
        "fr": "Placer librement, sans aligner sur la grille (mémorisé).",
    },
    "+ Deko": {"en": "+ Deco", "es": "+ Deco", "fr": "+ Déco"},
    "Box (Hintergrund)": {
        "en": "Box (background)",
        "es": "Caja (fondo)",
        "fr": "Boîte (arrière-plan)",
    },
    "Linie": {"en": "Line", "es": "Línea", "fr": "Ligne"},
    "Beschriftung": {"en": "Label", "es": "Etiqueta", "fr": "Libellé"},
    "Optische Hilfen zum Gruppieren: Box hinter Knöpfe, Trennlinie, Textlabel.": {
        "en": "Visual grouping helpers: a box behind buttons, a divider line, a text label.",
        "es": "Ayudas visuales para agrupar: una caja tras los botones, una línea, una etiqueta.",
        "fr": "Aides visuelles pour grouper : une boîte derrière les boutons, une ligne, un libellé.",
    },
    "Text": {"en": "Text", "es": "Texto", "fr": "Texte"},
    "Beschriftung:": {"en": "Label:", "es": "Etiqueta:", "fr": "Libellé :"},
    "Größe & Position": {
        "en": "Size & position",
        "es": "Tamaño y posición",
        "fr": "Taille et position",
    },
    "Größe & Position…": {
        "en": "Size & position…",
        "es": "Tamaño y posición…",
        "fr": "Taille et position…",
    },
    "Breite (px)": {"en": "Width (px)", "es": "Ancho (px)", "fr": "Largeur (px)"},
    "Höhe (px)": {"en": "Height (px)", "es": "Alto (px)", "fr": "Hauteur (px)"},
    "X-Position (px)": {
        "en": "X position (px)",
        "es": "Posición X (px)",
        "fr": "Position X (px)",
    },
    "Y-Position (px)": {
        "en": "Y position (px)",
        "es": "Posición Y (px)",
        "fr": "Position Y (px)",
    },
    "Raster ignorieren (exakte Pixel)": {
        "en": "Ignore grid (exact pixels)",
        "es": "Ignorar cuadrícula (píxeles exactos)",
        "fr": "Ignorer la grille (pixels exacts)",
    },
    "Ohne Häkchen rasten Größe und Position am nächsten Rasterpunkt ein.": {
        "en": "Unchecked, size and position snap to the nearest grid point.",
        "es": "Sin marcar, el tamaño y la posición se ajustan al punto de cuadrícula más cercano.",
        "fr": "Sans la case cochée, taille et position s'alignent sur le point de grille le plus proche.",
    },
    "Ganze Zahlen (Breite/Höhe ≥ 8, Position ≥ 0).": {
        "en": "Whole numbers (width/height ≥ 8, position ≥ 0).",
        "es": "Números enteros (ancho/alto ≥ 8, posición ≥ 0).",
        "fr": "Nombres entiers (largeur/hauteur ≥ 8, position ≥ 0).",
    },
    "Umbenennen…": {"en": "Rename…", "es": "Renombrar…", "fr": "Renommer…"},
    "Überschrift umbenennen": {
        "en": "Rename heading",
        "es": "Renombrar título",
        "fr": "Renommer le titre",
    },
    "Neuer Text:": {"en": "New text:", "es": "Nuevo texto:", "fr": "Nouveau texte :"},
    "Text bearbeiten…": {
        "en": "Edit text…",
        "es": "Editar texto…",
        "fr": "Modifier le texte…",
    },
    "Löschen": {"en": "Delete", "es": "Eliminar", "fr": "Supprimer"},
    "Ausgeblendete einblenden ({n})": {
        "en": "Show hidden ({n})",
        "es": "Mostrar ocultos ({n})",
        "fr": "Afficher les masqués ({n})",
    },
    "Für dieses Gerät gibt es noch keinen Nachbau.": {
        "en": "There is no replica for this device yet.",
        "es": "Todavía no hay una réplica para este dispositivo.",
        "fr": "Il n'y a pas encore de réplique pour cet appareil.",
    },
    "Anordnung zurücksetzen": {
        "en": "Reset layout",
        "es": "Restablecer disposición",
        "fr": "Réinitialiser la disposition",
    },
    "Die eigene Anordnung dieses Geräts verwerfen und zum Standard-Nachbau zurück?": {
        "en": "Discard this device's custom layout and go back to the default replica?",
        "es": "¿Descartar la disposición propia de este dispositivo y volver a la réplica estándar?",
        "fr": "Abandonner la disposition personnalisée de cet appareil et revenir à la réplique par défaut ?",
    },
    "Anordnung dieses Geräts zurücksetzen.": {
        "en": "Reset this device's layout.",
        "es": "Restablecer la disposición de este dispositivo.",
        "fr": "Réinitialiser la disposition de cet appareil.",
    },
    "Anordnen: ziehen = verschieben · Ecke ziehen = Größe · Rechtsklick "
    "= Größe/Text/Entfernen · „+ Deko“ für Box/Linie/Label · „✓ Fertig“": {
        "en": "Arrange: drag = move · drag corner = resize · right-click = "
        "size/text/remove · “+ Deco” for box/line/label · “✓ Done”",
        "es": "Organizar: arrastrar = mover · esquina = tamaño · clic derecho = "
        "tamaño/texto/quitar · «+ Deco» para caja/línea/etiqueta · «✓ Listo»",
        "fr": "Disposer : glisser = déplacer · coin = redimensionner · clic droit = "
        "taille/texte/retirer · « + Déco » pour boîte/ligne/libellé · « ✓ Terminé »",
    },
    # ----- device explorer (buttons, titles, transport hint) -------------- #
    "🔍 Geräte-Explorer…": {
        "en": "🔍 Device explorer…",
        "es": "🔍 Explorador de dispositivos…",
        "fr": "🔍 Explorateur d'appareils…",
    },
    "Geräte-Explorer": {
        "en": "Device explorer",
        "es": "Explorador de dispositivos",
        "fr": "Explorateur d'appareils",
    },
    "Registrieren…": {"en": "Register…", "es": "Registrar…", "fr": "Enregistrer…"},
    "Gerät registrieren": {
        "en": "Register device",
        "es": "Registrar dispositivo",
        "fr": "Enregistrer l'appareil",
    },
    "Geräteelemente…": {
        "en": "Device elements…",
        "es": "Elementos del dispositivo…",
        "fr": "Éléments de l'appareil…",
    },
    "Deregistrieren…": {
        "en": "Deregister…",
        "es": "Anular registro…",
        "fr": "Désenregistrer…",
    },
    "Ausgeblendete Geräte…": {
        "en": "Hidden devices…",
        "es": "Dispositivos ocultos…",
        "fr": "Appareils masqués…",
    },
    "Aktualisieren": {"en": "Refresh", "es": "Actualizar", "fr": "Actualiser"},
    "Transport": {"en": "Transport", "es": "Transporte", "fr": "Transport"},
    "Transport: „evdev“ = Achsen/Knöpfe über den Kernel-Input-Layer "
    "(Yokes, Pedale, Quadranten); „hidraw“ = roher HID-Zugriff, nur damit "
    "lassen sich LEDs/Anzeigen ansteuern (Saitek-Panels). Manche Geräte "
    "erscheinen doppelt — nimm hidraw, wenn du Ausgänge (LEDs/Displays) "
    "brauchst, sonst evdev.": {
        "en": "Transport: “evdev” = axes/buttons via the kernel input layer "
        "(yokes, pedals, quadrants); “hidraw” = raw HID access, the only way to "
        "drive LEDs/displays (Saitek panels). Some devices show up twice — pick "
        "hidraw if you need outputs (LEDs/displays), otherwise evdev.",
        "es": "Transporte: «evdev» = ejes/botones por la capa de entrada del kernel "
        "(yugos, pedales, cuadrantes); «hidraw» = acceso HID en bruto, la única "
        "forma de controlar LED/indicadores (paneles Saitek). Algunos dispositivos "
        "aparecen dos veces: elige hidraw si necesitas salidas (LED/indicadores), "
        "si no evdev.",
        "fr": "Transport : « evdev » = axes/boutons via la couche d'entrée du noyau "
        "(yokes, palonniers, quadrants) ; « hidraw » = accès HID brut, le seul "
        "moyen de piloter LED/affichages (panneaux Saitek). Certains appareils "
        "apparaissent en double — choisissez hidraw s'il vous faut des sorties "
        "(LED/affichages), sinon evdev.",
    },
    # ----- full i18n sweep: remaining mapper / explorer / teach strings --- #
    "(keine gescannten Eingänge)": {"en": "(no scanned inputs)", "es": "(sin entradas escaneadas)", "fr": "(aucune entrée scannée)"},
    "+ Anzeige hinzufügen…": {"en": "+ Add display…", "es": "+ Añadir indicador…", "fr": "+ Ajouter un afficheur…"},
    "+ Ausgabe ▾": {"en": "+ Output ▾", "es": "+ Salida ▾", "fr": "+ Sortie ▾"},
    "+ Eingabe ▾": {"en": "+ Input ▾", "es": "+ Entrada ▾", "fr": "+ Entrée ▾"},
    "+ Event": {"en": "+ Event", "es": "+ Evento", "fr": "+ Événement"},
    "+ Input anlernen…": {"en": "+ Teach input…", "es": "+ Aprender entrada…", "fr": "+ Apprendre une entrée…"},
    "Achse anlernen": {"en": "Teach axis", "es": "Aprender eje", "fr": "Apprendre l'axe"},
    "Achse von Anschlag zu Anschlag bewegen.": {"en": "Move the axis from stop to stop.", "es": "Mueve el eje de tope a tope.", "fr": "Déplacez l'axe de butée à butée."},
    "Achsen-Anlernen geht nur für angesteckte evdev-Geräte (Yoke/Pedale/Quadrant).": {"en": "Teaching an axis only works for a connected evdev device (yoke/pedals/quadrant).", "es": "Aprender un eje solo funciona con un dispositivo evdev conectado (yugo/pedales/cuadrante).", "fr": "L'apprentissage d'un axe ne fonctionne qu'avec un appareil evdev connecté (yoke/palonnier/quadrant)."},
    "Adresse": {"en": "Address", "es": "Dirección", "fr": "Adresse"},
    "Aktiv": {"en": "Active", "es": "Activo", "fr": "Actif"},
    "Aktuelles Gerät als Vorlage speichern…": {"en": "Save current device as template…", "es": "Guardar el dispositivo actual como plantilla…", "fr": "Enregistrer l'appareil actuel comme modèle…"},
    "Alle angeschlossenen Geräte anzeigen (auch fremde, noch nicht registrierte) und neue Geräte anlegen · Geräte-Paket importieren: Rechtsklick auf ein Gerät": {"en": "Show all connected devices (including unknown, not-yet-registered ones) and create new devices · Import a device package: right-click a device", "es": "Muestra todos los dispositivos conectados (también los desconocidos, aún no registrados) y crea nuevos dispositivos · Importar un paquete de dispositivo: clic derecho en un dispositivo", "fr": "Afficher tous les appareils connectés (y compris inconnus, non encore enregistrés) et créer de nouveaux appareils · Importer un paquet d'appareil : clic droit sur un appareil"},
    "Alle angeschlossenen Geräte — auch noch nicht registrierte. Ein unregistriertes Gerät markieren und „Registrieren…“, damit es im Profil mappbar wird.": {"en": "All connected devices — including not-yet-registered ones. Select an unregistered device and “Register…” so it can be mapped in the profile.", "es": "Todos los dispositivos conectados, incluidos los aún no registrados. Selecciona un dispositivo no registrado y «Registrar…» para poder mapearlo en el perfil.", "fr": "Tous les appareils connectés — y compris ceux non encore enregistrés. Sélectionnez un appareil non enregistré et « Enregistrer… » pour pouvoir le mapper dans le profil."},
    "Alles aus": {"en": "Stop all", "es": "Detener todo", "fr": "Tout arrêter"},
    "Als Geräte-Paket exportieren…": {"en": "Export as device package…", "es": "Exportar como paquete de dispositivo…", "fr": "Exporter comme paquet d'appareil…"},
    "Als Vorlage speichern": {"en": "Save as template", "es": "Guardar como plantilla", "fr": "Enregistrer comme modèle"},
    "Anlernen": {"en": "Teach", "es": "Aprender", "fr": "Apprendre"},
    "Anzeigen": {"en": "Displays", "es": "Indicadores", "fr": "Afficheurs"},
    "Anzeigen (Schreiben)": {"en": "Displays (write)", "es": "Indicadores (escritura)", "fr": "Afficheurs (écriture)"},
    "Art": {"en": "Type", "es": "Tipo", "fr": "Type"},
    "Auf gewähltes Gerät anlegen": {"en": "Create on selected device", "es": "Crear en el dispositivo seleccionado", "fr": "Créer sur l'appareil sélectionné"},
    "Aus Vorlage füllen": {"en": "Fill from template", "es": "Rellenar desde plantilla", "fr": "Remplir depuis un modèle"},
    "Aus Vorlage füllen…": {"en": "Fill from template…", "es": "Rellenar desde plantilla…", "fr": "Remplir depuis un modèle…"},
    "Aus dem aktuellen Mapping übernehmen:": {"en": "Take from the current mapping:", "es": "Tomar del mapeo actual:", "fr": "Reprendre du mappage actuel :"},
    "Aus der Geräteliste entfernen…": {"en": "Remove from device list…", "es": "Quitar de la lista de dispositivos…", "fr": "Retirer de la liste des appareils…"},
    "Ausgabe hinzugefügt ✓": {"en": "Output added ✓", "es": "Salida añadida ✓", "fr": "Sortie ajoutée ✓"},
    "Ausgang-Scan": {"en": "Output scan", "es": "Escaneo de salidas", "fr": "Scan des sorties"},
    "Ausgang-Scan geht nur für angesteckte hidraw-Panels.": {"en": "Output scan only works for a connected hidraw panel.", "es": "El escaneo de salidas solo funciona con un panel hidraw conectado.", "fr": "Le scan des sorties ne fonctionne qu'avec un panneau hidraw connecté."},
    "Ausgeblendete Geräte": {"en": "Hidden devices", "es": "Dispositivos ocultos", "fr": "Appareils masqués"},
    "Außen-Ring": {"en": "Outer ring", "es": "Anillo exterior", "fr": "Anneau extérieur"},
    "Bearbeiten…": {"en": "Edit…", "es": "Editar…", "fr": "Modifier…"},
    "Bedingung 1": {"en": "Condition 1", "es": "Condición 1", "fr": "Condition 1"},
    "Bedingung 2 (optional)": {"en": "Condition 2 (optional)", "es": "Condición 2 (opcional)", "fr": "Condition 2 (facultatif)"},
    "Beim Ausschalten — leer = nichts": {"en": "On switch-off — empty = nothing", "es": "Al apagar — vacío = nada", "fr": "À l'extinction — vide = rien"},
    "Beim Einschalten": {"en": "On switch-on", "es": "Al encender", "fr": "À l'allumage"},
    "Bit (0-7)": {"en": "Bit (0-7)", "es": "Bit (0-7)", "fr": "Bit (0-7)"},
    "Bridge starten und, sobald Port 7842 offen ist (MSFS mit Flug), den Mapper. Erst MSFS + Flug laden.": {"en": "Start the bridge and, once port 7842 is open (MSFS with a flight), the mapper. Load MSFS + a flight first.", "es": "Inicia el bridge y, en cuanto el puerto 7842 esté abierto (MSFS con un vuelo), el mapeador. Carga primero MSFS + un vuelo.", "fr": "Démarre le bridge puis, dès que le port 7842 est ouvert (MSFS avec un vol), le mappeur. Chargez d'abord MSFS + un vol."},
    "Byte/Bit (bzw. Zelle) nicht bekannt? Fast nie nötig, von Hand einzutippen: „{btn}“ schickt Testimpulse ans Panel — leuchtet DEINE LED/Zelle, „Das ist es!“ klicken; die Felder füllen sich automatisch (Panel angesteckt, Mapper gestoppt).": {"en": "Byte/bit (or cell) unknown? Almost never needs typing by hand: “{btn}” sends test pulses to the panel — when YOUR LED/cell lights up, click “That's it!”; the fields fill in automatically (panel plugged in, mapper stopped).", "es": "¿No conoces el byte/bit (o la celda)? Casi nunca hace falta escribirlo a mano: «{btn}» envía impulsos de prueba al panel — cuando se encienda TU LED/celda, pulsa «¡Es este!»; los campos se rellenan solos (panel conectado, mapeador detenido).", "fr": "Byte/bit (ou cellule) inconnu ? Presque jamais besoin de le saisir à la main : « {btn} » envoie des impulsions de test au panneau — quand VOTRE LED/cellule s'allume, cliquez sur « C'est ça ! » ; les champs se remplissent automatiquement (panneau branché, mappeur arrêté)."},
    "Code": {"en": "Code", "es": "Código", "fr": "Code"},
    "Das ist es!": {"en": "That's it!", "es": "¡Es este!", "fr": "C'est ça !"},
    "Detail": {"en": "Detail", "es": "Detalle", "fr": "Détail"},
    "Die „Adresse“ der LED im Gerät. Das Gerät bekommt seine Befehle als eine Reihe nummerierter Felder (Bytes); das Byte sagt, in WELCHEM Feld diese LED sitzt. Musst du nicht wissen — „🔦 Byte/Bit suchen…“ füllt es aus.": {"en": "The LED's “address” in the device. The device receives its commands as a series of numbered fields (bytes); the byte says in WHICH field this LED sits. You don't need to know it — “🔦 Find byte/bit…” fills it in.", "es": "La «dirección» del LED en el dispositivo. El dispositivo recibe sus órdenes como una serie de campos numerados (bytes); el byte indica en QUÉ campo está este LED. No necesitas saberlo: «🔦 Buscar byte/bit…» lo rellena.", "fr": "L'« adresse » de la LED dans l'appareil. L'appareil reçoit ses commandes sous forme d'une série de champs numérotés (octets) ; l'octet indique dans QUEL champ se trouve cette LED. Pas besoin de le savoir — « 🔦 Trouver octet/bit… » le remplit."},
    "Die „Adresse“ der ersten Ziffer im Gerät (das nummerierte Feld, in dem die Anzeige beginnt). Musst du nicht wissen — „🔦 Zelle suchen…“ füllt es aus.": {"en": "The “address” of the first digit in the device (the numbered field where the display starts). You don't need to know it — “🔦 Find cell…” fills it in.", "es": "La «dirección» del primer dígito en el dispositivo (el campo numerado donde empieza el indicador). No necesitas saberlo: «🔦 Buscar celda…» lo rellena.", "fr": "L'« adresse » du premier chiffre dans l'appareil (le champ numéroté où commence l'afficheur). Pas besoin de le savoir — « 🔦 Trouver cellule… » le remplit."},
    "Diese Geräte hast du aus der Geräteliste entfernt. Auswählen und „Wieder anzeigen“, um sie zurückzuholen.": {"en": "These devices you removed from the device list. Select one and “Show again” to bring it back.", "es": "Estos dispositivos los has quitado de la lista. Selecciona uno y «Mostrar de nuevo» para recuperarlo.", "fr": "Ces appareils, vous les avez retirés de la liste. Sélectionnez-en un et « Réafficher » pour le récupérer."},
    "Dieses Gerät hat im aktuellen Profil keine Mappings.": {"en": "This device has no mappings in the current profile.", "es": "Este dispositivo no tiene mapeos en el perfil actual.", "fr": "Cet appareil n'a aucun mappage dans le profil actuel."},
    "Dieses Gerät hat keine Anzeige/Ausgabe zum Speichern.": {"en": "This device has no display/output to save.", "es": "Este dispositivo no tiene indicador/salida para guardar.", "fr": "Cet appareil n'a aucun afficheur/sortie à enregistrer."},
    "Dieses Gerät ist bereits registriert.": {"en": "This device is already registered.", "es": "Este dispositivo ya está registrado.", "fr": "Cet appareil est déjà enregistré."},
    "Dieses Gerät ist nicht registriert.": {"en": "This device is not registered.", "es": "Este dispositivo no está registrado.", "fr": "Cet appareil n'est pas enregistré."},
    "Display": {"en": "Display", "es": "Pantalla", "fr": "Afficheur"},
    "Display (7-Segment)": {"en": "Display (7-segment)", "es": "Pantalla (7 segmentos)", "fr": "Afficheur (7 segments)"},
    "Display (7-Segment)…": {"en": "Display (7-segment)…", "es": "Pantalla (7 segmentos)…", "fr": "Afficheur (7 segments)…"},
    "Display hinzufügen": {"en": "Add display", "es": "Añadir pantalla", "fr": "Ajouter un afficheur"},
    "Drücke den Knopf mehrmals.": {"en": "Press the button several times.", "es": "Pulsa el botón varias veces.", "fr": "Appuyez plusieurs fois sur le bouton."},
    "Eigene Vorlagen:": {"en": "Your templates:", "es": "Tus plantillas:", "fr": "Vos modèles :"},
    "Ein Element aufleuchten lassen, um es am echten Panel zu identifizieren. Geht nur, wenn der Mapper das Panel NICHT steuert (er würde den Test sofort überschreiben).": {"en": "Light up an element to identify it on the real panel. Only works when the mapper is NOT driving the panel (it would overwrite the test immediately).", "es": "Encender un elemento para identificarlo en el panel real. Solo funciona si el mapeador NO controla el panel (sobrescribiría la prueba al instante).", "fr": "Faire clignoter un élément pour l'identifier sur le vrai panneau. Ne fonctionne que si le mappeur ne pilote PAS le panneau (il écraserait le test aussitôt)."},
    "Ein Testimpuls wandert über die Report-Adressen. Sobald am Gerät die richtige LED/Ziffer aufleuchtet: „Das ist es!“. Nur wenn der Mapper NICHT läuft.": {"en": "A test pulse walks across the report addresses. As soon as the right LED/digit lights up on the device: “That's it!”. Only when the mapper is NOT running.", "es": "Un impulso de prueba recorre las direcciones del reporte. En cuanto se encienda el LED/dígito correcto en el dispositivo: «¡Es este!». Solo si el mapeador NO está en marcha.", "fr": "Une impulsion de test parcourt les adresses du rapport. Dès que la bonne LED/le bon chiffre s'allume sur l'appareil : « C'est ça ! ». Uniquement si le mappeur ne tourne PAS."},
    "Ein vorhandenes SPAD.neXt-Profil (.xml) einlesen: die Events/SimVars, die dieses Flugzeug nutzt, erscheinen beim Mappen ganz oben im Variablen-Picker (kuratierte Kurzliste statt 700+ Namen). Nur die Semantik — den physischen Knopf wählst du weiter selbst.": {"en": "Read an existing SPAD.neXt profile (.xml): the events/SimVars this aircraft uses appear at the top of the variable picker when mapping (a curated short list instead of 700+ names). Semantics only — you still pick the physical button yourself.", "es": "Lee un perfil SPAD.neXt existente (.xml): los eventos/SimVars que usa esta aeronave aparecen arriba en el selector de variables al mapear (una lista breve curada en vez de más de 700 nombres). Solo la semántica: el botón físico lo sigues eligiendo tú.", "fr": "Lire un profil SPAD.neXt existant (.xml) : les événements/SimVars utilisés par cet avion apparaissent en haut du sélecteur de variables lors du mappage (une courte liste triée plutôt que plus de 700 noms). La sémantique seulement — le bouton physique, c'est toujours vous qui le choisissez."},
    "Eine Anzeige des Geräts an eine Variable binden — LED (ein Bit) oder Display (7-Segment-Wert ← Var). Legt bei Bedarf den generischen Ausgabe-Block an (Schritt E).": {"en": "Bind a device display to a variable — LED (one bit) or display (7-segment value ← var). Creates the generic output block if needed (step E).", "es": "Vincula un indicador del dispositivo a una variable — LED (un bit) o pantalla (valor de 7 segmentos ← var). Crea el bloque de salida genérico si hace falta (paso E).", "fr": "Lier un afficheur de l'appareil à une variable — LED (un bit) ou afficheur (valeur 7 segments ← var). Crée le bloc de sortie générique si nécessaire (étape E)."},
    "Eine einzelne Eingabe an ein Event/eine Variable binden — Taster/Schalter/Achse/Hat. Ein Encoder (2 Richtungen) wird an generischen Geräten in einem Rutsch angelernt; die Saitek-Panels steuern ihre Encoder über die Vorlage (kein eigener Schritt).": {"en": "Bind a single input to an event/variable — button/switch/axis/hat. An encoder (2 directions) is taught in one go on generic devices; the Saitek panels drive their encoders via the template (no separate step).", "es": "Vincula una sola entrada a un evento/variable — botón/interruptor/eje/hat. Un encoder (2 direcciones) se aprende de una vez en dispositivos genéricos; los paneles Saitek controlan sus encoders mediante la plantilla (sin paso aparte).", "fr": "Lier une seule entrée à un événement/une variable — bouton/interrupteur/axe/hat. Un encodeur (2 directions) s'apprend d'un coup sur les appareils génériques ; les panneaux Saitek pilotent leurs encodeurs via le modèle (pas d'étape séparée)."},
    "Einen bereits gescannten, benannten Eingang des Geräts wählen (Geräte-Explorer, Eingänge scannen) — füllt Art und Code automatisch.": {"en": "Pick an already scanned, named input of the device (Device Explorer, scan inputs) — fills type and code automatically.", "es": "Elige una entrada ya escaneada y con nombre del dispositivo (Explorador de dispositivos, escanear entradas) — rellena tipo y código automáticamente.", "fr": "Choisir une entrée déjà scannée et nommée de l'appareil (Explorateur d'appareils, scanner les entrées) — remplit le type et le code automatiquement."},
    "Eingänge scannen": {"en": "Scan inputs", "es": "Escanear entradas", "fr": "Scanner les entrées"},
    "Elemente aus dem aktuellen Mapping übernehmen (Bindings + Panel-Controls/LEDs/Display)": {"en": "Take elements from the current mapping (bindings + panel controls/LEDs/display)", "es": "Tomar elementos del mapeo actual (bindings + controles del panel/LEDs/pantalla)", "fr": "Reprendre des éléments du mappage actuel (bindings + commandes du panneau/LED/afficheur)"},
    "Elemente frei anordnen: im Nachbau die Knöpfe/Anzeigen ins Raster ziehen, an der blauen Ecke in der Größe ziehen (Rechtsklick = Größe in Pixel). Pro Gerät gespeichert.": {"en": "Arrange elements freely: in the replica drag the buttons/displays onto the grid, drag the blue corner to resize (right-click = size in pixels). Saved per device.", "es": "Organiza los elementos libremente: en la réplica arrastra los botones/indicadores a la cuadrícula, arrastra la esquina azul para cambiar el tamaño (clic derecho = tamaño en píxeles). Se guarda por dispositivo.", "fr": "Disposez les éléments librement : dans la réplique, glissez les boutons/afficheurs sur la grille, glissez le coin bleu pour redimensionner (clic droit = taille en pixels). Enregistré par appareil."},
    "Encoder (2 Richtungen)…": {"en": "Encoder (2 directions)…", "es": "Encoder (2 direcciones)…", "fr": "Encodeur (2 directions)…"},
    "Encoder anlernen": {"en": "Teach encoder", "es": "Aprender encoder", "fr": "Apprendre l'encodeur"},
    "Encoder gegen den Uhrzeigersinn drehen.": {"en": "Turn the encoder counter-clockwise.", "es": "Gira el encoder en sentido antihorario.", "fr": "Tournez l'encodeur dans le sens antihoraire."},
    "Encoder im Uhrzeigersinn drehen.": {"en": "Turn the encoder clockwise.", "es": "Gira el encoder en sentido horario.", "fr": "Tournez l'encodeur dans le sens horaire."},
    "Encoder mehrmals GEGEN den Uhrzeigersinn drehen.": {"en": "Turn the encoder COUNTER-clockwise several times.", "es": "Gira el encoder varias veces en sentido ANTIHORARIO.", "fr": "Tournez l'encodeur plusieurs fois dans le sens ANTIHORAIRE."},
    "Encoder mehrmals IM Uhrzeigersinn drehen.": {"en": "Turn the encoder CLOCKWISE several times.", "es": "Gira el encoder varias veces en sentido HORARIO.", "fr": "Tournez l'encodeur plusieurs fois dans le sens HORAIRE."},
    "Encoder-Anlernen abgebrochen (nicht beide Richtungen).": {"en": "Encoder teaching cancelled (not both directions).", "es": "Aprendizaje del encoder cancelado (no ambas direcciones).", "fr": "Apprentissage de l'encodeur annulé (pas les deux directions)."},
    "Encoder-Name": {"en": "Encoder name", "es": "Nombre del encoder", "fr": "Nom de l'encodeur"},
    "Erfasst": {"en": "Captured", "es": "Capturado", "fr": "Capturé"},
    "Erst registrieren, dann Elemente verwalten.": {"en": "Register first, then manage elements.", "es": "Regístralo primero y luego gestiona los elementos.", "fr": "Enregistrez d'abord, puis gérez les éléments."},
    "Erstes Byte (Offset)": {"en": "First byte (offset)", "es": "Primer byte (offset)", "fr": "Premier octet (offset)"},
    "Event: Name fehlt.": {"en": "Event: name is missing.", "es": "Evento: falta el nombre.", "fr": "Événement : nom manquant."},
    "Events (beim Drücken)": {"en": "Events (on press)", "es": "Eventos (al pulsar)", "fr": "Événements (à l'appui)"},
    "Falls die Drehrichtungen vertauscht sind — tauscht die beiden Codes beim Speichern.": {"en": "If the turn directions are swapped — swaps the two codes on save.", "es": "Si los sentidos de giro están intercambiados — intercambia los dos códigos al guardar.", "fr": "Si les sens de rotation sont inversés — échange les deux codes à l'enregistrement."},
    "Fertig": {"en": "Done", "es": "Listo", "fr": "Terminé"},
    "Fertig — Codes prüfen und übernehmen.": {"en": "Done — check the codes and apply.", "es": "Listo — comprueba los códigos y aplica.", "fr": "Terminé — vérifiez les codes et appliquez."},
    "Flanken": {"en": "Edges", "es": "Flancos", "fr": "Fronts"},
    "Ganzes Panel (Knöpfe + Anzeigen):": {"en": "Whole panel (buttons + displays):", "es": "Panel completo (botones + indicadores):", "fr": "Panneau entier (boutons + afficheurs) :"},
    "Ganzes Panel in einem Rutsch anlegen — eine Vorlage aus Knöpfen + Anzeigen. Die Saitek-Panels sind eingebaut (hidraw); eigene Anordnungen als Vorlage speicherbar.": {"en": "Create a whole panel in one go — a template of buttons + displays. The Saitek panels are built in (hidraw); your own arrangements can be saved as a template.", "es": "Crea un panel completo de una vez — una plantilla de botones + indicadores. Los paneles Saitek vienen incorporados (hidraw); tus propias disposiciones se pueden guardar como plantilla.", "fr": "Créer un panneau entier d'un coup — un modèle de boutons + afficheurs. Les panneaux Saitek sont intégrés (hidraw) ; vos propres dispositions peuvent être enregistrées comme modèle."},
    "Gerät deregistrieren": {"en": "Deregister device", "es": "Anular registro del dispositivo", "fr": "Désenregistrer l'appareil"},
    "Gerät getrennt.": {"en": "Device disconnected.", "es": "Dispositivo desconectado.", "fr": "Appareil déconnecté."},
    "Gerät nicht lesbar.": {"en": "Device not readable.", "es": "Dispositivo no legible.", "fr": "Appareil illisible."},
    "Gerät „{dev}“ importieren?\n\n• Gerät wird registriert (in deinen eigenen Geräten)\n• Anordnung + Kalibrierung werden übernommen\n": {"en": "Import device “{dev}”?\n\n• The device is registered (in your own devices)\n• Arrangement + calibration are applied\n", "es": "¿Importar el dispositivo «{dev}»?\n\n• El dispositivo se registra (en tus propios dispositivos)\n• Se aplican la disposición + la calibración\n", "fr": "Importer l'appareil « {dev} » ?\n\n• L'appareil est enregistré (dans vos propres appareils)\n• La disposition + l'étalonnage sont appliqués\n"},
    "Geräte": {"en": "Devices", "es": "Dispositivos", "fr": "Appareils"},
    "Geräte-Katalog nicht lesbar": {"en": "Device catalog not readable", "es": "Catálogo de dispositivos no legible", "fr": "Catalogue d'appareils illisible"},
    "Geräte-Paket": {"en": "Device package", "es": "Paquete de dispositivo", "fr": "Paquet d'appareil"},
    "Geräte-Paket exportieren": {"en": "Export device package", "es": "Exportar paquete de dispositivo", "fr": "Exporter le paquet d'appareil"},
    "Geräte-Paket importieren": {"en": "Import device package", "es": "Importar paquete de dispositivo", "fr": "Importer un paquet d'appareil"},
    "Geräte-Paket importieren…": {"en": "Import device package…", "es": "Importar paquete de dispositivo…", "fr": "Importer un paquet d'appareil…"},
    "Geräteelemente": {"en": "Device elements", "es": "Elementos del dispositivo", "fr": "Éléments de l'appareil"},
    "Helligkeit": {"en": "Brightness", "es": "Brillo", "fr": "Luminosité"},
    "Holen": {"en": "Pull", "es": "Traer", "fr": "Récupérer"},
    "Innen-Ring": {"en": "Inner ring", "es": "Anillo interior", "fr": "Anneau intérieur"},
    "Inputs": {"en": "Inputs", "es": "Entradas", "fr": "Entrées"},
    "Inputs (Lesen)": {"en": "Inputs (read)", "es": "Entradas (lectura)", "fr": "Entrées (lecture)"},
    "Kein Profil ausgewählt.": {"en": "No profile selected.", "es": "Ningún perfil seleccionado.", "fr": "Aucun profil sélectionné."},
    "Kein Profil geladen.": {"en": "No profile loaded.", "es": "Ningún perfil cargado.", "fr": "Aucun profil chargé."},
    "Kein Zielprofil ausgewählt.": {"en": "No target profile selected.", "es": "Ningún perfil de destino seleccionado.", "fr": "Aucun profil cible sélectionné."},
    "Kein anderes Profil hat Mappings für „{dev}“.": {"en": "No other profile has mappings for “{dev}”.", "es": "Ningún otro perfil tiene mapeos para «{dev}».", "fr": "Aucun autre profil n'a de mappages pour « {dev} »."},
    "Kein anderes Profil vorhanden.": {"en": "No other profile available.", "es": "No hay otro perfil disponible.", "fr": "Aucun autre profil disponible."},
    "Keine ausgeblendeten Geräte.": {"en": "No hidden devices.", "es": "No hay dispositivos ocultos.", "fr": "Aucun appareil masqué."},
    "Klick auf ein Element öffnet den Editor · Rechtsklick: Bearbeiten / Duplizieren / Entfernen": {"en": "Click an element to open the editor · right-click: edit / duplicate / remove", "es": "Clic en un elemento abre el editor · clic derecho: editar / duplicar / quitar", "fr": "Cliquer sur un élément ouvre l'éditeur · clic droit : modifier / dupliquer / retirer"},
    "Klick: gemappt → Editor, leerer Platzhalter → neu mappen · Schalter/Achsen live": {"en": "Click: mapped → editor, empty placeholder → map anew · switches/axes live", "es": "Clic: mapeado → editor, hueco vacío → mapear de nuevo · interruptores/ejes en vivo", "fr": "Clic : mappé → éditeur, emplacement vide → remapper · interrupteurs/axes en direct"},
    "Konnte nicht laden: ": {"en": "Could not load: ", "es": "No se pudo cargar: ", "fr": "Impossible de charger : "},
    "Kurz-ID für dieses Gerät (Profile referenzieren sie):": {"en": "Short ID for this device (profiles reference it):", "es": "ID corto para este dispositivo (los perfiles lo referencian):", "fr": "ID court pour cet appareil (les profils le référencent) :"},
    "LED an, wenn Variable <Operator> Wert (z. B. ≥ 0.5, < 30, == 2, != 0). Wert leer lassen = diese Bedingung weglassen.": {"en": "LED on when variable <operator> value (e.g. ≥ 0.5, < 30, == 2, != 0). Leave the value empty = drop this condition.", "es": "LED encendido cuando variable <operador> valor (p. ej. ≥ 0.5, < 30, == 2, != 0). Deja el valor vacío = omitir esta condición.", "fr": "LED allumée quand variable <opérateur> valeur (p. ex. ≥ 0.5, < 30, == 2, != 0). Laisser la valeur vide = ignorer cette condition."},
    "LED hinzufügen": {"en": "Add LED", "es": "Añadir LED", "fr": "Ajouter une LED"},
    "LED leuchtet, wenn ALLE gesetzten Bedingungen zutreffen. Eine reicht meist; zwei = Fenster, z. B. ≥ 0.01 UND < 0.95 für die rote Fahrwerks-LED beim Ausfahren.": {"en": "The LED is on when ALL set conditions hold. One is usually enough; two = a window, e.g. ≥ 0.01 AND < 0.95 for the red gear LED while extending.", "es": "El LED se enciende cuando se cumplen TODAS las condiciones definidas. Una suele bastar; dos = una ventana, p. ej. ≥ 0.01 Y < 0.95 para el LED rojo del tren al extenderse.", "fr": "La LED s'allume quand TOUTES les conditions définies sont vraies. Une suffit en général ; deux = une fenêtre, p. ex. ≥ 0.01 ET < 0.95 pour la LED rouge du train pendant la sortie."},
    "LED…": {"en": "LED…", "es": "LED…", "fr": "LED…"},
    "Lampe": {"en": "Lamp", "es": "Lámpara", "fr": "Voyant"},
    "Lese- (Inputs) und Schreib-Elemente (Anzeigen) getrennt verwalten: Inputs am Gerät betätigen und benennen, Anzeigen (LEDs/Displays) hinzufügen.": {"en": "Manage read (inputs) and write elements (displays) separately: actuate and name inputs on the device, add displays (LEDs/displays).", "es": "Gestiona por separado los elementos de lectura (entradas) y de escritura (indicadores): acciona y nombra las entradas en el dispositivo, añade indicadores (LEDs/pantallas).", "fr": "Gérez séparément les éléments de lecture (entrées) et d'écriture (afficheurs) : actionnez et nommez les entrées sur l'appareil, ajoutez des afficheurs (LED/afficheurs)."},
    "Live-Anlernen braucht das angesteckte hidraw-Panel.": {"en": "Live teaching needs the connected hidraw panel.", "es": "El aprendizaje en vivo necesita el panel hidraw conectado.", "fr": "L'apprentissage en direct nécessite le panneau hidraw connecté."},
    "Live-Anlernen geht nur für angesteckte evdev-Geräte (Yoke/Pedale/Quadrant).": {"en": "Live teaching only works for a connected evdev device (yoke/pedals/quadrant).", "es": "El aprendizaje en vivo solo funciona con un dispositivo evdev conectado (yugo/pedales/cuadrante).", "fr": "L'apprentissage en direct ne fonctionne qu'avec un appareil evdev connecté (yoke/palonnier/quadrant)."},
    "Live-Vorschau (Nadel bei ~65 %)": {"en": "Live preview (needle at ~65%)", "es": "Vista previa en vivo (aguja al ~65 %)", "fr": "Aperçu en direct (aiguille à ~65 %)"},
    "MSFS-Prefix automatisch finden (wie tools/find-prefix.sh)": {"en": "Find the MSFS prefix automatically (like tools/find-prefix.sh)", "es": "Encuentra el prefix de MSFS automáticamente (como tools/find-prefix.sh)", "fr": "Trouver le préfixe MSFS automatiquement (comme tools/find-prefix.sh)"},
    "Mapping entfernen": {"en": "Remove mapping", "es": "Quitar mapeo", "fr": "Retirer le mappage"},
    "Mappings aus einem anderen Profil holen…": {"en": "Pull mappings from another profile…", "es": "Traer mapeos de otro perfil…", "fr": "Récupérer les mappages d'un autre profil…"},
    "Mappings holen": {"en": "Pull mappings", "es": "Traer mapeos", "fr": "Récupérer les mappages"},
    "Mappings in anderes Profil übertragen…": {"en": "Transfer mappings to another profile…", "es": "Transferir mapeos a otro perfil…", "fr": "Transférer les mappages vers un autre profil…"},
    "Mappings übertragen": {"en": "Transfer mappings", "es": "Transferir mapeos", "fr": "Transférer les mappages"},
    "Mehrere Events": {"en": "Multiple events", "es": "Varios eventos", "fr": "Plusieurs événements"},
    "Mehrere Events je Betätigung (Event feuern / Variable setzen):": {"en": "Multiple events per actuation (fire event / set variable):", "es": "Varios eventos por accionamiento (disparar evento / fijar variable):", "fr": "Plusieurs événements par action (déclencher un événement / définir une variable) :"},
    "Mindestens ein Event beim Drücken/Einschalten nötig.": {"en": "At least one event on press/switch-on is required.", "es": "Se requiere al menos un evento al pulsar/encender.", "fr": "Au moins un événement à l'appui/à l'allumage est requis."},
    "Mindestens eine Bedingung mit einem Wert angeben.": {"en": "Specify at least one condition with a value.", "es": "Especifica al menos una condición con un valor.", "fr": "Indiquez au moins une condition avec une valeur."},
    "Modus-Wahl": {"en": "Mode selection", "es": "Selección de modo", "fr": "Sélection du mode"},
    "Nachkommastellen": {"en": "Decimals", "es": "Decimales", "fr": "Décimales"},
    "Name der Vorlage:": {"en": "Template name:", "es": "Nombre de la plantilla:", "fr": "Nom du modèle :"},
    "Neu mappen…": {"en": "Map anew…", "es": "Mapear de nuevo…", "fr": "Remapper…"},
    "Neues Binding": {"en": "New binding", "es": "Nuevo binding", "fr": "Nouveau binding"},
    "Nichts hinzuzufügen — alle Vorlage-Elemente sind schon da.": {"en": "Nothing to add — all template elements are already there.", "es": "Nada que añadir — todos los elementos de la plantilla ya están.", "fr": "Rien à ajouter — tous les éléments du modèle sont déjà là."},
    "Panel testen": {"en": "Test panel", "es": "Probar panel", "fr": "Tester le panneau"},
    "Positionen": {"en": "Positions", "es": "Posiciones", "fr": "Positions"},
    "Probiert die LEDs/Zellen am echten Panel durch, bis deine aufleuchtet — dann werden Byte/Bit bzw. Zelle automatisch eingetragen.": {"en": "Steps through the LEDs/cells on the real panel until yours lights up — then byte/bit or cell is filled in automatically.", "es": "Recorre los LEDs/celdas del panel real hasta que se encienda el tuyo — entonces se rellena byte/bit o celda automáticamente.", "fr": "Parcourt les LED/cellules du vrai panneau jusqu'à ce que la vôtre s'allume — puis octet/bit ou cellule est renseigné automatiquement."},
    "Registriert ✓ → ": {"en": "Registered ✓ → ", "es": "Registrado ✓ → ", "fr": "Enregistré ✓ → "},
    "Report-Byte": {"en": "Report byte", "es": "Byte del reporte", "fr": "Octet du rapport"},
    "Report-Bytes:": {"en": "Report bytes:", "es": "Bytes del reporte:", "fr": "Octets du rapport :"},
    "Richtung": {"en": "Direction", "es": "Dirección", "fr": "Direction"},
    "SPAD.neXt-Import": {"en": "SPAD.neXt import", "es": "Importación de SPAD.neXt", "fr": "Importation SPAD.neXt"},
    "SPAD.neXt-Profil (.xml) oder Katalog (.json) wählen": {"en": "Choose a SPAD.neXt profile (.xml) or catalog (.json)", "es": "Elige un perfil SPAD.neXt (.xml) o un catálogo (.json)", "fr": "Choisir un profil SPAD.neXt (.xml) ou un catalogue (.json)"},
    "SWAP-Taster": {"en": "SWAP button", "es": "Botón SWAP", "fr": "Bouton SWAP"},
    "Schalter mehrmals umlegen.": {"en": "Flip the switch several times.", "es": "Cambia el interruptor varias veces.", "fr": "Basculez l'interrupteur plusieurs fois."},
    "Segmente": {"en": "Segments", "es": "Segmentos", "fr": "Segments"},
    "Senden fehlgeschlagen:": {"en": "Send failed:", "es": "Fallo al enviar:", "fr": "Échec de l'envoi :"},
    "Standby": {"en": "Standby", "es": "Standby", "fr": "Standby"},
    "Taster": {"en": "Button", "es": "Botón", "fr": "Bouton"},
    "Totzone (roh)": {"en": "Deadzone (raw)", "es": "Zona muerta (bruto)", "fr": "Zone morte (brut)"},
    "Totzone muss innerhalb Eingang min…max liegen ({lo}…{hi}).": {"en": "Deadzone must be within input min…max ({lo}…{hi}).", "es": "La zona muerta debe estar dentro del min…max de entrada ({lo}…{hi}).", "fr": "La zone morte doit être dans le min…max d'entrée ({lo}…{hi})."},
    "Totzone: max muss größer als min sein.": {"en": "Deadzone: max must be greater than min.", "es": "Zona muerta: max debe ser mayor que min.", "fr": "Zone morte : max doit être supérieur à min."},
    "Totzone: min UND max angeben (oder beide leer).": {"en": "Deadzone: specify min AND max (or leave both empty).", "es": "Zona muerta: indica min Y max (o deja ambos vacíos).", "fr": "Zone morte : indiquez min ET max (ou laissez les deux vides)."},
    "Trimmrad": {"en": "Trim wheel", "es": "Rueda de compensación", "fr": "Molette de trim"},
    "Variable fehlt.": {"en": "Variable is missing.", "es": "Falta la variable.", "fr": "Variable manquante."},
    "Vorhandene Elemente bleiben erhalten.": {"en": "Existing elements are kept.", "es": "Los elementos existentes se conservan.", "fr": "Les éléments existants sont conservés."},
    "Vorlage ▾": {"en": "Template ▾", "es": "Plantilla ▾", "fr": "Modèle ▾"},
    "Weiter": {"en": "Next", "es": "Siguiente", "fr": "Suivant"},
    "Welche einzelne LED innerhalb des Bytes. Jedes Byte steuert bis zu 8 Lampen (Bit 0-7). Auch das findet „🔦 Byte/Bit suchen…“ automatisch.": {"en": "Which single LED within the byte. Each byte drives up to 8 lamps (bit 0-7). “🔦 Find byte/bit…” finds this automatically too.", "es": "Qué LED individual dentro del byte. Cada byte controla hasta 8 lámparas (bit 0-7). «🔦 Buscar byte/bit…» también lo encuentra automáticamente.", "fr": "Quelle LED individuelle dans l'octet. Chaque octet pilote jusqu'à 8 voyants (bit 0-7). « 🔦 Trouver octet/bit… » le trouve aussi automatiquement."},
    "Wert-Encoder": {"en": "Value encoder", "es": "Encoder de valor", "fr": "Encodeur de valeur"},
    "Wie heißt diese Anzeige?": {"en": "What's this display called?", "es": "¿Cómo se llama este indicador?", "fr": "Comment s'appelle cet afficheur ?"},
    "Wie heißt dieser Encoder? (z. B. „Heading“, „Höhe“)": {"en": "What's this encoder called? (e.g. “Heading”, “Altitude”)", "es": "¿Cómo se llama este encoder? (p. ej. «Rumbo», «Altitud»)", "fr": "Comment s'appelle cet encodeur ? (p. ex. « Cap », « Altitude »)"},
    "Wie heißt dieses Bedienelement?": {"en": "What's this control called?", "es": "¿Cómo se llama este control?", "fr": "Comment s'appelle cette commande ?"},
    "Wie viele Stellen/Segmente hat das Display?": {"en": "How many digits/segments does the display have?", "es": "¿Cuántos dígitos/segmentos tiene la pantalla?", "fr": "Combien de chiffres/segments a l'afficheur ?"},
    "Wie viele Ziffern die Anzeige hat (z. B. 5 für eine Frequenz wie 118.00).": {"en": "How many digits the display has (e.g. 5 for a frequency like 118.00).", "es": "Cuántos dígitos tiene el indicador (p. ej. 5 para una frecuencia como 118.00).", "fr": "Combien de chiffres a l'afficheur (p. ex. 5 pour une fréquence comme 118.00)."},
    "Wieder anzeigen": {"en": "Show again", "es": "Mostrar de nuevo", "fr": "Réafficher"},
    "Zahlenfeld ungültig.": {"en": "Number field invalid.", "es": "Campo numérico no válido.", "fr": "Champ numérique non valide."},
    "Zeiger": {"en": "Needle", "es": "Aguja", "fr": "Aiguille"},
    "Zellen": {"en": "Cells", "es": "Celdas", "fr": "Cellules"},
    "Ziffern nach dem Komma (0 = ganze Zahl).": {"en": "Digits after the decimal point (0 = whole number).", "es": "Dígitos tras la coma (0 = número entero).", "fr": "Chiffres après la virgule (0 = nombre entier)."},
    "Zweite Bedingung, UND-verknüpft — für ein Fenster. Leer = nicht benutzt.": {"en": "Second condition, AND-combined — for a window. Empty = unused.", "es": "Segunda condición, combinada con Y — para una ventana. Vacío = sin usar.", "fr": "Deuxième condition, combinée par ET — pour une fenêtre. Vide = inutilisé."},
    "alles aus": {"en": "stop all", "es": "detener todo", "fr": "tout arrêter"},
    "anlernen": {"en": "teach", "es": "aprender", "fr": "apprendre"},
    "außen": {"en": "outer", "es": "exterior", "fr": "extérieur"},
    "bash bridge/run-bridge.sh   (Supervisor → bridge.py → Proton)": {"en": "bash bridge/run-bridge.sh   (supervisor → bridge.py → Proton)", "es": "bash bridge/run-bridge.sh   (supervisor → bridge.py → Proton)", "fr": "bash bridge/run-bridge.sh   (superviseur → bridge.py → Proton)"},
    "bash bridge/setup-prefix.sh  (Windows-Python + SimConnect)": {"en": "bash bridge/setup-prefix.sh  (Windows Python + SimConnect)", "es": "bash bridge/setup-prefix.sh  (Python de Windows + SimConnect)", "fr": "bash bridge/setup-prefix.sh  (Python Windows + SimConnect)"},
    "das Trimmrad mehrmals nach oben / im Uhrzeigersinn drehen": {"en": "turn the trim wheel up / clockwise several times", "es": "gira la rueda de compensación hacia arriba / en sentido horario varias veces", "fr": "tournez la molette de trim vers le haut / dans le sens horaire plusieurs fois"},
    "das Trimmrad mehrmals nach unten / gegen den Uhrzeigersinn drehen": {"en": "turn the trim wheel down / counter-clockwise several times", "es": "gira la rueda de compensación hacia abajo / en sentido antihorario varias veces", "fr": "tournez la molette de trim vers le bas / dans le sens antihoraire plusieurs fois"},
    "den INNEREN Ring mehrmals GEGEN den Uhrzeigersinn drehen": {"en": "turn the INNER ring COUNTER-clockwise several times", "es": "gira el anillo INTERIOR en sentido ANTIHORARIO varias veces", "fr": "tournez l'anneau INTÉRIEUR dans le sens ANTIHORAIRE plusieurs fois"},
    "den INNEREN Ring mehrmals IM Uhrzeigersinn drehen": {"en": "turn the INNER ring CLOCKWISE several times", "es": "gira el anillo INTERIOR en sentido HORARIO varias veces", "fr": "tournez l'anneau INTÉRIEUR dans le sens HORAIRE plusieurs fois"},
    "den Mode-Selektor mehrmals auf DIESE Position drehen": {"en": "turn the mode selector to THIS position several times", "es": "gira el selector de modo a ESTA posición varias veces", "fr": "tournez le sélecteur de mode sur CETTE position plusieurs fois"},
    "den SWAP-Taster mehrmals drücken": {"en": "press the SWAP button several times", "es": "pulsa el botón SWAP varias veces", "fr": "appuyez plusieurs fois sur le bouton SWAP"},
    "den ÄUSSEREN Ring mehrmals GEGEN den Uhrzeigersinn drehen": {"en": "turn the OUTER ring COUNTER-clockwise several times", "es": "gira el anillo EXTERIOR en sentido ANTIHORARIO varias veces", "fr": "tournez l'anneau EXTÉRIEUR dans le sens ANTIHORAIRE plusieurs fois"},
    "den ÄUSSEREN Ring mehrmals IM Uhrzeigersinn drehen": {"en": "turn the OUTER ring CLOCKWISE several times", "es": "gira el anillo EXTERIOR en sentido HORARIO varias veces", "fr": "tournez l'anneau EXTÉRIEUR dans le sens HORAIRE plusieurs fois"},
    "erkannt": {"en": "detected", "es": "detectado", "fr": "détecté"},
    "filedialog.askdirectory → prefix_path (gui-settings.json)": {"en": "filedialog.askdirectory → prefix_path (gui-settings.json)", "es": "filedialog.askdirectory → prefix_path (gui-settings.json)", "fr": "filedialog.askdirectory → prefix_path (gui-settings.json)"},
    "gegen": {"en": "CCW", "es": "antihorario", "fr": "antihoraire"},
    "hoch": {"en": "up", "es": "arriba", "fr": "haut"},
    "im UZS": {"en": "CW", "es": "horario", "fr": "horaire"},
    "innen": {"en": "inner", "es": "interior", "fr": "intérieur"},
    "invertieren": {"en": "invert", "es": "invertir", "fr": "inverser"},
    "ja": {"en": "yes", "es": "sí", "fr": "oui"},
    "killpg SIGTERM (Mapper-Prozessgruppe) + sweep 'peripherals_bridge run'": {"en": "killpg SIGTERM (mapper process group) + sweep 'peripherals_bridge run'", "es": "killpg SIGTERM (grupo de procesos del mapeador) + barrido 'peripherals_bridge run'", "fr": "killpg SIGTERM (groupe de processus du mappeur) + balayage 'peripherals_bridge run'"},
    "killpg SIGTERM + sweep 'bridge/bridge.py' / 'bridge/run-bridge.sh'": {"en": "killpg SIGTERM + sweep 'bridge/bridge.py' / 'bridge/run-bridge.sh'", "es": "killpg SIGTERM + barrido 'bridge/bridge.py' / 'bridge/run-bridge.sh'", "fr": "killpg SIGTERM + balayage 'bridge/bridge.py' / 'bridge/run-bridge.sh'"},
    "leer · Klick zum Mappen": {"en": "empty · click to map", "es": "vacío · clic para mapear", "fr": "vide · cliquer pour mapper"},
    "leuchtet ~2 s": {"en": "lights ~2 s", "es": "se enciende ~2 s", "fr": "s'allume ~2 s"},
    "mehrere Events je Betätigung — unten bearbeiten ↓": {"en": "multiple events per actuation — edit below ↓", "es": "varios eventos por accionamiento — editar abajo ↓", "fr": "plusieurs événements par action — modifier ci-dessous ↓"},
    "nein": {"en": "no", "es": "no", "fr": "non"},
    "nicht gefunden — angesteckt?": {"en": "not found — plugged in?", "es": "no encontrado — ¿conectado?", "fr": "introuvable — branché ?"},
    "nicht gemappt": {"en": "not mapped", "es": "sin mapear", "fr": "non mappé"},
    "nicht registriert": {"en": "not registered", "es": "no registrado", "fr": "non enregistré"},
    "pkexec tools/install-udev-rules.sh  (udev-Regeln, Passwortdialog)": {"en": "pkexec tools/install-udev-rules.sh  (udev rules, password dialog)", "es": "pkexec tools/install-udev-rules.sh  (reglas udev, diálogo de contraseña)", "fr": "pkexec tools/install-udev-rules.sh  (règles udev, dialogue de mot de passe)"},
    "prefix_path speichern + Bridge-Env (STEAM_COMPAT_DATA_PATH) setzen": {"en": "save prefix_path + set bridge env (STEAM_COMPAT_DATA_PATH)", "es": "guardar prefix_path + fijar el entorno del bridge (STEAM_COMPAT_DATA_PATH)", "fr": "enregistrer prefix_path + définir l'env du bridge (STEAM_COMPAT_DATA_PATH)"},
    "registriert als ": {"en": "registered as ", "es": "registrado como ", "fr": "enregistré comme "},
    "runter": {"en": "down", "es": "abajo", "fr": "bas"},
    "stop_mapper() + stop_bridge() — alle Strays wegräumen": {"en": "stop_mapper() + stop_bridge() — clear all strays", "es": "stop_mapper() + stop_bridge() — eliminar todos los restos", "fr": "stop_mapper() + stop_bridge() — nettoyer tous les résidus"},
    "weiterdrehen oder «Weiter»": {"en": "keep turning or «Next»", "es": "sigue girando o «Siguiente»", "fr": "continuez à tourner ou « Suivant »"},
    "{n} Variablen/Events aus {src} geladen (davon {ev} Events). Sie stehen jetzt ganz oben im Variablen-Picker beim Mappen.": {"en": "Loaded {n} variables/events from {src} (of which {ev} events). They now sit at the top of the variable picker when mapping.", "es": "Se cargaron {n} variables/eventos de {src} (de ellos {ev} eventos). Ahora aparecen arriba en el selector de variables al mapear.", "fr": "{n} variables/événements chargés depuis {src} (dont {ev} événements). Ils apparaissent maintenant en haut du sélecteur de variables lors du mappage."},
    "Überschreiben?": {"en": "Overwrite?", "es": "¿Sobrescribir?", "fr": "Écraser ?"},
    "Überspringen": {"en": "Skip", "es": "Omitir", "fr": "Ignorer"},
    "Übertragen": {"en": "Transfer", "es": "Transferir", "fr": "Transférer"},
    "— warte auf Bewegung —": {"en": "— waiting for movement —", "es": "— esperando movimiento —", "fr": "— en attente de mouvement —"},
    "„{dev}“ ({nb} Eingaben / {no} Anzeigen) übertragen nach:": {"en": "Transfer “{dev}” ({nb} inputs / {no} displays) to:", "es": "Transferir «{dev}» ({nb} entradas / {no} indicadores) a:", "fr": "Transférer « {dev} » ({nb} entrées / {no} afficheurs) vers :"},
    "„{dev}“ exportiert ✓\n\n{nb} Eingaben / {no} Anzeigen (aus Profil „{p}“) · Anordnung: {lay} · Kalibrierung: {cal}\n→ {path}": {"en": "“{dev}” exported ✓\n\n{nb} inputs / {no} displays (from profile “{p}”) · arrangement: {lay} · calibration: {cal}\n→ {path}", "es": "«{dev}» exportado ✓\n\n{nb} entradas / {no} indicadores (del perfil «{p}») · disposición: {lay} · calibración: {cal}\n→ {path}", "fr": "« {dev} » exporté ✓\n\n{nb} entrées / {no} afficheurs (du profil « {p} ») · disposition : {lay} · étalonnage : {cal}\n→ {path}"},
    "„{dev}“ importiert ✓\n\n{nb} Eingaben / {no} Anzeigen{into} · Anordnung: {lay} · Kalibrierung: {cal}": {"en": "“{dev}” imported ✓\n\n{nb} inputs / {no} displays{into} · arrangement: {lay} · calibration: {cal}", "es": "«{dev}» importado ✓\n\n{nb} entradas / {no} indicadores{into} · disposición: {lay} · calibración: {cal}", "fr": "« {dev} » importé ✓\n\n{nb} entrées / {no} afficheurs{into} · disposition : {lay} · étalonnage : {cal}"},
    "„{dev}“ — Mappings holen aus:": {"en": "“{dev}” — pull mappings from:", "es": "«{dev}» — traer mapeos de:", "fr": "« {dev} » — récupérer les mappages de :"},
    "„{dev}“ → „{t}“: {wb} Eingaben / {wo} Anzeigen übertragen ✓": {"en": "“{dev}” → “{t}”: {wb} inputs / {wo} displays transferred ✓", "es": "«{dev}» → «{t}»: {wb} entradas / {wo} indicadores transferidos ✓", "fr": "« {dev} » → « {t} » : {wb} entrées / {wo} afficheurs transférés ✓"},
    "„{dev}“: {wb} Eingaben / {wo} Anzeigen aus „{s}“ geholt ✓": {"en": "“{dev}”: {wb} inputs / {wo} displays pulled from “{s}” ✓", "es": "«{dev}»: {wb} entradas / {wo} indicadores traídos de «{s}» ✓", "fr": "« {dev} » : {wb} entrées / {wo} afficheurs récupérés de « {s} » ✓"},
    "„{name}“ aus der Geräteliste entfernen?\n\nDas blendet das Gerät nur für dich aus (der mitgelieferte Katalog und deine Profil-Mappings bleiben unangetastet). Über den Geräte-Explorer → „Ausgeblendete Geräte…“ kannst du es jederzeit wieder einblenden.": {"en": "Remove “{name}” from the device list?\n\nThis only hides the device for you (the bundled catalog and your profile mappings stay untouched). Via Device Explorer → “Hidden devices…” you can show it again any time.", "es": "¿Quitar «{name}» de la lista de dispositivos?\n\nEsto solo oculta el dispositivo para ti (el catálogo incluido y tus mapeos de perfil quedan intactos). Desde el Explorador de dispositivos → «Dispositivos ocultos…» puedes volver a mostrarlo cuando quieras.", "fr": "Retirer « {name} » de la liste des appareils ?\n\nCela masque l'appareil uniquement pour vous (le catalogue fourni et vos mappages de profil restent intacts). Via l'Explorateur d'appareils → « Appareils masqués… », vous pouvez le réafficher à tout moment."},
    "„{name}“ deregistriert ✓": {"en": "“{name}” deregistered ✓", "es": "«{name}» dado de baja ✓", "fr": "« {name} » désenregistré ✓"},
    "„{t}“ hat für dieses Gerät schon {eb} Eingaben / {eo} Anzeigen. Überschreiben?": {"en": "“{t}” already has {eb} inputs / {eo} displays for this device. Overwrite?", "es": "«{t}» ya tiene {eb} entradas / {eo} indicadores para este dispositivo. ¿Sobrescribir?", "fr": "« {t} » a déjà {eb} entrées / {eo} afficheurs pour cet appareil. Écraser ?"},
    "• (kein Mapping im Paket)": {"en": "• (no mapping in the package)", "es": "• (sin mapeo en el paquete)", "fr": "• (aucun mappage dans le paquet)"},
    "• Mapping landet in Profil „{p}“ (überschreibt vorhandenes)": {"en": "• Mapping goes into profile “{p}” (overwrites existing)", "es": "• El mapeo va al perfil «{p}» (sobrescribe el existente)", "fr": "• Le mappage va dans le profil « {p} » (écrase l'existant)"},
    "● live": {"en": "● live", "es": "● en vivo", "fr": "● en direct"},
    "⚠ Der Mapper läuft und steuert das Panel — bitte erst im Connection-Tab stoppen.": {"en": "⚠ The mapper is running and driving the panel — please stop it first in the Connection tab.", "es": "⚠ El mapeador está en marcha y controla el panel — deténlo primero en la pestaña Conexión.", "fr": "⚠ Le mappeur tourne et pilote le panneau — arrêtez-le d'abord dans l'onglet Connexion."},
    "⚠ Der Mapper läuft — erst im Connection-Tab stoppen.": {"en": "⚠ The mapper is running — stop it first in the Connection tab.", "es": "⚠ El mapeador está en marcha — deténlo primero en la pestaña Conexión.", "fr": "⚠ Le mappeur tourne — arrêtez-le d'abord dans l'onglet Connexion."},
    "✎ Anordnen": {"en": "✎ Arrange", "es": "✎ Organizar", "fr": "✎ Disposer"},
    "✓ Fertig": {"en": "✓ Done", "es": "✓ Listo", "fr": "✓ Terminé"},
    "🎚 Anlernen…": {"en": "🎚 Teach…", "es": "🎚 Aprender…", "fr": "🎚 Apprendre…"},
    "🎚 anlernen": {"en": "🎚 teach", "es": "🎚 aprender", "fr": "🎚 apprendre"},
    "📋 Benannt": {"en": "📋 Named", "es": "📋 Con nombre", "fr": "📋 Nommé"},
    "🔦 Byte/Bit suchen…": {"en": "🔦 Find byte/bit…", "es": "🔦 Buscar byte/bit…", "fr": "🔦 Trouver octet/bit…"},
    "🔦 LEDs/Display testen…": {"en": "🔦 Test LEDs/display…", "es": "🔦 Probar LEDs/pantalla…", "fr": "🔦 Tester LED/afficheur…"},
    "🔦 Zelle suchen…": {"en": "🔦 Find cell…", "es": "🔦 Buscar celda…", "fr": "🔦 Trouver cellule…"},
}
