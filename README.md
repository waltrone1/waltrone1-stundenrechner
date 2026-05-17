# waltrone1 Stundenrechner

**waltrone1 Stundenrechner** is a free Windows desktop time and minijob hour calculator by **WALTRONE**.

It helps you manage monthly working-hour targets, daily time entries, automatic carry-over balances, vacation days and sick days in a clean German-language desktop interface.

The tool is designed for Windows users, admins, employees, part-time workers, minijob workflows and private productivity use cases where monthly hours should be tracked locally without a cloud service.

---

## Features

- Modern Windows desktop interface based on CustomTkinter
- German user interface
- Monthly working-hour target tracking
- Daily time entries for work days
- Automatic monthly carry-over balance
- Month overview with traffic-light status colors
- Vacation tracking: full day and half day
- Sick-day tracking: full day and half day
- Annual vacation / sick-day overview
- Configurable standard day hours for absence calculation
- Optional calendar input via `tkcalendar`
- Light / dark mode support
- Autosave to local JSON data file
- Local application data folder under the user profile
- Application icon included
- PyInstaller / Inno Setup build notes for creating a Windows executable and installer

---

## Use Cases

This tool can be useful for:

- Tracking monthly minijob hours
- Checking whether the current month is below, on target or above the planned hours
- Keeping a running balance across multiple months
- Recording vacation and sick days in the same overview
- Managing private working-time documentation
- Preparing a simple local time overview without spreadsheets
- Using a small Windows utility as part of a personal productivity workflow

---

## Project Status

This project is prepared as a public source package.

The repository package provides source files, documentation, license information, build-related files and metadata for a clean GitHub repository setup.

Current version:

```text
1.0.0.0
```

---

## Download

A release ZIP can be published through the GitHub Releases section.

A WALTRONE download/support page may also be used for users who prefer a simple download option or want to support the project voluntarily.

---

## Repository Structure

```text
waltrone1-stundenrechner/
|
|-- README.md
|-- CHANGELOG.md
|-- LICENSE
|-- .gitignore
|-- requirements.txt
|-- run.py
|-- waltrone1-stundenrechner.py
|-- waltrone1-Stundenrechner.ico
|-- version_info.txt
|-- GITHUB_REPOSITORY_INFO.txt
|
|-- docs/
|   |-- usage.md
|   |-- build-windows.md
|   `-- original-py2exe-notes.txt
|
|-- py2exe/
|   |-- README.md
|   |-- build_exe_windows.bat
|   `-- waltrone1-Stundenrechner.iss
|
`-- screenshots/
    `-- .gitkeep
```

The main start file is:

```text
run.py
```

The main source file is:

```text
waltrone1-stundenrechner.py
```

The `py2exe/` folder contains build-related helper files for creating a Windows executable and installer.

Generated files such as `.exe`, `.zip`, `build/`, `dist/`, `.venv/` or release folders should not be committed directly to the repository.

Final release packages should be published through GitHub Releases.

---

## Basic Usage

1. Download the latest release ZIP.
2. Extract the ZIP file completely.
3. Install the required Python packages if starting from source.
4. Start the application with `python run.py`.
5. Enter the monthly target hours.
6. Enter daily work entries or absence days.
7. Check the monthly overview and carry-over balance.
8. Review the saved data before using it for documentation.

---

## Build / Source Notes

If the project is started from source, install the required dependencies first:

```text
pip install -r requirements.txt
```

Then start the application with:

```text
python run.py
```

Build-related files for creating a Windows executable are located in:

```text
py2exe/
```

On Windows, the included build script can be used from the `py2exe` folder:

```text
build_exe_windows.bat
```

Generated build output such as `.exe`, `.zip`, `build/`, `dist/` or release folders should not be committed directly to the repository.

Final release packages should be published through GitHub Releases.

---

## Safety Notes

waltrone1 Stundenrechner is a local working-time calculation and documentation helper.

It does not automatically upload data, publish files or synchronize entries with external services.

Important notes:

- The application stores data locally as JSON.
- Always back up important data files before replacing or updating the application.
- Time and absence calculations should be checked manually before payroll or legal use.
- The tool is not a legal, tax or payroll advisory system.
- Local system settings, date formats or manual input errors can affect results.
- Always verify exported or copied information before publishing or submitting it.

---

## License

This project is released under the **WALTRONE Community License**.

You may use this tool for free.

However, the following is not allowed without written permission:

- Commercial resale
- Rebranding
- Selling modified versions
- Commercial integration into paid products or services
- Republishing the project under another name
- Removing WALTRONE branding or author information

For details, see the `LICENSE` file.

---

## About WALTRONE

**WALTRONE** is a GitHub and community project focused on small, useful tools for Windows, automation, productivity and system management.

GitHub handle / domain identity:

```text
waltrone1
```

Project brand:

```text
WALTRONE
```

---

## Support

This tool is free to use.

If you find it useful, you may support the project voluntarily through the official WALTRONE download/support page.

---

## Disclaimer

This tool is provided as-is, without warranty of any kind.

Use it at your own risk.

The author is not responsible for data loss, incorrect calculations, missed working time, payroll decisions, incorrect documentation, system issues or damages caused by the use of this software.
