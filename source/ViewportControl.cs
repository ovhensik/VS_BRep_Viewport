using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Media3D;
using EnvDTE;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;

namespace UsdBrepViewport
{
    internal sealed class ViewportControl : UserControl
    {
        private readonly TextBox _repoPath;
        private readonly TextBlock _status;
        private readonly Viewport3D _viewport;
        private readonly Model3DGroup _scene;
        private readonly PerspectiveCamera _camera;
        private Point _lastMouse;
        private bool _dragging;
        private double _azimuth = 35.0;
        private double _elevation = 25.0;
        private double _distance = 30.0;
        private Point3D _target = new Point3D(0, 0, 0);

        public ViewportControl()
        {
            var root = new DockPanel { LastChildFill = true, Background = new SolidColorBrush(Color.FromRgb(28, 35, 45)) };
            var header = new StackPanel { Orientation = Orientation.Vertical, Margin = new Thickness(8) };
            DockPanel.SetDock(header, Dock.Top);

            var repoRow = new DockPanel { Margin = new Thickness(0, 0, 0, 5) };
            repoRow.Children.Add(new TextBlock { Text = "USD BRep repo", Foreground = Brushes.White, Width = 105, VerticalAlignment = VerticalAlignment.Center });
            _repoPath = new TextBox { Text = DefaultRepoPath(), MinWidth = 180, Margin = new Thickness(0, 0, 5, 0) };
            repoRow.Children.Add(_repoPath);
            var browse = new Button { Content = "Browse...", Padding = new Thickness(8, 3, 8, 3) };
            browse.Click += BrowseRepo;
            DockPanel.SetDock(browse, Dock.Right);
            repoRow.Children.Add(browse);
            header.Children.Add(repoRow);

            var actions = new StackPanel { Orientation = Orientation.Horizontal };
            var run = new Button { Content = "Run Active Python File", Padding = new Thickness(10, 5, 10, 5), Margin = new Thickness(0, 0, 8, 0) };
            run.Click += async (s, e) => await RunActiveScriptAsync();
            actions.Children.Add(run);
            var reset = new Button { Content = "Home View", Padding = new Thickness(10, 5, 10, 5) };
            reset.Click += (s, e) => SetCamera(_target, _distance);
            actions.Children.Add(reset);
            _status = new TextBlock { Text = "Open a Python file, assign its output to `result`, then run it.", Foreground = Brushes.Gainsboro, Margin = new Thickness(12, 0, 0, 0), VerticalAlignment = VerticalAlignment.Center, TextWrapping = TextWrapping.Wrap };
            actions.Children.Add(_status);
            header.Children.Add(actions);
            root.Children.Add(header);

            _scene = new Model3DGroup();
            _scene.Children.Add(new AmbientLight(Color.FromRgb(115, 122, 133)));
            _scene.Children.Add(new DirectionalLight(Color.FromRgb(230, 235, 245), new Vector3D(-1, -2, -3)));
            _scene.Children.Add(new DirectionalLight(Color.FromRgb(95, 110, 130), new Vector3D(2, 1, 1)));

            _camera = new PerspectiveCamera { FieldOfView = 38, UpDirection = new Vector3D(0, 0, 1) };
            _viewport = new Viewport3D { Camera = _camera, ClipToBounds = true };
            _viewport.Children.Add(new ModelVisual3D { Content = _scene });
            _viewport.MouseLeftButtonDown += ViewportMouseDown;
            _viewport.MouseLeftButtonUp += ViewportMouseUp;
            _viewport.MouseMove += ViewportMouseMove;
            _viewport.MouseWheel += ViewportMouseWheel;
            var viewHost = new Grid { Background = new SolidColorBrush(Color.FromRgb(22, 28, 37)) };
            viewHost.Children.Add(_viewport);
            root.Children.Add(viewHost);
            Content = root;
            SetCamera(_target, _distance);
        }

        private static string DefaultRepoPath()
        {
            var configured = Environment.GetEnvironmentVariable("USD_BREP_ROOT");
            if (!string.IsNullOrWhiteSpace(configured)) return configured;
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "usd-brep");
        }

        private void BrowseRepo(object sender, RoutedEventArgs e)
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            using (var dialog = new System.Windows.Forms.FolderBrowserDialog())
            {
                dialog.Description = "Select the NVIDIA usd-brep checkout";
                dialog.SelectedPath = Directory.Exists(_repoPath.Text) ? _repoPath.Text : DefaultRepoPath();
                if (dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK)
                    _repoPath.Text = dialog.SelectedPath;
            }
        }

        private async System.Threading.Tasks.Task RunActiveScriptAsync()
        {
            try
            {
                _status.Text = "Saving and running the active Python file...";
                var scriptPath = await GetActiveDocumentPathAsync();
                if (string.IsNullOrWhiteSpace(scriptPath) || !File.Exists(scriptPath) || !string.Equals(Path.GetExtension(scriptPath), ".py", StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Open and save a .py file in the Visual Studio editor first.");

                var repo = _repoPath.Text.Trim();
                if (!Directory.Exists(repo)) throw new DirectoryNotFoundException("USD BRep repo folder not found: " + repo);
                var release = Path.Combine(repo, "_build", "windows-x86_64", "release");
                var python = Path.Combine(repo, ".venv", "Scripts", "python.exe");
                if (!Directory.Exists(release))
                    throw new DirectoryNotFoundException("Release build not found. Build USD BRep first with prebuild.bat and repo.bat build.");
                if (!File.Exists(python))
                    throw new FileNotFoundException("The repo Python environment is missing. From the usd-brep folder, run `uv sync --group gui` to install NumPy, then try again.");

                var worker = ExtractWorker();
                var meshFile = Path.Combine(Path.GetTempPath(), "usd_brep_viewport_" + Guid.NewGuid().ToString("N") + ".json");
                var start = new ProcessStartInfo
                {
                    FileName = python,
                    Arguments = Quote(worker) + " " + Quote(repo) + " " + Quote(scriptPath) + " " + Quote(meshFile),
                    WorkingDirectory = Path.GetDirectoryName(scriptPath),
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true
                };
                var buildBin = release;
                var usdRoot = Path.Combine(repo, "_build", "target-deps", "usd", "release");
                var pythonRoot = Path.Combine(repo, "_build", "target-deps", "python");
                start.EnvironmentVariables["PYTHONPATH"] = buildBin + Path.PathSeparator + Path.Combine(release, "site");
                start.EnvironmentVariables["PATH"] = string.Join(Path.PathSeparator.ToString(), new[] { buildBin, Path.Combine(buildBin, "extraLibs"), Path.Combine(usdRoot, "lib"), Path.Combine(usdRoot, "bin"), pythonRoot, Environment.GetEnvironmentVariable("PATH") });
                start.EnvironmentVariables["OMNISOLID_PLUGIN_PATH"] = Path.Combine(repo, "_build", "schema", "omniSolid", "resources");

                string stdout;
                string stderr;
                using (var process = new System.Diagnostics.Process { StartInfo = start })
                {
                    process.Start();
                    var outTask = process.StandardOutput.ReadToEndAsync();
                    var errTask = process.StandardError.ReadToEndAsync();
                    await System.Threading.Tasks.Task.Run(() => process.WaitForExit());
                    stdout = await outTask;
                    stderr = await errTask;
                    if (process.ExitCode != 0)
                        throw new InvalidOperationException(string.IsNullOrWhiteSpace(stderr) ? stdout : stderr);
                }

                var json = File.ReadAllText(meshFile);
                File.Delete(meshFile);
                ShowMesh(json);
                _status.Text = string.IsNullOrWhiteSpace(stdout) ? "Model updated from " + Path.GetFileName(scriptPath) : stdout.Trim();
            }
            catch (Exception ex)
            {
                _status.Text = ex.Message;
            }
        }

        private static string Quote(string value) => "\"" + value.Replace("\"", "\\\"") + "\"";

        private async System.Threading.Tasks.Task<string> GetActiveDocumentPathAsync()
        {
            await ThreadHelper.JoinableTaskFactory.SwitchToMainThreadAsync();
            var dte = Microsoft.VisualStudio.Shell.ServiceProvider.GlobalProvider.GetService(typeof(SDTE)) as EnvDTE.DTE;
            if (dte == null || dte.ActiveDocument == null) return null;
            dte.ExecuteCommand("File.SaveAll");
            return dte.ActiveDocument.FullName;
        }

        private string ExtractWorker()
        {
            var path = Path.Combine(Path.GetTempPath(), "usd_brep_viewport_worker.py");
            using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("UsdBrepViewport.usd_brep_worker.py"))
            {
                if (stream == null) throw new FileNotFoundException("Embedded Python worker was not packaged.");
                using (var output = File.Create(path)) stream.CopyTo(output);
            }
            return path;
        }

        private void ShowMesh(string json)
        {
            // Fine CAD tessellations can produce JSON well above the serializer's
            // small default limit, so allow the complete mesh payload to load.
            var serializer = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
            var data = serializer.Deserialize<Dictionary<string, object>>(json);
            var vertices = ((System.Collections.IEnumerable)data["vertices"]).Cast<object>().Select(value => Convert.ToDouble(value, CultureInfo.InvariantCulture)).ToArray();
            var normals = ((System.Collections.IEnumerable)data["normals"]).Cast<object>().Select(value => Convert.ToDouble(value, CultureInfo.InvariantCulture)).ToArray();
            var triangles = ((System.Collections.IEnumerable)data["triangles"]).Cast<object>().Select(value => Convert.ToInt32(value, CultureInfo.InvariantCulture)).ToArray();
            if (vertices.Length < 9 || triangles.Length < 3 || normals.Length != vertices.Length) throw new InvalidDataException("The script returned an incomplete display mesh.");

            var count = vertices.Length / 3;
            var min = new double[] { double.MaxValue, double.MaxValue, double.MaxValue };
            var max = new double[] { double.MinValue, double.MinValue, double.MinValue };
            for (var i = 0; i < count; i++)
                for (var axis = 0; axis < 3; axis++)
                {
                    var v = vertices[i * 3 + axis];
                    min[axis] = Math.Min(min[axis], v);
                    max[axis] = Math.Max(max[axis], v);
                }
            var center = new Point3D((min[0] + max[0]) / 2, (min[1] + max[1]) / 2, (min[2] + max[2]) / 2);
            var span = Math.Max(max[0] - min[0], Math.Max(max[1] - min[1], max[2] - min[2]));
            if (span <= 1e-9) span = 1;

            var mesh = new MeshGeometry3D();
            for (var i = 0; i < count; i++)
            {
                mesh.Positions.Add(ReadPoint(vertices, i));
                var normal = new Vector3D(normals[i * 3], normals[i * 3 + 1], normals[i * 3 + 2]);
                if (normal.LengthSquared > 1e-20) normal.Normalize(); else normal = new Vector3D(0, 0, 1);
                mesh.Normals.Add(normal);
            }
            foreach (var index in triangles)
            {
                if (index < 0 || index >= count) throw new InvalidDataException("Mesh index is out of range.");
                mesh.TriangleIndices.Add(index);
            }
            var material = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(180, 194, 208)));
            _scene.Children.Clear();
            _scene.Children.Add(new AmbientLight(Color.FromRgb(105, 110, 120)));
            _scene.Children.Add(new DirectionalLight(Color.FromRgb(245, 245, 245), new Vector3D(-1, -2, -3)));
            _scene.Children.Add(new DirectionalLight(Color.FromRgb(90, 110, 145), new Vector3D(2, 1, 1)));
            _scene.Children.Add(new GeometryModel3D(mesh, material) { BackMaterial = material });
            _target = center;
            SetCamera(center, span * 2.8);
            _status.Text = string.Format(CultureInfo.InvariantCulture, "Loaded {0:N0} triangles", triangles.Length / 3);
        }

        private static Point3D ReadPoint(double[] vertices, int index)
        {
            if (index < 0 || index * 3 + 2 >= vertices.Length / 3 * 3) throw new InvalidDataException("Mesh index is out of range.");
            return new Point3D(vertices[index * 3], vertices[index * 3 + 1], vertices[index * 3 + 2]);
        }

        private void SetCamera(Point3D target, double distance)
        {
            _target = target;
            _distance = Math.Max(distance, 0.01);
            var az = _azimuth * Math.PI / 180.0;
            var el = _elevation * Math.PI / 180.0;
            var pos = new Point3D(
                target.X + _distance * Math.Cos(el) * Math.Cos(az),
                target.Y + _distance * Math.Cos(el) * Math.Sin(az),
                target.Z + _distance * Math.Sin(el));
            _camera.Position = pos;
            _camera.LookDirection = target - pos;
            _camera.UpDirection = new Vector3D(0, 0, 1);
        }

        private void ViewportMouseDown(object sender, MouseButtonEventArgs e)
        {
            _dragging = true; _lastMouse = e.GetPosition(_viewport); _viewport.CaptureMouse();
        }
        private void ViewportMouseUp(object sender, MouseButtonEventArgs e) { _dragging = false; _viewport.ReleaseMouseCapture(); }
        private void ViewportMouseMove(object sender, MouseEventArgs e)
        {
            if (!_dragging || e.LeftButton != MouseButtonState.Pressed) return;
            var point = e.GetPosition(_viewport); var dx = point.X - _lastMouse.X; var dy = point.Y - _lastMouse.Y;
            _lastMouse = point; _azimuth += dx * 0.6; _elevation = Math.Max(-85, Math.Min(85, _elevation - dy * 0.5));
            SetCamera(_target, _distance);
        }
        private void ViewportMouseWheel(object sender, MouseWheelEventArgs e) { SetCamera(_target, _distance * (e.Delta > 0 ? 0.85 : 1.18)); }
    }
}
