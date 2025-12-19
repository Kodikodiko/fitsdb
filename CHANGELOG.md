# Changelog

## [Unreleased] - 19.12.2025

### ✨ Features

- **Erweitertes Statistik-Panel**: Der Statistikbereich wurde erheblich verbessert:
  - **Metrik-Übersicht**: Zeigt Top-Level-Statistiken wie die Gesamtzahl der Objekte, die Gesamtbelichtungszeit und die Gesamtzahl der Nächte an. Enthält außerdem Vergleichsmetriken des letzten vollen Monats mit dem Vorjahresmonat.
  - **Visualisierungen**: Ein 3-spaltiges Layout zeigt Balkendiagramme für "Anzahl FITS pro Monat", "Gesamtbelichtungszeit pro Monat (h)" und "FITS-Dateien pro Observatorium".
- **Interaktive Objektfilterung**: Benutzer können auf eine Zeile in der Ergebnistabelle klicken, um die gesamte App nach diesem spezifischen Objekt zu filtern. Eine Schaltfläche "Objektfilter löschen" ermöglicht das einfache Entfernen dieses Filters.
- **"Anzahl FITS pro Monat"-Chart**: Ein neues Diagramm zur Visualisierung der Anzahl der FITS-Dateien pro Monat wurde hinzugefügt.

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