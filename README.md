# Minecraft Server Manager TUI

A lightweight, beautiful, and highly functional Terminal User Interface (TUI) for managing Minecraft servers. Built with Python and the [Textual](https://textual.textualize.io/) framework, inspired by system monitors like `htop` and `gotop`.

<img width="1297" height="689" alt="Captura de tela 2026-03-02 014741" src="https://github.com/user-attachments/assets/1272cc69-bbee-4b8c-b4e0-100754c40a1c" />

## ✨ Features

* **Live Hardware Monitoring:** Real-time graphs for System and Server-specific CPU/RAM usage.
* **Interactive Console:** View server logs in real-time and send commands directly from the integrated input bar.
* **Player Tracking:** Automatically detects players joining and leaving by reading the server logs (No RCON required).
* **Smart Status & Uptime:** Tracks server uptime and automatically detects when the server goes into a "Paused" state (e.g., PaperMC/Purpur empty server pause feature).
* **Dynamic Configuration:** Change allocated RAM and add extra JVM Arguments directly from the console interface.
* **Mouse & Keyboard Support:** Fully clickable UI with convenient shortcut bindings (F1, F2).

## 🚀 Installation

1. Clone this repository to your machine:
```
git clone https://github.com/laurorual/Minecraft-Server-Manager-TUI.git
cd Minecraft-Server-Manager-TUI
```

2. Install the required Python dependencies:
```
pip install -r requirements.txt
```
Important: Place your Minecraft server files in the same folder! Server file must be named `server.jar`.

## 🎮 Usage

Run the application using Python:
```
python manager.py
```

## ⌨️ Key Bindings

    F1 - Start / Restart the server

    F2 - Stop the server safely (sends the stop command)

    Q - Quit the application

## ⚙️ Configuration Commands

While the app is running, you can use the interactive console input to configure the server:

    Click Change RAM limit to set the allocated memory (in GB).

    Click JVM Arguments to add custom Java flags (e.g., Aikar's flags for better performance).

    Type any standard Minecraft command (e.g., say Hello, time set day) and press ENTER to execute it.

## 📝 License

This project is open-source and available under the MIT License.
