# DaVinci Resolve Audio File Batch Renamer

**Author:** Longman  
**Date:** May 18, 2025  
**Version:** 1.0

## Overview

This Python script provides a command-line interface to interact with DaVinci Resolve Studio for organizing audio clips within ONE specific project timeline. It allows users to inspect audio clips, and perform batch renaming and path replacement operations, over ONE or MULTIPLE audio tracks. 

## Workflow

1. **Select Project, Timeline & Audio Track**
    - Select a project from the DaVinci Resolve project folder.
    - Select a timeline within the project.
    - Select one, multiple, or all audio tracks within the timeline.

2. **Inspect Audio Clips**
    - View a summary on the selected tracks, including:
    - `Each audio clip instance` used in the timeline in chronological order;
    - followed by the file path of the `unique media pool item`;
    - and general info such as timeline start timecode, frame start, duration.

3. **Batch Rename and Replace Audio Clips**
    - For each unique media pool item:
        -  Enter a new base filename. (Leave blank if no change shall be made.)

        - The script will then:
        - rename the file on disk `'{index}-{base filename}.{format}'` eg '01-Introduction.wav'
        - replace the media pool item with the new file path, and;
        - update the clip name in Resolve.
        - 

## Prerequisites


1.  **DaVinci Resolve Studio:** Version 17 or newer is recommended for optimal scripting API support. This script is `*not*` compatible with the free version of DaVinci Resolve, as external scripting is a Studio-only feature.

2.  **Python:** Python 3.7 or newer (mainly due to `rich` library features).

3.  **DaVinci Resolve Scripting API Module:**
    * The Python environment used to run the script must be able to locate the `DaVinciResolveScript.py` module provided by DaVinci Resolve.
    * The script includes an initial check for this module. If it's not found, ensure your `PYTHONPATH` environment variable includes the path to Resolve's scripting modules, or that you are using a Python environment where Resolve makes these modules available.
    * Typical default paths for the `Modules` folder:
        * **macOS:** `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules`
        * **Windows:** `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules`
        * **Linux:** `/opt/resolve/Developer/Scripting/Modules` (or sometimes `/home/resolve/Developer/Scripting/Modules`)

4.  **Python `rich` Library:**
    * If not already installed, run `'pip install rich'` in terminal.

## Crucial Setup: Enabling DaVinci Resolve's External Scripting

For any external script (including this script) to communicate with DaVinci Resolve, you **must** enable external scripting within Resolve's preferences:

1.  Open DaVinci Resolve Studio.
2.  Go to *"Preferences"*.
3.  Under *"System"* tab, select *"General"* from the menu on the left.
5.  Find the option *"External scripting using"*.
6.  Change from **"None" to "Local"**.
7.  Click "Save" to apply the changes.
8.  **Restart DaVinci Resolve Studio** for the changes to take effect.

## How to Run the Script

1.  Save the script as a `.py` file (e.g., `resolve_audio_util.py`) on your computer.
2.  Open your system's terminal or command prompt.
3.  Navigate to the directory where you saved the script:
    ```bash
    cd path/to/your/script/directory
    ```
4.  Run the script using Python:
    ```bash
    python resolve_audio_util.py
    ```
5.  Follow the on-screen prompts.

## Important Notes & Warnings

* **BACKUP YOUR WORK:** Before running any batch operations, especially those that modify files on disk (like the "Batch Rename and Relink" feature), **always create backups of your DaVinci Resolve project (.drp) and all associated media files.**
* **FILE SYSTEM MODIFICATIONS:** The "Batch Rename and Relink Audio Clips" feature will rename files on your computer's storage. Understand this before proceeding with that option.
* **TESTING RECOMMENDED:** It is highly advisable to first test this script on a duplicate or non-critical DaVinci Resolve project and media to familiarize yourself with its operations and ensure it behaves as expected in your environment.
* **PERMISSIONS:** Ensure the script has the necessary read/write permissions for the directories where your audio media is stored if you intend to use the renaming feature.

---

This script is provided as-is. The author is not responsible for any data loss or project corruption. Use with caution and at your own risk.