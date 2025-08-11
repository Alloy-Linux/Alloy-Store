import gi
import yaml
import gzip
import os
import sys

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, GLib

APPSTREAM_YAML_PATH = os.environ.get("NIXOS_APPSTREAM_DATA")

icons_base_dir = None
if APPSTREAM_YAML_PATH and os.path.isfile(APPSTREAM_YAML_PATH):
    share_app_info_dir = os.path.dirname(os.path.dirname(APPSTREAM_YAML_PATH))
    icons_base_dir = os.path.join(share_app_info_dir, "icons", "nixos", "64x64")
else:
    icons_base_dir = None

ICON_BASE_PATH = icons_base_dir


def load_apps_streamed(limit=None):
    try:
        if not os.path.isfile(APPSTREAM_YAML_PATH):
            raise FileNotFoundError(f"Appstream YAML not found: {APPSTREAM_YAML_PATH}")

        count = 0
        with gzip.open(APPSTREAM_YAML_PATH, 'rt', encoding='utf-8') as f:
            for doc in yaml.safe_load_all(f):
                if not isinstance(doc, dict):
                    continue
                if doc.get("Type") != "desktop-application":
                    continue

                name_data = doc.get('Name', 'Unknown')
                name = name_data.get('C') if isinstance(name_data, dict) else name_data

                summary_data = doc.get('Summary', 'No description')
                summary = summary_data.get('C') if isinstance(summary_data, dict) else summary_data

                icon_name = 'application-x-executable'
                icon_info = doc.get('Icon', {})
                if isinstance(icon_info, dict) and 'cached' in icon_info and len(icon_info['cached']) > 0:
                    cached_entry = icon_info['cached'][0]
                    if isinstance(cached_entry, dict):
                        icon_name = cached_entry.get('name', icon_name)
                elif isinstance(icon_info, str):
                    icon_name = icon_info

                yield {
                    'name': name or 'Unknown',
                    'summary': summary or 'No description',
                    'icon': icon_name,
                }

                count += 1
                if limit and count >= limit:
                    break

    except Exception as e:
        print(f"Error streaming appstream data: {e}", file=sys.stderr)
        yield {'name': 'Error', 'summary': str(e), 'icon': 'dialog-error'}


def create_landing(container):
    grid = Gtk.Grid()
    grid.set_row_spacing(24)
    grid.set_column_spacing(24)
    grid.set_margin_start(24)
    grid.set_margin_end(24)
    grid.set_margin_top(24)
    grid.set_margin_bottom(24)
    grid.set_column_homogeneous(True)
    container.append(grid)

    create_landing.app_count = 0
    max_apps = 6

    def add_app_tile(app):
        i = create_landing.app_count
        if i >= max_apps:
            return False

        create_landing.app_count += 1

        display_name = app.get('name', 'Unknown')
        description = app.get('summary', 'No description')
        icon_name = app.get('icon', 'application-x-executable')

        button = Gtk.Button()
        button.set_hexpand(True)
        button.set_vexpand(False)
        button.set_margin_top(6)
        button.set_margin_bottom(6)
        button.set_margin_start(6)
        button.set_margin_end(6)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_hexpand(True)

        icon_path = None
        if ICON_BASE_PATH:
            candidate_name = icon_name
            if not icon_name.lower().endswith('.png'):
                candidate_name = icon_name + ".png"
            candidate = os.path.join(ICON_BASE_PATH, candidate_name)
            if os.path.isfile(candidate):
                icon_path = candidate
            else:
                print(f"[DEBUG] Icon file not found: {candidate}", file=sys.stderr)

        if icon_path:
            icon = Gtk.Image.new_from_file(icon_path)
        else:
            icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_valign(Gtk.Align.CENTER)
        icon.set_pixel_size(64)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_hexpand(True)

        title_label = Gtk.Label(label=display_name)
        title_label.set_xalign(0)
        title_label.add_css_class("title-3")
        title_label.set_hexpand(True)

        description_label = Gtk.Label(label=description)
        description_label.set_xalign(0)
        description_label.add_css_class("dim-label")
        description_label.set_wrap(True)
        description_label.set_max_width_chars(30)
        description_label.set_hexpand(True)

        vbox.append(title_label)
        vbox.append(description_label)

        hbox.append(icon)
        hbox.append(vbox)

        button.set_child(hbox)

        row = i // 3
        col = i % 3
        grid.attach(button, col, row, 1, 1)

        return False

    import concurrent.futures

    def load_and_add_apps():
        count = 0
        for app in load_apps_streamed():
            if count >= max_apps:
                break
            GLib.idle_add(add_app_tile, app)
            count += 1

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    executor.submit(load_and_add_apps)
