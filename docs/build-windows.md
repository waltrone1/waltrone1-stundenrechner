# Windows Build Notes

These notes describe a simple Windows build workflow for waltrone1 Stundenrechner.

## 1. Create a virtual environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip setuptools wheel
```

## 2. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pyinstaller
```

## 3. Build executable with PyInstaller

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --name "waltrone1-Stundenrechner" `
  --icon ".\waltrone1-Stundenrechner.ico" `
  --paths "." `
  --hidden-import "customtkinter" `
  --hidden-import "tkcalendar" `
  --hidden-import "babel.numbers" `
  --hidden-import "babel.dates" `
  --hidden-import "PIL" `
  --hidden-import "PIL.Image" `
  --hidden-import "PIL.ImageTk" `
  --hidden-import "PIL.IcoImagePlugin" `
  --collect-submodules "customtkinter" `
  --collect-submodules "tkcalendar" `
  --collect-submodules "PIL" `
  --windowed `
  ".\waltrone1-stundenrechner.py"
```

Expected result:

```text
dist\waltrone1-Stundenrechner\
```

Use the complete generated folder, not only the EXE file.

## 4. Optional installer build

The folder `py2exe/` contains an example Inno Setup script.

Typical build folder layout:

```text
C:\Build
|-- waltrone1-Stundenrechner\
|   |-- _internal\
|   `-- waltrone1-Stundenrechner.exe
|-- waltrone1-Stundenrechner.iss
`-- waltrone1-Stundenrechner.ico
```

Open the `.iss` file in Inno Setup and compile it.

Expected installer output:

```text
C:\Build\Installer\waltrone1-Stundenrechner-Setup-x64.exe
```
