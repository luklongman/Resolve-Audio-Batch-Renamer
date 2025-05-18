import sys
import os
import math

# --- Try to import DaVinci Resolve Scripting API ---
try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    # Rich will be imported later, so use basic print for this initial crucial error
    print("ERROR: The DaVinciResolveScript module was not found.")
    print("Please ensure DaVinci Resolve Studio is running and the scripting API is correctly configured.")
    print("This includes enabling 'External scripting using' to 'Local' in Resolve's Preferences > System > General,")
    print("and ensuring PYTHONPATH includes the DaVinci Resolve Scripting Modules path (e.g., $RESOLVE_SCRIPT_API/Modules on Linux/macOS or specific paths on Windows).")
    sys.exit(1)

# --- Import Rich Library Components ---
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.rule import Rule
    from rich.padding import Padding
    from rich.style import Style
    from rich.markdown import Markdown
except ImportError:
    print("ERROR: The 'rich' library is not installed. Please install it by running: pip install rich")
    sys.exit(1)

# --- Initialize Rich Console ---
console = Console(highlight=False)

# --- Define some styles ---
error_style = Style(color="red", bold=True)
warning_style = Style(color="yellow")
info_style = Style(color="blue")
success_style = Style(color="green")
header_style = Style(color="cyan", bold=True, underline=True)
prompt_style = Style(color="magenta")
table_header_style = Style(color="blue", bold=True)
item_style = Style(color="white")
detail_style = Style(color="white", dim=True)

# --- Helper Functions ---
def get_resolve():
    """Connects to DaVinci Resolve"""
    try:
        resolve = dvr_script.scriptapp("Resolve")
        if resolve is None:
            console.print("ERROR: Failed to connect to DaVinci Resolve. Is it running and configured for local scripting?", style=error_style)
            sys.exit(1)
        return resolve
    except Exception as e:
        console.print(f"ERROR: An exception occurred while connecting to Resolve: {e}", style=error_style)
        sys.exit(1)

def frames_to_timecode(frames, frame_rate, drop_frame=False):
    """Converts frame count to HH:MM:SS:FF timecode string."""
    if frame_rate <= 0:
        return "00:00:00:00"
    fps_int = int(round(frame_rate))
    total_seconds = frames / frame_rate
    frames_remainder = int(frames % fps_int)
    ss = int(total_seconds % 60)
    mm = int((total_seconds / 60) % 60)
    hh = int(total_seconds / 3600)
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{frames_remainder:02d}"

def select_from_list_adv(item_list, item_type_name, allow_zero_for_all=False, mandatory=True):
    """
    Advanced prompt for user to select an item from a numbered list using Rich.
    """
    if not item_list and not allow_zero_for_all:
        console.print(f"No {item_type_name}s found to select.", style=warning_style)
        return None
    if not item_list and allow_zero_for_all:
        console.print(f"No {item_type_name}s found, but '0' might be an option if applicable elsewhere.", style=info_style)

    title_text = Text(f"Available {item_type_name.capitalize()}s", style=header_style)
    console.print(Padding(title_text, (1, 0, 0, 0)))

    table = Table(show_header=True, header_style=table_header_style, show_lines=True, border_style="dim white")
    table.add_column("#", style="dim cyan", width=5, justify="right")
    table.add_column(f"{item_type_name.capitalize()} Name", style=item_style, min_width=20, overflow="fold")
    table.add_column("Details", style=detail_style, min_width=30, overflow="fold")


    for i, item_data in enumerate(item_list):
        display_name = ""
        extra_info_str = ""

        if isinstance(item_data, str):
            display_name = item_data
        elif hasattr(item_data, 'GetName') and callable(getattr(item_data, 'GetName')): # Timeline object
            display_name = item_data.GetName()
            if item_type_name == "timeline":
                try:
                    settings = item_data.GetSettings()
                    frame_rate = float(settings.get("timelineFrameRate", 0))
                    start_frame = int(settings.get("timelineStartFrame", 0))
                    end_frame = int(settings.get("timelineEndFrame", 0))
                    duration_frames = end_frame - start_frame
                    duration_str = frames_to_timecode(duration_frames, frame_rate)
                    start_tc_str = frames_to_timecode(start_frame, frame_rate)
                    video_tracks = item_data.GetTrackCount("video")
                    audio_tracks = item_data.GetTrackCount("audio")
                    extra_info_str = (f"Start: {start_tc_str}, Duration: {duration_str}, "
                                      f"FR: {frame_rate:.2f}fps, V: {video_tracks}, A: {audio_tracks}")
                except Exception:
                    extra_info_str = "Info: N/A"
        elif isinstance(item_data, dict) and 'display_name' in item_data:
            display_name = item_data['display_name']
            if 'info' in item_data:
                extra_info_str = str(item_data['info'])

        table.add_row(str(i + 1), display_name, extra_info_str)

    console.print(table)

    prompt_display_text = f"Choose a {item_type_name} by number"
    _prompt_suffix = ": "
    if allow_zero_for_all:
        prompt_display_text += " (0 for All)"
    if not mandatory and not allow_zero_for_all:
         _prompt_suffix = " (or press Enter to skip): "
    prompt_display_text += _prompt_suffix


    while True:
        try:
            console.print(f"\n{prompt_display_text}", style=prompt_style, end="")
            choice_str = input()

            if not choice_str and not mandatory and not allow_zero_for_all:
                console.print("Selection skipped.", style=info_style)
                return None

            choice_num = int(choice_str)

            if allow_zero_for_all and choice_num == 0:
                return "ALL_ITEMS_SELECTED"
            if 1 <= choice_num <= len(item_list):
                return item_list[choice_num - 1]
            else:
                invalid_choice_msg = "Invalid choice. Please enter a number from the list"
                if allow_zero_for_all:
                    invalid_choice_msg += " (or 0 if applicable)"
                invalid_choice_msg += "."
                console.print(invalid_choice_msg, style=warning_style)
        except ValueError:
            console.print("Invalid input. Please enter a number.", style=warning_style)
        except Exception as e:
            console.print(f"An error occurred during selection: {e}", style=error_style)
            return None

# --- Main Application Functions ---

def select_project(project_manager):
    console.print(Rule("[bold cyan]Select Project[/bold cyan]"))
    with console.status("[yellow]Fetching projects...", spinner="dots"):
        project_names = project_manager.GetProjectListInCurrentFolder()

    if not project_names:
        console.print("No projects found in the current folder.", style=warning_style)
        return None

    project_names.sort(key=lambda s: s.lower())

    selected_project_name = select_from_list_adv(project_names, "project", mandatory=True)
    if not selected_project_name:
        return None

    console.print(f"Loading project: [bold magenta]{selected_project_name}[/]...", style=info_style)
    project = project_manager.LoadProject(selected_project_name)
    if not project:
        console.print(f"ERROR: Failed to load project '{selected_project_name}'.", style=error_style)
        project = project_manager.GetCurrentProject()
        if not project or project.GetName() != selected_project_name:
            console.print("Could not access the selected project.", style=error_style)
            return None
        else:
            console.print(f"Continuing with already open project: [bold magenta]{project.GetName()}[/]", style=info_style)
    else:
        console.print(f"Successfully loaded project: [bold green]{project.GetName()}[/]", style=success_style)
    return project

def select_timeline(project):
    console.print(Rule(f"[bold cyan]Select Timeline for Project: {project.GetName()}[/bold cyan]"))
    with console.status("[yellow]Fetching timelines...", spinner="dots"):
        timeline_count = project.GetTimelineCount()
        timelines_objs = []
        if timeline_count > 0:
            for i in range(1, timeline_count + 1):
                timeline = project.GetTimelineByIndex(i)
                if timeline:
                    timelines_objs.append(timeline)
    if not timelines_objs:
        console.print("No timelines found in this project.", style=warning_style)
        return None

    timelines_objs.sort(key=lambda t: t.GetName().lower())

    selected_timeline_obj = select_from_list_adv(timelines_objs, "timeline", mandatory=True)
    if not selected_timeline_obj:
        return None

    if not project.SetCurrentTimeline(selected_timeline_obj):
        console.print(f"ERROR: Could not set '[bold magenta]{selected_timeline_obj.GetName()}[/]' as current timeline.", style=error_style)
        current_timeline_check = project.GetCurrentTimeline()
        if not current_timeline_check or current_timeline_check.GetName() != selected_timeline_obj.GetName():
            console.print("Failed to switch to the selected timeline.", style=error_style)
            return None
        else:
            console.print(f"Continuing with timeline: [bold magenta]{current_timeline_check.GetName()}[/]", style=info_style)
            selected_timeline_obj = current_timeline_check
    else:
        console.print(f"Successfully set current timeline to: [bold green]{selected_timeline_obj.GetName()}[/]", style=success_style)
    return selected_timeline_obj

def select_audio_tracks(timeline):
    console.print(Rule(f"[bold cyan]Select Audio Track(s) for Timeline: {timeline.GetName()}[/bold cyan]"))
    with console.status("[yellow]Fetching audio tracks...", spinner="dots"):
        num_audio_tracks = timeline.GetTrackCount("audio")
        audio_tracks_data = []
        if num_audio_tracks > 0:
            for i in range(1, int(num_audio_tracks) + 1):
                track_name = timeline.GetTrackName("audio", i)
                if not track_name:
                    track_name = f"Audio Track {i}"
                clips_on_track = timeline.GetItemListInTrack("audio", i)
                num_clips = len(clips_on_track) if clips_on_track else 0
                track_info_str = f"Clips: {num_clips}"
                audio_tracks_data.append({
                    "display_name": track_name,
                    "info": track_info_str,
                    "type": "audio",
                    "index": i,
                    "timeline_obj": timeline
                })

    if not audio_tracks_data:
        console.print(f"No audio tracks found on timeline '[bold magenta]{timeline.GetName()}[/]'.", style=warning_style)
        return None

    selected_track_data = select_from_list_adv(audio_tracks_data, "audio track", allow_zero_for_all=True, mandatory=True)

    if selected_track_data == "ALL_ITEMS_SELECTED":
        if not audio_tracks_data:
            console.print("No audio tracks to select as 'All'.", style=warning_style)
            return []
        console.print("All audio tracks selected.", style=info_style)
        return audio_tracks_data
    elif selected_track_data:
        console.print(f"Selected audio track: [bold magenta]{selected_track_data['display_name']}[/]", style=info_style)
        return [selected_track_data]
    else:
        return None


def inspect_audio_clips(timeline, selected_tracks_data):
    console.print(Rule("[bold cyan]Inspect Audio Clips[/bold cyan]"))
    if not selected_tracks_data:
        console.print("No audio tracks selected for inspection.", style=warning_style)
        return

    frame_rate = float(timeline.GetSetting("timelineFrameRate") or 24.0)
    clip_index_overall = 1

    for track_data in selected_tracks_data:
        track_display_name = track_data['display_name']
        track_api_index = track_data['index']
        
        track_title = Text(f"Track: {track_display_name} (API Index: {track_api_index})", style="bold yellow")
        console.print(Rule(track_title, style="blue"))


        clips_in_track = timeline.GetItemListInTrack("audio", track_api_index)
        if not clips_in_track:
            console.print("  No clips found on this track.", style=info_style)
            continue

        table = Table(show_header=True, header_style=table_header_style, show_lines=True, border_style="dim white")
        table.add_column("#", style="dim cyan", width=5, justify="right")
        table.add_column("Clip Name", style=item_style, min_width=20, overflow="fold")
        table.add_column("Filepath", style=detail_style, min_width=30, overflow="fold")
        table.add_column("Start TC", style="magenta", width=12)
        table.add_column("Duration TC", style="magenta", width=12)
        table.add_column("Start (fr)", style="dim magenta", width=10, justify="right")
        table.add_column("Dur (fr)", style="dim magenta", width=10, justify="right")


        for item in clips_in_track:
            item_name = item.GetName() or "N/A"
            start_frames = item.GetStart()
            duration_frames = item.GetDuration()
            start_tc = frames_to_timecode(start_frames, frame_rate)
            duration_tc = frames_to_timecode(duration_frames, frame_rate)
            media_pool_item = item.GetMediaPoolItem()
            filepath = "N/A (Not linked or issue)"
            if media_pool_item:
                try:
                    fp_prop = media_pool_item.GetClipProperty('File Path')
                    if isinstance(fp_prop, str) and fp_prop: filepath = fp_prop
                    elif isinstance(fp_prop, dict) and 'File Path' in fp_prop: filepath = fp_prop['File Path']
                    else:
                        fn_prop = media_pool_item.GetClipProperty('File Name')
                        mp_prop = media_pool_item.GetClipProperty('Media Folder')
                        if fn_prop and mp_prop: filepath = os.path.join(mp_prop, fn_prop)
                        elif fn_prop: filepath = f"[Filename only: {fn_prop}]"
                except Exception:
                    filepath = "Error fetching path"
            
            table.add_row(
                str(clip_index_overall),
                item_name,
                Text(filepath, overflow="fold"),
                start_tc,
                duration_tc,
                str(start_frames),
                str(duration_frames)
            )
            clip_index_overall += 1
        console.print(table)
    console.print(Rule("[bold cyan]Inspection Finished[/bold cyan]"))

def batch_rename_relink_audio_clips(project, timeline, selected_tracks_data):
    console.print(Rule("[bold red]Batch Rename and Relink Audio Clips[/bold red]"))
    if not selected_tracks_data:
        console.print("No audio tracks selected for renaming/relinking.", style=warning_style)
        return

    console.print(Panel(
        Text.assemble(
            ("IMPORTANT REMINDERS:\n", "bold yellow"),
            ("- This operation will RENAME files on your DISK.\n", "yellow"),
            ("- It will then attempt to RELINK these clips within DaVinci Resolve.\n", "yellow"),
            ("- Ensure you have BACKUPS of your media and project before proceeding.\n", "bold red"),
            ("- If a new filename is left empty, the original base filename will be used for numbering.\n", "yellow"),
            ("- The renaming format will be '{index}-{new_or_original_filename}.{extension}'.", "yellow")
        ),
        title="[bold white on red] WARNING [/]",
        border_style="red",
        expand=False
    ))

    if not Confirm.ask("Are you sure you want to proceed with Batch Rename and Relink?", default=False, console=console):
        console.print("Operation cancelled by user.", style=info_style)
        return

    unique_media_pool_items_map = {}
    all_timeline_items = []
    for track_data in selected_tracks_data:
        track_api_index = track_data['index']
        clips_in_track = timeline.GetItemListInTrack("audio", track_api_index)
        if clips_in_track:
            all_timeline_items.extend(clips_in_track)

    if not all_timeline_items:
        console.print("No audio clips found in the selected track(s) to process.", style=warning_style)
        return

    initial_mpi_data = []
    temp_mpi_to_timeline_names = {}

    with console.status("[yellow]Collecting unique media pool items...", spinner="dots"):
        for ti in all_timeline_items:
            mpi = ti.GetMediaPoolItem()
            if mpi:
                mpi_props = mpi.GetClipProperty()
                if isinstance(mpi_props, dict):
                    current_path = mpi_props.get('File Path', '')
                    if current_path:
                        mpi_obj_id = id(mpi)
                        if mpi_obj_id not in temp_mpi_to_timeline_names:
                            temp_mpi_to_timeline_names[mpi_obj_id] = []
                        ti_name = ti.GetName() or "Unnamed Timeline Clip"
                        if ti_name not in temp_mpi_to_timeline_names[mpi_obj_id]:
                             temp_mpi_to_timeline_names[mpi_obj_id].append(ti_name)

                        if current_path not in unique_media_pool_items_map:
                            unique_media_pool_items_map[current_path] = mpi
                            initial_mpi_data.append({
                                "mpi": mpi,
                                "original_filepath_at_start": current_path,
                                "timeline_item_names": []
                            })
        for data_entry in initial_mpi_data:
            mpi_obj_id_for_lookup = id(data_entry["mpi"])
            if mpi_obj_id_for_lookup in temp_mpi_to_timeline_names:
                data_entry["timeline_item_names"] = temp_mpi_to_timeline_names[mpi_obj_id_for_lookup]

    if not initial_mpi_data:
        console.print("No valid Media Pool items with file paths could be collected from the timeline clips.", style=warning_style)
        return

    num_total_unique_mpi = len(initial_mpi_data)
    num_digits_for_index = len(str(num_total_unique_mpi))
    
    console.print(f"\nFound {num_total_unique_mpi} unique source media file(s) to process.", style=info_style)
    success_count = 0
    fail_count = 0
    user_quit_batch = False

    for i, mpi_entry in enumerate(initial_mpi_data):
        if user_quit_batch:
            break

        media_pool_item = mpi_entry["mpi"]
        current_mpi_props = media_pool_item.GetClipProperty()
        if not isinstance(current_mpi_props, dict) or not current_mpi_props.get('File Path'):
            console.print(f"  [warning]WARNING:[/] Could not get current file path for Media Pool Item (originally [magenta]{mpi_entry['original_filepath_at_start']}[/]). Skipping.", style=warning_style)
            fail_count +=1
            continue
        
        original_filepath_for_this_iteration = current_mpi_props['File Path']
        current_index_str = str(i + 1).zfill(num_digits_for_index)
        original_clip_name_in_pool = current_mpi_props.get('Clip Name', 'Unknown MPI Clip')
        timeline_item_names_str = ", ".join(mpi_entry["timeline_item_names"]) if mpi_entry["timeline_item_names"] else "N/A"

        console.print(Rule(f"Processing unique source {i+1}/{num_total_unique_mpi}", style="dim yellow"))
        console.print(f"  Media Pool Clip Name (Current): '[bold cyan]{original_clip_name_in_pool}[/]'")
        console.print(f"  Current File Path: '[magenta]{original_filepath_for_this_iteration}[/]'")
        console.print(f"  Used by Timeline Clip(s): [dim white]{timeline_item_names_str}[/]")

        if not os.path.exists(original_filepath_for_this_iteration):
            console.print(f"  [error]ERROR:[/] Source file does not exist on disk: [magenta]{original_filepath_for_this_iteration}[/]. Skipping.", style=error_style)
            fail_count += 1
            continue

        original_dir = os.path.dirname(original_filepath_for_this_iteration)
        original_basename_full = os.path.basename(original_filepath_for_this_iteration)
        original_basename_no_ext, original_ext = os.path.splitext(original_basename_full)

        already_script_named = False
        current_base_for_prompt = original_basename_no_ext
        if len(original_basename_no_ext) > num_digits_for_index and original_basename_no_ext[num_digits_for_index] == '-':
            try:
                int(original_basename_no_ext[:num_digits_for_index])
                already_script_named = True
                current_base_for_prompt = original_basename_no_ext[num_digits_for_index+1:] # Show current base without index
                console.print(f"  [info]INFO:[/] Filename '[cyan]{original_basename_no_ext}[/]' appears to be already indexed. Current base: '[cyan]{current_base_for_prompt}[/]'", style=info_style)
            except ValueError:
                pass # Not an indexed name matching the pattern

        prompt_message_text = Text(f"Enter new target base for '[u]{current_base_for_prompt}[/u]'")
        prompt_message_text.append(Text.assemble(("\n(empty to keep current base, 'Q' to end batch): "), style=prompt_style))
        
        new_base_filename_user = Prompt.ask(prompt_message_text, default="", console=console).strip()

        if new_base_filename_user.upper() == 'Q':
            console.print("  User chose to end batch processing.", style=info_style)
            user_quit_batch = True
            break 

        final_base_filename_to_use = new_base_filename_user if new_base_filename_user else current_base_for_prompt
        
        new_disk_filename_base = f"{current_index_str}-{final_base_filename_to_use}"
        new_filename_on_disk = f"{new_disk_filename_base}{original_ext}"
        new_filepath_on_disk = os.path.join(original_dir, new_filename_on_disk)

        if original_filepath_for_this_iteration == new_filepath_on_disk:
            console.print(f"  [info]INFO:[/] Generated new path is identical to current. No rename needed for this file.", style=info_style)
            if original_clip_name_in_pool != new_disk_filename_base:
                console.print(f"  Attempting to update Media Pool Clip Name to: [cyan]{new_disk_filename_base}[/]")
                if media_pool_item.SetClipProperty("Clip Name", new_disk_filename_base):
                    console.print(f"    Media Pool Clip Name updated to '[bold green]{new_disk_filename_base}[/]'.", style=success_style)
                else:
                    console.print(f"    [warning]Failed[/] to update Media Pool Clip Name for '[cyan]{original_clip_name_in_pool}[/]'.", style=warning_style)
            success_count +=1
            continue

        try:
            console.print(f"  Renaming on disk: '[magenta]{original_filepath_for_this_iteration}[/]' -> '[bold green]{new_filepath_on_disk}[/]'")
            os.rename(original_filepath_for_this_iteration, new_filepath_on_disk)
            console.print("  Disk rename successful.", style=success_style)
        except OSError as e:
            console.print(f"  [error]ERROR:[/] Failed to rename file on disk: {e}. Skipping Resolve relink for this clip.", style=error_style)
            fail_count += 1
            continue 
        except Exception as e:
            console.print(f"  [error]ERROR:[/] An unexpected error occurred during disk rename: {e}. Skipping.", style=error_style)
            fail_count += 1
            continue

        console.print(f"  Attempting to relink Media Pool Item in Resolve to: [bold green]{new_filepath_on_disk}[/]")
        relink_success = media_pool_item.ReplaceClip(new_filepath_on_disk)

        if relink_success:
            console.print("  Resolve Media Pool Item relink (ReplaceClip) successful.", style=success_style)
            console.print(f"  Updating Media Pool Clip Name to: [cyan]{new_disk_filename_base}[/]")
            if media_pool_item.SetClipProperty("Clip Name", new_disk_filename_base):
                console.print(f"    Media Pool Clip Name updated to '[bold green]{new_disk_filename_base}[/]'.", style=success_style)
            else:
                console.print(f"    [warning]WARNING:[/] Failed to update Media Pool Clip Name for '[cyan]{original_clip_name_in_pool}[/]' after relink.", style=warning_style)
            success_count += 1
        else:
            console.print("  [error]ERROR:[/] Resolve Media Pool Item relink (ReplaceClip) failed.", style=error_style)
            console.print("    Troubleshooting steps:", style=warning_style)
            console.print("    - Ensure the new file path is accessible by Resolve.", style=warning_style)
            console.print(f"    - Manually try to 'Replace Selected Clip...' for '[cyan]{original_clip_name_in_pool}[/]' (original file: [magenta]{original_basename_full}[/]) in Resolve's Media Pool, pointing it to '[bold green]{new_filename_on_disk}[/]'.", style=warning_style)
            console.print(f"    - The file on disk [bold red]HAS BEEN RENAMED[/] to '[bold green]{new_filename_on_disk}[/]'. You may need to manually relink or revert renames if this continues to fail.", style=warning_style)
            fail_count += 1

    console.print(Rule("[bold cyan]Batch Processing Summary[/bold cyan]"))
    if user_quit_batch:
        console.print("\nBatch processing was ended prematurely by the user.", style=info_style)
    console.print(f"Successfully processed and relinked: [bold green]{success_count}[/] unique source file(s)", style=success_style)
    console.print(f"Failed to process: [bold red]{fail_count}[/] unique source file(s)", style=error_style if fail_count > 0 else info_style)
    console.print(Rule("[bold red]Batch Rename and Relink Audio Clips Finished[/bold red]"))


def main_action_loop(project, timeline, initial_selected_tracks_data):
    current_selected_tracks = initial_selected_tracks_data

    while True:
        if not current_selected_tracks:
            console.print("\nNo audio tracks are currently selected or available to operate on.", style=warning_style)
            reselect_choice = Prompt.ask("Would you like to (R)eselect audio tracks or (E)xit to timeline selection?", choices=["r", "e"], default="e", console=console).lower()
            if reselect_choice == 'r':
                current_selected_tracks = select_audio_tracks(timeline)
                if current_selected_tracks is None: 
                    current_selected_tracks = [] 
            else:
                return
        else:
            track_names_display_list = [t['display_name'] for t in current_selected_tracks if isinstance(t, dict) and 'display_name' in t]
            
            if not track_names_display_list and current_selected_tracks:
                track_names_display = f"{len(current_selected_tracks)} item(s) selected (type unknown)"
            elif len(track_names_display_list) > 3:
                track_names_display = f"{len(track_names_display_list)} audio track(s) selected"
            elif track_names_display_list:
                 track_names_display = ", ".join(track_names_display_list)
            else:
                 track_names_display = "None"


            console.print(Rule(Text.assemble(
                "Actions for Timeline: ",
                (f"{timeline.GetName()}", "bold magenta"),
                " | Selected Audio Track(s): ",
                (f"{track_names_display}", "bold yellow")
            ), style="cyan"))

            menu_table = Table.grid(padding=(0,1))
            menu_table.add_column(style="dim cyan", width=3)
            menu_table.add_column()
            menu_table.add_row("1.", "Inspect Audio Clips")
            menu_table.add_row("2.", "Batch Rename and Relink Audio Clips")
            menu_table.add_row("3.", "Select Different Audio Track(s)")
            menu_table.add_row("4.", "Go Back to Timeline Selection")
            menu_table.add_row("5.", "Exit Script")
            console.print(Padding(Panel(menu_table, title="[bold]Main Menu[/]", border_style="green", expand=False), (1,0)))

            choice = Prompt.ask("Enter your choice", choices=["1", "2", "3", "4", "5"], console=console)

            if choice == '1':
                inspect_audio_clips(timeline, current_selected_tracks)
            elif choice == '2':
                batch_rename_relink_audio_clips(project, timeline, current_selected_tracks)
            elif choice == '3':
                new_selection = select_audio_tracks(timeline)
                current_selected_tracks = new_selection if new_selection is not None else []
            elif choice == '4':
                console.print("Returning to timeline selection...", style=info_style)
                return
            elif choice == '5':
                console.print("Exiting script.", style=info_style)
                sys.exit(0)


def display_readme_and_confirm():
    """Displays the README.md content from an external file and asks for user confirmation."""
    readme_filename = "README.md"
    # Construct path relative to the script file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    readme_path = os.path.join(script_dir, readme_filename)

    readme_content = ""
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
    except FileNotFoundError:
        console.print(f"Error: {readme_filename} not found in the script directory ({script_dir}).", style=error_style)
        console.print("Please ensure the README.md file is present to view instructions.", style=warning_style)
        # Optionally, ask if user wants to continue without README or just exit
        if not Confirm.ask("Continue without viewing instructions?", default=False, console=console):
            sys.exit(1)
        return # Allow continuation if user explicitly agrees
    except Exception as e:
        console.print(f"Error reading {readme_filename}: {e}", style=error_style)
        if not Confirm.ask("Continue without viewing instructions?", default=False, console=console):
            sys.exit(1)
        return

    if readme_content:
        console.print(Rule("[bold cyan]Script Information & Instructions[/bold cyan]"))
        md = Markdown(readme_content)
        console.print(md)
        console.print(Rule(style="cyan"))
    
    if not Confirm.ask("Do you understand the instructions and wish to proceed with the script?", default=True, console=console):
        console.print("Script execution cancelled by the user.", style=info_style)
        sys.exit(0)
    console.clear()


def main():
    display_readme_and_confirm()

    console.print(Panel(
        Text.assemble(
            ("DaVinci Resolve Script Initializing...\n", "bold white on blue"),
            (f"Script Path: {__file__}\n", "dim white"),
            (f"Current Working Directory: {os.getcwd()}", "dim white")
        ),
        title="[b]Script Info[/b]",
        border_style="blue",
        expand=False
    ))
    
    resolve = get_resolve()
    project_manager = resolve.GetProjectManager()
    if not project_manager:
        console.print("ERROR: Could not get Project Manager.", style=error_style)
        sys.exit(1)

    while True: 
        project = select_project(project_manager)
        if not project:
            console.print("No project loaded or selected.", style=info_style)
            if Confirm.ask("Do you want to try selecting another project or exit?", default=True, console=console):
                continue
            else:
                console.print("Exiting script.", style=info_style)
                sys.exit(0)


        while True: 
            timeline = select_timeline(project)
            if not timeline:
                console.print("No timeline selected for the current project.", style=warning_style)
                if Confirm.ask(f"Try selecting another timeline in '{project.GetName()}'?", default=True, console=console):
                    continue 
                else: 
                    break 

            initial_selected_tracks = select_audio_tracks(timeline)
            
            if initial_selected_tracks is None:
                initial_selected_tracks = []

            main_action_loop(project, timeline, initial_selected_tracks)

            post_action_choice = Prompt.ask(
                Text.assemble(("Work with another (T)imeline in this project, change (P)roject, or (E)xit? "), (f"(Current Project: {project.GetName()})", "dim white")),
                choices=["t", "p", "e"], default="t", console=console
            ).lower()

            if post_action_choice == 'p':
                break 
            elif post_action_choice == 'e':
                console.print("Exiting script.", style=info_style)
                sys.exit(0)

        final_choice_prompt = Text.assemble(("Select another (P)roject or (E)xit script? "), style=prompt_style)
        final_choice = Prompt.ask(final_choice_prompt, choices=["p", "e"], default="p", console=console).lower()
        if final_choice != 'p':
            console.print("Exiting script.", style=info_style)
            break

if __name__ == "__main__":
    main()