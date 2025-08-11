import gi
import yaml
import gzip
import os
import sys
import sqlite3
import json

from gi.repository import Gtk, GLib

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

APPSTREAM_YAML_PATH = os.environ.get("NIXOS_APPSTREAM_DATA")
DB_PATH = os.path.expanduser('~/.cache/alloy_store_apps.db')

icons_base_dir = None
if APPSTREAM_YAML_PATH and os.path.isfile(APPSTREAM_YAML_PATH):
    share_app_info_dir = os.path.dirname(os.path.dirname(APPSTREAM_YAML_PATH))
    icons_base_dir = os.path.join(share_app_info_dir, "icons", "nixos", "64x64")
else:
    icons_base_dir = None

ICON_BASE_PATH = icons_base_dir


def create_db(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS apps (
            id TEXT PRIMARY KEY,
            name TEXT,
            summary TEXT,
            description TEXT,
            icon TEXT,
            developer TEXT,
            license TEXT,
            homepage TEXT,
            screenshots TEXT
        )
    ''')
    conn.commit()


def populate_db(conn):
    if not APPSTREAM_YAML_PATH or not os.path.isfile(APPSTREAM_YAML_PATH):
        print(f"Appstream YAML not found: {APPSTREAM_YAML_PATH}", file=sys.stderr)
        return

    c = conn.cursor()

    with gzip.open(APPSTREAM_YAML_PATH, 'rt', encoding='utf-8') as f:
        for doc in yaml.safe_load_all(f):
            if not isinstance(doc, dict):
                continue
            if doc.get("Type") != "desktop-application":
                continue

            app_id = doc.get("ID")
            if not app_id:
                continue

            name_data = doc.get('Name', 'Unknown')
            name = name_data.get('C') if isinstance(name_data, dict) else name_data

            summary_data = doc.get('Summary', 'No summary')
            summary = summary_data.get('C') if isinstance(summary_data, dict) else summary_data

            description_data = doc.get('Description', 'No description')
            description = description_data.get('C') if isinstance(description_data, dict) else description_data

            icon_name = 'application-x-executable'
            icon_info = doc.get('Icon', {})
            if isinstance(icon_info, dict) and 'cached' in icon_info and len(icon_info['cached']) > 0:
                cached_entry = icon_info['cached'][0]
                if isinstance(cached_entry, dict):
                    icon_name = cached_entry.get('name', icon_name)
            elif isinstance(icon_info, str):
                icon_name = icon_info

            developer_data = doc.get('Developer', {})
            developer = developer_data.get('name', {}).get('C', 'N/A')

            license_str = doc.get('ProjectLicense', 'N/A')

            homepage_url = doc.get('Url', {}).get('homepage', 'N/A')

            screenshots = [s.get('source-image', {}).get('url') for s in doc.get('Screenshots', []) if
                           s.get('source-image', {}).get('url')]
            screenshots_json = json.dumps(screenshots)

            c.execute('''
                INSERT OR REPLACE INTO apps (id, name, summary, description, icon, developer, license, homepage, screenshots)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (app_id, name, summary, description, icon_name, developer, license_str, homepage_url,
                  screenshots_json))

    conn.commit()


def get_random_apps(conn, limit=6):
    c = conn.cursor()
    c.execute('SELECT id, name, summary, icon FROM apps ORDER BY RANDOM() LIMIT ?', (limit,))
    return c.fetchall()


def ensure_db():
    first_run = not os.path.isfile(DB_PATH) or os.stat(DB_PATH).st_size == 0
    conn = sqlite3.connect(DB_PATH)
    create_db(conn)
    if first_run:
        print("[DEBUG] Populating SQL database")
        populate_db(conn)
    return conn


def create_landing(container, main_window):
    grid = Gtk.Grid()
    grid.set_row_spacing(24)
    grid.set_column_spacing(24)
    grid.set_margin_start(24)
    grid.set_margin_end(24)
    grid.set_margin_top(24)
    grid.set_margin_bottom(24)
    grid.set_column_homogeneous(True)
    container.append(grid)

    conn = ensure_db()
    max_apps = 6
    apps = get_random_apps(conn, max_apps * 3)
    create_landing.app_count = 0
    app_index = 0

    def add_app_tile(_=None):
        nonlocal app_index
        if create_landing.app_count >= max_apps or app_index >= len(apps):
            return False

        app_id, display_name, description, icon_name = apps[app_index]

        icon_path = None
        if ICON_BASE_PATH:
            candidate_name = icon_name
            if not icon_name.lower().endswith('.png'):
                candidate_name = icon_name + ".png"
            candidate = os.path.join(ICON_BASE_PATH, candidate_name)
            if os.path.isfile(candidate):
                icon_path = candidate

        if not icon_path:
            app_index += 1
            return True

        button = Gtk.Button()
        button.set_hexpand(True)
        button.set_vexpand(False)
        button.set_margin_top(6)
        button.set_margin_bottom(6)
        button.set_margin_start(6)
        button.set_margin_end(6)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_hexpand(True)

        icon = Gtk.Image.new_from_file(icon_path)
        icon.set_valign(Gtk.Align.CENTER)
        icon.set_pixel_size(64)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_hexpand(True)

        title_label = Gtk.Label(label=display_name)
        title_label.set_halign(Gtk.Align.START)
        title_label.add_css_class("title-3")
        title_label.set_hexpand(True)

        description_label = Gtk.Label(label=description)
        description_label.set_halign(Gtk.Align.START)
        description_label.add_css_class("dim-label")
        description_label.set_wrap(True)
        description_label.set_max_width_chars(30)
        description_label.set_hexpand(True)

        vbox.append(title_label)
        vbox.append(description_label)

        hbox.append(icon)
        hbox.append(vbox)

        button.set_child(hbox)

        row = create_landing.app_count // 3
        col = create_landing.app_count % 3
        grid.attach(button, col, row, 1, 1)

        def on_button_clicked(btn, app_id=app_id):
            main_window.show_detail(app_id)

        button.connect("clicked", on_button_clicked)

        create_landing.app_count += 1
        app_index += 1
        return True

    GLib.timeout_add(50, add_app_tile)