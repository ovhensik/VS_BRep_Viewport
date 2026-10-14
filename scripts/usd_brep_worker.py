"""Run a saved USD BRep Python script and return its display mesh as JSON."""
from __future__ import annotations

import json
import os
import sys
import traceback


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: usd_brep_worker.py <repo-root> <script.py> <mesh.json>", file=sys.stderr)
        return 2

    repo, script_path, mesh_path = map(os.path.abspath, sys.argv[1:])
    build = os.path.join(repo, "_build", "windows-x86_64", "release")
    usd_root = os.path.join(repo, "_build", "target-deps", "usd", "release")
    python_root = os.path.join(repo, "_build", "target-deps", "python")
    sys.path.insert(0, repo)
    sys.path.insert(0, build)
    dll_directory_handles = []
    if hasattr(os, "add_dll_directory"):
        for directory in (
            build,
            os.path.join(build, "extraLibs"),
            os.path.join(usd_root, "lib"),
            os.path.join(usd_root, "bin"),
            python_root,
        ):
            if os.path.isdir(directory):
                dll_directory_handles.append(os.add_dll_directory(directory))
    os.environ["OMNISOLID_PLUGIN_PATH"] = os.path.join(
        repo, "_build", "schema", "omniSolid", "resources"
    )

    try:
        # Match the import used by the repository's own SMLib GUI.
        import _omni_solid as sm

        with open(script_path, "r", encoding="utf-8-sig") as stream:
            source = stream.read()
        namespace = {
            "__name__": "__main__",
            "__file__": script_path,
            "sm": sm,
            "usd_brep": sm,
        }
        old_cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(script_path))
            exec(compile(source, script_path, "exec"), namespace, namespace)
        finally:
            os.chdir(old_cwd)

        result = namespace.get("result")
        if result is None:
            raise RuntimeError("Your script must assign the model to a variable named `result`.")
        results = list(result) if isinstance(result, (list, tuple)) else [result]
        all_points = []
        all_normals = []
        all_triangles = []

        for body in results:
            mesh_body = body if isinstance(body, sm.PolyBrep) else sm.tessellate(
                body,
                chord_height_tolerance=0.005,
                curve_angle_tolerance_deg=8.0,
                surface_angle_tolerance_deg=8.0,
            )
            if mesh_body is None:
                continue
            # Face-varying normals are smooth across each curved source face but
            # remain split at CAD edges between distinct faces.
            arrays = mesh_body.to_numpy_arrays(face_varying_normals=True)
            points = arrays.get("points", ())
            normals = arrays.get("normals", ())
            face_stream = arrays.get("faces", ())
            point_values = [[float(value) for value in point[:3]] for point in points]
            normal_values = [[float(value) for value in normal[:3]] for normal in normals]
            cursor = 0
            while cursor < len(face_stream):
                count = int(face_stream[cursor])
                face = [int(value) for value in face_stream[cursor + 1:cursor + 1 + count]]
                if len(face) < 3 or cursor + count + 1 > len(face_stream):
                    raise RuntimeError("USD BRep returned an invalid tessellation face stream.")
                if len(normal_values) < len(face):
                    raise RuntimeError("USD BRep returned fewer face-corner normals than mesh vertices.")
                offset = len(all_points) // 3
                for corner, point_index in enumerate(face):
                    if point_index < 0 or point_index >= len(point_values):
                        raise RuntimeError("USD BRep returned an out-of-range mesh index.")
                    all_points.extend(point_values[point_index])
                    all_normals.extend(normal_values.pop(0))
                # The face corners were copied into a face-local vertex block above,
                # so triangulate with local corner offsets rather than source indices.
                for index in range(1, len(face) - 1):
                    all_triangles.extend((offset, offset + index, offset + index + 1))
                cursor += count + 1

        if not all_triangles:
            raise RuntimeError("The script's `result` did not produce any displayable faces.")
        with open(mesh_path, "w", encoding="utf-8") as stream:
            json.dump({"vertices": all_points, "normals": all_normals, "triangles": all_triangles}, stream)
        print("Displayed {} triangle(s).".format(len(all_triangles) // 3))
        return 0
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
