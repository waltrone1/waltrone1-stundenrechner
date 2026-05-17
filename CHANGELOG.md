# Changelog

All notable changes to **waltrone1 Stundenrechner** will be documented in this file.

This project is part of the **WALTRONE Community Tools** collection.

---

## [1.0.0.0] - 2026-05-17

### Added

- Initial public source package of waltrone1 Stundenrechner
- Windows desktop interface based on CustomTkinter
- German UI for working-time tracking
- Monthly target-hour management
- Daily work-entry tracking
- Automatic monthly carry-over balance
- Month overview with traffic-light status colors
- Vacation day tracking, including full and half days
- Sick-day tracking, including full and half days
- Annual vacation and sick-day overview
- Configurable standard day hours for absence calculation
- Optional calendar input via `tkcalendar`
- Light / dark mode support
- Autosave to local JSON data file
- Application icon
- GitHub repository structure with README, LICENSE, CHANGELOG, docs and build helper files
- PyInstaller / Inno Setup build notes for creating a Windows executable and installer

### Notes

- waltrone1 Stundenrechner is a local calculation and documentation helper.
- The application does not automatically upload, publish or synchronize user data.
- Users should verify calculations before using them for payroll, accounting or official documentation.

---

## Versioning

This project uses a simple version format:

```text
MAJOR.MINOR.PATCH.BUILD
```
