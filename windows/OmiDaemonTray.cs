using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace OmiDaemon
{
    public class TrayApplication : Form
    {
        private NotifyIcon trayIcon;
        private ContextMenuStrip trayMenu;
        private ToolStripMenuItem statusMenuItem;
        private ToolStripMenuItem pauseResumeMenuItem;
        private ToolStripMenuItem autoStartMenuItem;
        private Timer logWatcherTimer;
        private string projectRoot;
        private string logFilePath;
        private string drivePath = @"G:\My Drive\OMI";
        private string obsidianPath = @"C:\Users\andri\Documents\Agentic Workflow Repository\personal\Obsidian-Vault-main\Executive Briefs";
        private long lastLogLength = 0;
        private bool isPaused = false;

        [STAThread]
        public static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new TrayApplication());
        }

        public TrayApplication()
        {
            // Determine project root directory
            string exeDir = AppDomain.CurrentDomain.BaseDirectory;
            if (File.Exists(Path.Combine(exeDir, "pyproject.toml")))
            {
                projectRoot = exeDir;
            }
            else if (File.Exists(Path.Combine(exeDir, "..", "pyproject.toml")))
            {
                projectRoot = Path.GetFullPath(Path.Combine(exeDir, ".."));
            }
            else
            {
                projectRoot = @"C:\Users\andri\Documents\Agentic Workflow Repository\personal\OmiDaemon";
            }

            logFilePath = Path.Combine(projectRoot, "logs", "omidaemon.log");

            InitializeComponents();
            StartDaemonIfNotRunning();

            // Set up background log watcher for notifications
            logWatcherTimer = new Timer();
            logWatcherTimer.Interval = 3000;
            logWatcherTimer.Tick += LogWatcherTimer_Tick;
            logWatcherTimer.Start();
        }

        private void InitializeComponents()
        {
            trayMenu = new ContextMenuStrip();

            var titleItem = new ToolStripMenuItem("OmiDaemon — Executive AI");
            titleItem.Font = new Font(titleItem.Font, FontStyle.Bold);
            titleItem.Enabled = false;
            trayMenu.Items.Add(titleItem);

            statusMenuItem = new ToolStripMenuItem("Status: Watching Google Drive (OMI)");
            statusMenuItem.Enabled = false;
            trayMenu.Items.Add(statusMenuItem);

            trayMenu.Items.Add(new ToolStripSeparator());

            var scanItem = new ToolStripMenuItem("Scan Google Drive Now", null, OnScanNow);
            trayMenu.Items.Add(scanItem);

            var obsidianItem = new ToolStripMenuItem("Open Obsidian Notes", null, OnOpenObsidian);
            trayMenu.Items.Add(obsidianItem);

            var driveItem = new ToolStripMenuItem("Open Google Drive (OMI) Folder", null, OnOpenDrive);
            trayMenu.Items.Add(driveItem);

            var logItem = new ToolStripMenuItem("View Activity Log", null, OnViewLog);
            trayMenu.Items.Add(logItem);

            trayMenu.Items.Add(new ToolStripSeparator());

            pauseResumeMenuItem = new ToolStripMenuItem("Pause Monitoring", null, OnTogglePause);
            trayMenu.Items.Add(pauseResumeMenuItem);

            autoStartMenuItem = new ToolStripMenuItem("Auto-Start with Windows", null, OnToggleAutoStart);
            autoStartMenuItem.Checked = IsAutoStartEnabled();
            trayMenu.Items.Add(autoStartMenuItem);

            trayMenu.Items.Add(new ToolStripSeparator());

            var exitItem = new ToolStripMenuItem("Exit OmiDaemon", null, OnExit);
            trayMenu.Items.Add(exitItem);

            trayIcon = new NotifyIcon();
            trayIcon.Text = "OmiDaemon: Wearable AI Assistant";
            trayIcon.ContextMenuStrip = trayMenu;
            trayIcon.Visible = true;

            // Load custom icon if available
            string iconPath = Path.Combine(projectRoot, "assets", "icon.ico");
            if (File.Exists(iconPath))
            {
                try { trayIcon.Icon = new Icon(iconPath); } catch { trayIcon.Icon = SystemIcons.Application; }
            }
            else
            {
                trayIcon.Icon = SystemIcons.Application;
            }

            trayIcon.DoubleClick += (s, e) => OnOpenObsidian(s, e);

            // Hide the form itself
            this.WindowState = FormWindowState.Minimized;
            this.ShowInTaskbar = false;
            this.Visible = false;

            trayIcon.ShowBalloonTip(3000, "OmiDaemon Active", "Watching Google Drive for Omi wearable transcripts.", ToolTipIcon.Info);
        }

        private void StartDaemonIfNotRunning()
        {
            RunPythonCommand("start-bg");
        }

        private void OnScanNow(object sender, EventArgs e)
        {
            trayIcon.ShowBalloonTip(2000, "OmiDaemon", "Scanning Google Drive for new transcripts...", ToolTipIcon.Info);
            System.Threading.ThreadPool.QueueUserWorkItem(_ =>
            {
                RunPythonCommand("start --once");
            });
        }

        private void OnOpenObsidian(object sender, EventArgs e)
        {
            if (Directory.Exists(obsidianPath))
            {
                Process.Start("explorer.exe", "\"" + obsidianPath + "\"");
            }
            else
            {
                string parent = Path.GetDirectoryName(obsidianPath);
                if (Directory.Exists(parent)) Process.Start("explorer.exe", "\"" + parent + "\"");
            }
        }

        private void OnOpenDrive(object sender, EventArgs e)
        {
            if (Directory.Exists(drivePath))
            {
                Process.Start("explorer.exe", "\"" + drivePath + "\"");
            }
            else
            {
                MessageBox.Show("Drive folder not found: " + drivePath, "OmiDaemon");
            }
        }

        private void OnViewLog(object sender, EventArgs e)
        {
            if (File.Exists(logFilePath))
            {
                Process.Start("notepad.exe", "\"" + logFilePath + "\"");
            }
            else
            {
                MessageBox.Show("No log file found yet at: " + logFilePath, "OmiDaemon");
            }
        }

        private void OnTogglePause(object sender, EventArgs e)
        {
            isPaused = !isPaused;
            if (isPaused)
            {
                RunPythonCommand("stop-bg");
                statusMenuItem.Text = "Status: Paused";
                pauseResumeMenuItem.Text = "Resume Monitoring";
                trayIcon.ShowBalloonTip(2000, "OmiDaemon", "Background monitoring paused.", ToolTipIcon.Warning);
            }
            else
            {
                RunPythonCommand("start-bg");
                statusMenuItem.Text = "Status: Watching Google Drive (OMI)";
                pauseResumeMenuItem.Text = "Pause Monitoring";
                trayIcon.ShowBalloonTip(2000, "OmiDaemon", "Background monitoring resumed.", ToolTipIcon.Info);
            }
        }

        private bool IsAutoStartEnabled()
        {
            try
            {
                var psi = new ProcessStartInfo("schtasks", "/Query /TN OmiDaemon")
                {
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    RedirectStandardOutput = true
                };
                var proc = Process.Start(psi);
                proc.WaitForExit();
                return proc.ExitCode == 0;
            }
            catch { return false; }
        }

        private void OnToggleAutoStart(object sender, EventArgs e)
        {
            if (autoStartMenuItem.Checked)
            {
                // Remove task
                Process.Start(new ProcessStartInfo("schtasks", "/Delete /TN OmiDaemon /F") { CreateNoWindow = true, UseShellExecute = false });
                autoStartMenuItem.Checked = false;
                trayIcon.ShowBalloonTip(2000, "OmiDaemon", "Auto-start disabled.", ToolTipIcon.Info);
            }
            else
            {
                RunPythonCommand("install-startup");
                autoStartMenuItem.Checked = true;
                trayIcon.ShowBalloonTip(2000, "OmiDaemon", "Auto-start enabled for Windows login.", ToolTipIcon.Info);
            }
        }

        private void LogWatcherTimer_Tick(object sender, EventArgs e)
        {
            if (!File.Exists(logFilePath)) return;
            try
            {
                var fi = new FileInfo(logFilePath);
                if (fi.Length > lastLogLength && lastLogLength > 0)
                {
                    using (var fs = new FileStream(logFilePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    {
                        fs.Seek(lastLogLength, SeekOrigin.Begin);
                        using (var reader = new StreamReader(fs))
                        {
                            string newContent = reader.ReadToEnd();
                            foreach (var line in newContent.Split('\n'))
                            {
                                if (line.Contains("Successfully processed & routed"))
                                {
                                    string title = line.Trim();
                                    trayIcon.ShowBalloonTip(4000, "Transcript Processed", title, ToolTipIcon.Info);
                                }
                            }
                        }
                    }
                }
                lastLogLength = fi.Length;
            }
            catch { }
        }

        private void RunPythonCommand(string args)
        {
            try
            {
                var psi = new ProcessStartInfo("python", "-m omidaemon.cli " + args)
                {
                    WorkingDirectory = projectRoot,
                    CreateNoWindow = true,
                    UseShellExecute = false
                };
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to run python command: " + ex.Message, "OmiDaemon Error");
            }
        }

        private void OnExit(object sender, EventArgs e)
        {
            trayIcon.Visible = false;
            logWatcherTimer.Stop();
            RunPythonCommand("stop-bg");
            Application.Exit();
        }

        protected override void SetVisibleCore(bool value)
        {
            base.SetVisibleCore(false);
        }
    }
}
