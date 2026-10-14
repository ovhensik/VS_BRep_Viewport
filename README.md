# USD BRep Viewport for Visual Studio

A Visual Studio extension that runs NVIDIA USD BRep Python scripts and previews their NURBS-based models as tessellated meshes in a dockable 3D viewport. Modeling operations remain exact in USD BRep; the viewport displays a tessellated copy.

## Features

- Runs the active, saved Python file against a local NVIDIA `usd-brep` build.
- Shows the returned Brep (or list of Breps) as an interactive shaded triangle mesh in a dockable tool window.
- Left-drag to orbit, scroll to zoom, and a **Home View** button to frame the model.
- A **Browse...** button to select a different `usd-brep` checkout.
- Errors and status messages are shown in the viewport status line.

## Requirements

- Visual Studio 2019 or 2022 (Community, Professional or Enterprise) with the **Visual Studio extension development** workload. In Visual Studio Installer, choose **Modify** for your version, select that workload, then choose **Modify** to install it. It includes the Visual Studio SDK, the VSSDK packaging tools and the .NET Framework targeting tools needed by the extension.
- .NET Framework 4.7.2 targeting pack (normally installed by the extension workload).
- A local checkout of NVIDIA `usd-brep` (default location `%USERPROFILE%\usd-brep`) built in **Release / x64** using `prebuild.bat` and `repo.bat build`.
- The repo's Python GUI environment with NumPy installed. If `usd-brep\.venv\Scripts\python.exe` is missing, run `uv sync --group gui` from the repo root.

## Project layout

- `source\`: the Visual Studio package, tool window and viewport control.
- `scripts\usd_brep_worker.py`: the Python worker embedded in the extension. It runs your script and returns the tessellated mesh as JSON.
- `examples\`: sample scripts (`box.py`, `muzzle_break.py`) and `mb.usda`.

## Build and install

1. Open `UsdBrepViewport.csproj` in Visual Studio.
2. Build the project in Release.
3. Find `UsdBrepViewport.vsix` in `bin\Release` and double-click it to install. Close Visual Studio if the installer asks.
4. Start Visual Studio, open the `usd-brep` solution or a Python file, and choose **View → Other Windows → USD BRep Viewport**.

The tool window defaults to `%USERPROFILE%\usd-brep`. Use its **Browse...** button to select a different checkout. The extension runs the repo's `.venv` Python interpreter (so NumPy is available for mesh conversion) and imports `_omni_solid` from the selected build, matching the repository's own GUI.

## Try it

Open the included `examples\box.py` or `examples\muzzle_break.py` in Visual Studio (or create and save a Python file such as this):

```python
import _omni_solid as sm

result = sm.boolean_difference(
    sm.create_box((0, 0, 0), 10, 10, 10),
    sm.create_sphere((5, 5, 5), 4),
)
```

Make that file the active Visual Studio document and click **Run Active Python File**. The extension saves the document, runs it with the repo's Python environment and DLLs from the selected USD BRep build, tessellates `result`, then updates the viewport. Assign a single Brep or a list of Breps to `result`.

Drag with the left mouse button to orbit, scroll to zoom, and use **Home View** to frame the model.

## Troubleshooting

- **"The repo Python environment is missing"**: run `uv sync --group gui` from the `usd-brep` folder.
- **"Release build not found"**: build `usd-brep` in Release / x64 with `prebuild.bat` and `repo.bat build`.
- **"Your script must assign the model to a variable named `result`"** or **"did not produce any displayable faces"**: make sure the script assigns a non-empty Brep (or list of Breps) to `result`.
- **Import or DLL errors**: usually an incomplete `usd-brep` build, or the wrong folder selected with **Browse...**.

## Current limits

- This is an early prototype (v0.1.x) for Windows x64 only, and it is read-only: it displays tessellated triangles but does not edit faces/edges, show CAD feature history, or replace a production CAD renderer.
- The viewport is a dockable Visual Studio tool window, while the code stays in Visual Studio's normal editor.
- Scripts run in a child Python process. The script must produce a `result` variable; errors are shown in the viewport status line.
- The bridge targets the Windows x64 Release build layout of `usd-brep`.
