# Changelog

## [Unreleased]

## [1.1.0] - 21.12.2025

### ✨ Features

- **Galaktische Koordinaten-Visualisierung**: Ein neues Streudiagramm wurde hinzugefügt, das die Verteilung der Himmelsobjekte in galaktischen Koordinaten darstellt.
  - **X-Achse**: Galaktische Länge (l) von 180° bis -180°, zentriert auf das galaktische Zentrum (0°).
  - **Y-Achse**: Galaktische Breite (b) von -90° bis +90°.
  - **Interaktivität**: Die Punkte können nach Observatorium gefiltert werden. Nicht ausgewählte Observatorien werden ausgeblendet, um die Analyse zu fokussieren.
  - **Datenbereinigung**: Objekte mit den Namen "Unknown" oder "flatwizard" werden in dieser Ansicht automatisch herausgefiltert.

### 🐛 Bugfixes

- **Robuste JSON-Header-Verarbeitung**: Ein kritischer Fehler wurde behoben, bei dem die Koordinatenextraktion aus FITS-Headern fehlschlug. Die App kann nun korrekt mit einfach oder doppelt "escaped" JSON-Strings im `header_dump`-Feld umgehen, was den Datenverlust bei der Verarbeitung drastisch reduziert.

### ⚙️ Verbesserungen & Refinements

- **Vereinfachte Benutzeroberfläche**: Die Visualisierungsansicht wurde aufgeräumt. Veraltete und irreführende Diagramme wurden entfernt, um den Fokus auf die wissenschaftlich korrekte galaktische Darstellung zu legen.
- **Achsen-Konfiguration**: Die Achsen der galaktischen Karte wurden präzise konfiguriert, um eine intuitive und standardkonforme Darstellung zu gewährleisten (invertierte X-Achse, voller Y-Achsen-Bereich).
- **Punktgröße angepasst**: Die Punktgröße im Diagramm wurde reduziert, um die Lesbarkeit bei großen Datenmengen zu verbessern.

## [Unreleased] - 19.12.2025

### ✨ Features

- **Erweitertes Statistik-Panel**: Der Statistikbereich wurde erheblich verbessert:
  - **Metrik-Übersicht**: Zeigt Top-Level-Statistiken wie die Gesamtzahl der Objekte, die Gesamtbelichtungszeit und die Gesamtzahl der Nächte an. Enthält außerdem Vergleichsmetriken des letzten vollen Monats mit dem Vorjahresmonat.
  - **Visualisierungen**: Ein 3-spaltiges Layout zeigt Balkendiagramme für "Anzahl FITS pro Monat", "Gesamtbelichtungszeit pro Monat (h)" und "FITS-Dateien pro Observatorium".
- **Interaktive Objektfilterung**: Benutzer können auf eine Zeile in der Ergebnistabelle klicken, um die gesamte App nach diesem spezifischen Objekt zu filtern. Eine Schaltfläche "Objektfilter löschen" ermöglicht das einfache Entfernen dieses Filters.
- **"Anzahl FITS pro Monat"-Chart**: Ein neues Diagramm zur Visualisierung der Anzahl der FITS-Dateien pro Monat wurde hinzugefügt.
- **Alternative Anwendungsversion (`app2.py`)**: Es wurde eine zweite, eigenständige Anwendungsdatei (`app2.py`) erstellt.
  - **`app.py`**: Bleibt die Hauptanwendung, die eine aktive Verbindung zu einer PostgreSQL-Datenbank erfordert. Ideal für die Live-Datennutzung und -Indizierung.
  - **`app2.py`**: Eine Version, die für die einfache Weitergabe und Veröffentlichung konzipiert ist. Sie liest Daten aus einer statischen `fits_data.parquet`-Datei und benötigt keine Datenbankverbindung.
  - **Datenexport-Skript (`export_data.py`)**: Ein Skript wurde hinzugefügt, um die Daten aus der Datenbank in die `fits_data.parquet`-Datei zu exportieren, die von `app2.py` verwendet wird.

### 🐛 Bugfixes

- **Berechnung der Diagrammdaten**: Mehrere Probleme bei der Aggregation von Diagrammdaten wurden behoben, wodurch eine korrekte chronologische Sortierung auf der X-Achse sichergestellt und Datenfehler bei der Visualisierung vermieden wurden.
- **Datenrundung**: Ein Fehler wurde behoben, bei dem die Werte der Belichtungszeit in den Tooltips der Diagramme nicht gerundet wurden. Alle Belichtungszeiten werden nun in der gesamten Anwendung konsistent auf eine Dezimalstelle gerundet.
- **Monats-Charts**: Die Monats-Diagramme zeigen nun auch Monate ohne Daten korrekt mit einem Wert von 0 an, anstatt diese auszulassen.

### ⚙️ Verbesserungen & Refinements

- **Standardfilter**: Die Anwendung startet nun ohne vorausgewählten Client, wodurch standardmäßig ein vollständiger Überblick über alle Daten gegeben wird.
- **UI-Layout**: Das Layout des Statistik-Panels wurde schrittweise zu einem kompakteren und lesbareren Design verfeinert, mit Diagrammen in Spalten und der Objektliste in einem separaten, einklappbaren Bereich.
- **Vereinfachung der Diagramme**: Die komplexen Jahresvergleichsdiagramme wurden letztendlich auf eine sauberere Darstellung mit einem Balken pro Monat vereinfacht, um den Fokus auf die jüngsten Aktivitäten zu legen.
- **Neuanordnung der Charts**: Die Statistik-Diagramme wurden neu angeordnet: 1. Anzahl FITS pro Monat, 2. Gesamtbelichtungszeit, 3. FITS pro Observatorium.
- **Konsistente Chart-Bibliothek**: Alle Statistik-Diagramme verwenden nun Altair, um eine einheitliche Darstellung und korrekte Ausrichtung der X-Achsen zu gewährleisten.
- **Horizontale Achsenbeschriftung**: Die X-Achsenbeschriftung des "FITS pro Observatorium"-Diagramms ist nun horizontal, um die Lesbarkeit zu verbessern.