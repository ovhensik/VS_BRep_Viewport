using System;
using System.ComponentModel.Design;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.VisualStudio.Shell;
using Microsoft.VisualStudio.Shell.Interop;

namespace UsdBrepViewport
{
    [PackageRegistration(UseManagedResourcesOnly = true, AllowsBackgroundLoading = true)]
    [ProvideAutoLoad(UIContextGuids80.NoSolution, PackageAutoLoadFlags.BackgroundLoad)]
    [InstalledProductRegistration("USD BRep Viewport", "Dockable viewport for NVIDIA USD BRep scripts", "0.1.0")]
    [ProvideMenuResource("Menus.ctmenu", 1)]
    [ProvideToolWindow(typeof(ViewportToolWindow))]
    [Guid(PackageGuidString)]
    public sealed class UsdBrepViewportPackage : AsyncPackage
    {
        public const string PackageGuidString = "6c55c61b-9857-49e7-a8e5-775c98500103";
        private static readonly Guid CommandSet = new Guid("52ac8928-8fbe-4de5-8b35-c1f7403031a5");
        private const int ShowViewportCommandId = 0x0100;

        protected override async System.Threading.Tasks.Task InitializeAsync(CancellationToken cancellationToken, IProgress<ServiceProgressData> progress)
        {
            await base.InitializeAsync(cancellationToken, progress).ConfigureAwait(false);
            await JoinableTaskFactory.SwitchToMainThreadAsync(cancellationToken);

            var commandService = await GetServiceAsync(typeof(IMenuCommandService)).ConfigureAwait(true) as OleMenuCommandService;
            if (commandService != null)
            {
                var command = new MenuCommand(ShowViewport, new CommandID(CommandSet, ShowViewportCommandId));
                commandService.AddCommand(command);
            }
        }

        private void ShowViewport(object sender, EventArgs e)
        {
            ThreadHelper.ThrowIfNotOnUIThread();
            JoinableTaskFactory.RunAsync(async delegate
            {
                var window = await FindToolWindowAsync(typeof(ViewportToolWindow), 0, true, DisposalToken);
                if (window?.Frame is IVsWindowFrame frame)
                    Microsoft.VisualStudio.ErrorHandler.ThrowOnFailure(frame.Show());
            });
        }
    }
}
