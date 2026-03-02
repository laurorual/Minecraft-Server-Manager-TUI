import asyncio
import psutil
import time
import re
import shlex
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, Button, Footer, RichLog, Input

CSS = """
Screen {
    background: black;
    layout: grid;
    grid-size: 5 4;
    grid-rows: 20% 20% 20% 40%;
    grid-columns: 2fr 1fr 1fr 1fr 1fr;
}

#hardware-panel { column-span: 5; row-span: 1; border: round cyan; height: 100%; content-align: center middle; }

#console-panel {
    column-span: 3;
    row-span: 3;
    border: round cyan;
    height: 100%;
    padding: 0; /* Remove preenchimentos extras para não desalinhar o input */
}
#console-log { height: 1fr; background: black; }

/* Campo de digitar comandos corrigido (sem bordas conflitantes) */
#console-input {
    border: none;
    background: #111111;
    color: white;
    height: 3;
    padding: 0 1;
}
#console-input:focus { 
    background: #222222; 
    border: none;
}

#status-container { column-span: 1; row-span: 3; height: 100%; }
.middle-box { border: round cyan; width: 100%; }

/* Ajuste final das proporções para evitar botões cortados */
#status-box { height: 11fr; } 
#uptime-box { height: 4fr; }
#options-box { height: 8fr; }

#players-panel { column-span: 1; row-span: 3; border: round cyan; height: 100%; padding: 0 1; }

.title { text-style: bold; padding-left: 1; }
#status-text { color: red; text-align: center; text-style: bold; margin-top: 1; margin-bottom: 1; }

#uptime-text { color: cyan; text-align: center; text-style: bold; margin-top: 1; }
#uptime-sub { color: gray; text-align: center; margin-top: 1; }

.option-btn { margin-top: 1; }

Button { width: 100%; border: solid cyan; background: black; color: white; height: 3; }
Button:hover { background: cyan; color: black; }
Button:focus { background: black; color: white; border: solid cyan; text-style: none; }
Button:focus:hover { background: cyan; color: black; }
"""

class McManagerApp(App):
    CSS = CSS
    
    BINDINGS = [
        ("f1", "start_server", "Start/Restart"),
        ("f2", "stop_server", "Stop"),
        ("f4", "test_player", "Test Player"),
        ("q", "quit", "Quit")
    ]

    def __init__(self):
        super().__init__()
        self.server_process = None
        self.server_pid = None
        self.server_psutil = None
        self.server_start_time = None
        
        self.allocated_ram = 2  
        self.active_ram = 2     
        self.jvm_args = ""
        
        self.input_mode = "command"
        
        self.online_players = set()
        self.join_regex = re.compile(r": ([a-zA-Z0-9_]{3,16}) joined the game")
        self.leave_regex = re.compile(r": ([a-zA-Z0-9_]{3,16}) left the game")

    def compose(self) -> ComposeResult:
        yield Static("Loading hardware stats...", id="hardware-panel")
        
        with Vertical(id="console-panel"):
            yield RichLog(id="console-log", wrap=True, highlight=True, markup=True)
            yield Input(placeholder="> Type a command...", id="console-input")
        
        with Vertical(id="status-container"):
            with Vertical(id="status-box", classes="middle-box"):
                yield Static("Status", classes="title")
                yield Static("Offline", id="status-text")
                yield Button("Start (F1)", id="btn-start")
                yield Button("Stop (F2)", id="btn-stop")
                
            with Vertical(id="uptime-box", classes="middle-box"):
                yield Static("Uptime", classes="title")
                yield Static("00:00:00", id="uptime-text")
                yield Static("Started at: --:--", id="uptime-sub")
                
            with Vertical(id="options-box", classes="middle-box"):
                yield Static("Other Options", classes="title")
                yield Button("Change RAM limit", id="btn-ram", classes="option-btn")
                yield Button("JVM Arguments", id="btn-args", classes="option-btn")

        yield Static("Players: 0\n", id="players-panel", classes="title")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.update_dashboard)

    def make_bar(self, percent: float, width: int = 40) -> str:
        percent = min(max(percent, 0.0), 100.0)
        filled = int((percent / 100) * width)
        empty = width - filled
        color = "lime" if percent < 60 else "yellow" if percent < 85 else "red"
        return f"\\[[{color}]{'|' * filled}[/{color}]{' ' * empty}\\]"

    def update_dashboard(self) -> None:
        sys_cpu = psutil.cpu_percent()
        sys_ram = psutil.virtual_memory()
        
        sys_cpu_bar = self.make_bar(sys_cpu)
        sys_ram_bar = self.make_bar(sys_ram.percent)
        
        stats = f"[bold cyan]System:[/bold cyan] CPU {sys_cpu_bar} {sys_cpu:5.1f}%  |  RAM {sys_ram_bar} {sys_ram.percent:5.1f}%\n"
        
        if self.server_process and self.server_process.returncode is None and self.server_psutil:
            try:
                mem_mb = self.server_psutil.memory_info().rss / (1024 * 1024)
                proc_cpu = self.server_psutil.cpu_percent() / psutil.cpu_count()
                ram_percent = min((mem_mb / (self.active_ram * 1024)) * 100, 100)
                
                proc_cpu_bar = self.make_bar(proc_cpu)
                proc_ram_bar = self.make_bar(ram_percent)
                
                stats += f"[bold lime]Server:[/bold lime] CPU {proc_cpu_bar} {proc_cpu:5.1f}%  |  RAM {proc_ram_bar} {mem_mb:4.0f} MB"
            except psutil.NoSuchProcess:
                stats += "[bold red]Server:[/bold red] Offline"
        else:
             stats += "[bold red]Server:[/bold red] Offline"

        self.query_one("#hardware-panel", Static).update(stats)

        if self.server_start_time and self.server_process and self.server_process.returncode is None:
            elapsed = int(time.time() - self.server_start_time)
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            uptime_str = "00:00:00"
            
        self.query_one("#uptime-text", Static).update(uptime_str)

    def update_players_panel(self) -> None:
        panel = self.query_one("#players-panel", Static)
        count = len(self.online_players)
        
        content = f"Players: {count}\n\n"
        for player in sorted(self.online_players):
            content += f" • {player}\n"
            
        panel.update(content)

    def reset_input(self) -> None:
        inp = self.query_one("#console-input", Input)
        inp.value = ""
        inp.placeholder = "> Type a command..."
        self.input_mode = "command"

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        console = self.query_one("#console-log", RichLog)

        if self.input_mode == "ram":
            if val.isdigit() and int(val) > 0:
                self.allocated_ram = int(val)
                console.write(f"[bold magenta][System] Config: RAM limit changed to {val}GB. Restart the server to apply.[/bold magenta]")
            elif val != "":
                console.write("[bold red][System] Invalid RAM value. Cancelled.[/bold red]")
            self.reset_input()

        elif self.input_mode == "args":
            self.jvm_args = val
            if val:
                console.write("[bold magenta][System] Config: JVM Args updated. Restart the server to apply.[/bold magenta]")
            else:
                console.write("[bold magenta][System] Config: JVM Args cleared. Restart the server to apply.[/bold magenta]")
            self.reset_input()

        elif self.input_mode == "command":
            if val:
                if self.server_process and self.server_process.returncode is None:
                    console.write(f"[bold white]> {val}[/bold white]")
                    self.server_process.stdin.write((val + "\n").encode('utf-8'))
                    await self.server_process.stdin.drain()
                else:
                    console.write("[bold red][System] Server is offline. Cannot send command.[/bold red]")
            self.reset_input()

    async def action_change_ram(self) -> None:
        self.input_mode = "ram"
        inp = self.query_one("#console-input", Input)
        inp.placeholder = "> Enter RAM in GB (e.g. 4) and press ENTER..."
        inp.focus()
        self.query_one("#console-log", RichLog).write("\n[bold yellow][System] How much RAM (in GB) do you want to allocate? Type in the box below and press ENTER (or leave empty to cancel).[/bold yellow]")

    async def action_change_args(self) -> None:
        self.input_mode = "args"
        inp = self.query_one("#console-input", Input)
        inp.placeholder = "> Enter JVM Args and press ENTER (or leave empty to clear)..."
        inp.focus()
        self.query_one("#console-log", RichLog).write("\n[bold yellow][System] Type the extra JVM Arguments below and press ENTER.[/bold yellow]")

    async def action_start_server(self) -> None:
        console = self.query_one("#console-log", RichLog)
        btn_start = self.query_one("#btn-start", Button)
        
        if self.server_process is not None and self.server_process.returncode is None:
            console.write("[bold yellow][System] Restarting server...[/bold yellow]")
            await self.action_stop_server()
            await self.server_process.wait()

        self.update_status("Starting...", "yellow")
        
        self.active_ram = self.allocated_ram
        
        cmd_list = ["java", f"-Xms{self.active_ram}G", f"-Xmx{self.active_ram}G"]
        if self.jvm_args:
            cmd_list.extend(shlex.split(self.jvm_args))
        cmd_list.extend(["-jar", "server.jar", "nogui"])
        
        cmd_str = " ".join(cmd_list)
        console.write(f"[bold cyan][System] Executing: {cmd_str}[/bold cyan]")

        self.online_players.clear()
        self.update_players_panel()

        self.server_process = await asyncio.create_subprocess_exec(
            *cmd_list,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        self.server_pid = self.server_process.pid
        self.server_start_time = time.time()
        
        try:
            self.server_psutil = psutil.Process(self.server_pid)
            self.server_psutil.cpu_percent() 
        except psutil.NoSuchProcess:
            self.server_psutil = None
        
        now = datetime.now().strftime("%H:%M:%S")
        self.query_one("#uptime-sub", Static).update(f"Started at: {now}")
        
        btn_start.label = "Restart (F1)"
        self.update_status("Running", "lime")
        asyncio.create_task(self.read_console(console))

    async def read_console(self, console: RichLog) -> None:
        while True:
            line = await self.server_process.stdout.readline()
            if not line:
                break
            
            text = line.decode('utf-8', errors='replace').rstrip()
            console.write(text)

            join_match = self.join_regex.search(text)
            if join_match:
                self.online_players.add(join_match.group(1))
                self.update_players_panel()
                self.update_status("Running", "lime")

            leave_match = self.leave_regex.search(text)
            if leave_match:
                player = leave_match.group(1)
                if player in self.online_players:
                    self.online_players.remove(player)
                self.update_players_panel()

            text_lower = text.lower()
            if "server empty for" in text_lower and "pausing" in text_lower:
                self.update_status("Paused", "yellow")
            elif "resuming server" in text_lower:
                self.update_status("Running", "lime")

        self.update_status("Offline", "red")
        self.server_pid = None
        self.server_psutil = None
        self.server_start_time = None
        self.query_one("#uptime-sub", Static).update("Started at: --:--")
        
        self.online_players.clear()
        self.update_players_panel()
        
        self.query_one("#btn-start", Button).label = "Start (F1)"
        console.write("[bold red][System] Server stopped.[/bold red]")

    async def action_stop_server(self) -> None:
        console = self.query_one("#console-log", RichLog)
        
        if self.server_process is None or self.server_process.returncode is not None:
            console.write("[bold yellow][System] Server is already offline.[/bold yellow]")
            return

        console.write("[bold cyan][System] Sending 'stop' command...[/bold cyan]")
        self.update_status("Stopping...", "yellow")
        
        self.server_process.stdin.write(b"stop\n")
        await self.server_process.stdin.drain()

    async def action_test_player(self) -> None:
        console = self.query_one("#console-log", RichLog)
        
        if "FantasmaBot" not in self.online_players:
            fake_log = "[12:00:00] [Server thread/INFO]: FantasmaBot joined the game"
        else:
            fake_log = "[12:00:00] [Server thread/INFO]: FantasmaBot left the game"
            
        console.write(f"[bold magenta][Test][/bold magenta] {fake_log}")
        
        join_match = self.join_regex.search(fake_log)
        if join_match:
            self.online_players.add(join_match.group(1))
            self.update_status("Running", "lime")
            
        leave_match = self.leave_regex.search(fake_log)
        if leave_match:
            player = leave_match.group(1)
            if player in self.online_players:
                self.online_players.remove(player)
                
        self.update_players_panel()

    def update_status(self, text: str, color: str) -> None:
        status = self.query_one("#status-text", Static)
        status.update(text)
        status.styles.color = color

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start":
            await self.action_start_server()
        elif event.button.id == "btn-stop":
            await self.action_stop_server()
        elif event.button.id == "btn-ram":
            await self.action_change_ram()
        elif event.button.id == "btn-args":
            await self.action_change_args()

if __name__ == "__main__":
    app = McManagerApp()
    app.run()
