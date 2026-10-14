# USD BRep Viewport for Visual Studio

This prototype adds a dockable Visual Studio tool window. It runs the active, saved Python file against a local NVIDIA `usd-brep` build and displays the returned Brep as an interactive shaded triangle mesh. The modeling operations remain exact in USD BRep; the viewport uses a tessellated display copy.

## Requirements

- Visual Studio 2019 Community or newer, with **Visual Studio extension development** installed through Visual Studio Installer. On this machine, that workload is currently missing from both Visual Studio 2019 and 2022. In Visual Studio Installer, choose **Modify** for the version you use, select **Visual Studio extension development**, then choose **Modify** to install it. This workload includes the Visual Studio SDK and .NET Framework targeting tools needed by the extension.
- The user's `C:\Users\David\usd-brep` checkout built in **Release / x64** using `prebuild.bat` and `repo.bat build`.
- The repo's Python GUI environment with NumPy installed. If `usd-brep\.venv\Scripts\python.exe` is missing, run `uv sync --group gui` from the repo root.
- .NET Framework 4.7.2 targeting pack (normally installed by the Visual Studio extension workload).
- The Visual Studio 2019 extension workload provides the VSSDK packaging tools used by this project; it does not need to restore SDK packages from NuGet.

## Build and install

1. Open `UsdBrepViewport.csproj` in Visual Studio.
2. Build the project in Release.
3. Find `UsdBrepViewport.vsix` under the project's `bin\Release` output folder and double-click it to install.
4. Restart Visual Studio, open the `usd-brep` solution or a Python file, and choose **View → Other Windows → USD BRep Viewport**.

The tool window defaults to `%USERPROFILE%\usd-brep`. Use its **Browse...** button to select a different checkout. It uses the repo's `.venv` Python 3.12 interpreter so NumPy is available for mesh conversion, and imports `_omni_solid`, matching the repository's own GUI.

## Try it

Open the included `examples\box.py` in Visual Studio (or create and save a Python file such as this):

```python
import _omni_solid as sm

result = sm.boolean_difference(
    sm.create_box((0, 0, 0), 10, 10, 10),
    sm.create_sphere((5, 5, 5), 4),
)
```

Make that file the active Visual Studio document and click **Run Active Python File**. The extension saves the document, runs it with the repo's Python 3.12 environment and DLLs from the selected USD BRep build, tessellates `result`, then updates the viewport. Assign a single Brep or a list of Breps to `result`.

Drag with the left mouse button to orbit, scroll to zoom, and use **Home View** to frame the model.

## Current limits

- The viewport is a dockable Visual Studio tool window, while the code stays in Visual Studio's normal editor.
- This first prototype displays tessellated triangles. It does not edit faces/edges, show CAD feature history, or replace a production CAD renderer.
- Scripts run in a child Python process. The script must produce a `result` variable; errors are shown in the viewport status line.
- The current bridge targets the user's Windows x64 Release build layout.
