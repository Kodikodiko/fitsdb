# Changelog

## [Unreleased] - 2025-12-19

### ✨ Features

- **Erweitertes Statistik-Panel**: Der Statistikbereich wurde erheblich verbessert, um tiefere Einblicke in den FITS-Dateikatalog zu ermöglichen.
  - Zeigt wichtige zusammenfassende Metriken an: Gesamtzahl der Objekte, Gesamtbelichtungszeit und Gesamtzahl der Beobachtungsnächte.
  - Enthält monatliche Vergleichsmetriken für Beobachtungsnächte und Belichtungszeit (letzter voller Monat im Vergleich zum Vorjahresmonat).
  - Visualisiert die Aktivität der letzten 6 Monate mit monatlichen Balkendiagrammen für "Beobachtungsnächte" und "Gesamtbelichtungszeit (h)".
  - Fügt ein Balkendiagramm hinzu, das die Gesamtzahl der FITS-Dateien pro Observatorium anzeigt.
- **Interaktive Objektfilterung**: Benutzer können nun auf eine beliebige Zeile in der Hauptergebnistabelle klicken, um die gesamte Anwendung, einschließlich aller Statistiken, sofort nach diesem bestimmten Himmelsobjekt zu filtern. Eine Schaltfläche "Objektfilter löschen" ermöglicht die einfache Rückkehr zur globalen Ansicht.

### 🐛 Bugfixes

- **Fehlerbehebung bei Diagrammachsen**: Die Logik zur Datenaggregation für Zeitreihendiagramme wurde korrigiert, um sicherzustellen, dass die Monatsbeschriftungen korrekt sind und keine zukünftigen Daten anzeigen.
- **Diagramm-Gruppierung**: Ein Fehler in der Diagrammimplementierung wurde behoben, um sicherzustellen, dass Jahresvergleichsdaten in nebeneinander liegenden (gruppierten) Balken anstatt gestapelt dargestellt werden.

### ⚙️ Verbesserungen & Refinements

- **Standardansicht**: Die Anwendung startet nun standardmäßig ohne Vorauswahl eines Clients und bietet so beim Laden einen vollständigen Überblick über den Katalog.
- **Datenformatierung**: Alle in der App angezeigten Belichtungszeiten (in Metriken, Tabellen und Diagrammen) werden zur besseren Lesbarkeit nun konsistent auf eine Dezimalstelle gerundet.
- **UI-Layout**: Das Layout des Statistik-Panels wurde mehrfach überarbeitet und in einem kompakten Raster mit drei Spalten für Diagramme und einem einklappbaren Bereich für die Objektliste neu angeordnet.
- **Vereinfachung der Diagramme**: Auf Basis von Feedback wurden die komplexen Jahresvergleichsdiagramme wieder auf einfache Balkendiagramme (ein Balken pro Monat) reduziert, um die Aktivität der letzten sechs Monate darzustellen.
- **Farbliche Anpassungen**: Die Farben der Vergleichsbalken wurden zur besseren Unterscheidung angepasst, einschließlich der Verwendung von Transparenz.
