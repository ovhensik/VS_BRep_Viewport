using System.Runtime.InteropServices;
using Microsoft.VisualStudio.Shell;

namespace UsdBrepViewport
{
    [Guid("2cb1e5cc-9c6e-4d0c-a351-a3d365d0fa3d")]
    public sealed class ViewportToolWindow : ToolWindowPane
    {
        public ViewportToolWindow() : base(null)
        {
            Caption = "USD BRep Viewport";
            Content = new ViewportControl();
        }
    }
}
