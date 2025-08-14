import gi
import re
import yaml
import gzip
import os
import sqlite3
import json
import subprocess
import xml.etree.ElementTree as ET

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk

APPSTREAM_YAML_PATH = os.environ.get("NIXOS_APPSTREAM_DATA")
DB_PATH = os.path.expanduser('~/.cache/alloy_store_apps.db')

icons_base_dir = None
if APPSTREAM_YAML_PATH and os.path.isfile(APPSTREAM_YAML_PATH):
    share_app_info_dir = os.path.dirname(os.path.dirname(APPSTREAM_YAML_PATH))
    icons_base_dir = os.path.join(share_app_info_dir, "icons", "nixos", "64x64")
else:
    icons_base_dir = None

ICON_BASE_PATH = icons_base_dir

GENERIC_ICON_NAMES = [
    "application-x-executable",
    "image-missing",
    "utilities-terminal",
    "text-x-generic"
]

def _get_landing_icon_image(icon_name):
    icon_path = None
    if ICON_BASE_PATH:
        candidate_name = icon_name
        if not icon_name.lower().endswith('.png'):
            candidate_name = icon_name + ".png"
        candidate = os.path.join(ICON_BASE_PATH, candidate_name)
        if os.path.isfile(candidate):
            icon_path = candidate
    return icon_path


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
            screenshots TEXT,
            category TEXT,
            nix_package_attribute TEXT NULL,
            flatpak_ref TEXT NULL,
            origin TEXT NULL,
            source_type TEXT NOT NULL DEFAULT 'local_appstream'
        )
    ''')
    conn.commit()


def populate_db(conn):
    if not APPSTREAM_YAML_PATH or not os.path.isfile(APPSTREAM_YAML_PATH):
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

            nix_package_attribute = app_id.lower()
            if nix_package_attribute.endswith('.desktop'):
                nix_package_attribute = nix_package_attribute[:-len('.desktop')]
            nix_package_attribute = re.sub(r'[._]', '-', nix_package_attribute)

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

            categories = doc.get('Categories', [])
            category_json = json.dumps(categories) if categories else json.dumps(["Uncategorized"])

            c.execute('''
                INSERT OR REPLACE INTO apps 
                (id, name, summary, description, icon, developer, license, homepage, screenshots, category, nix_package_attribute, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (app_id, name, summary, description, icon_name, developer, license_str, homepage_url,
                  screenshots_json, category_json, nix_package_attribute, 'local_appstream'))

    conn.commit()


def populate_flatpak_apps(conn):
    c = conn.cursor()
    appstream_path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'flatpak', 'appstream', 'flathub', 'x86_64', 'active', 'appstream.xml.gz')

    if not os.path.isfile(appstream_path):
        return

    with gzip.open(appstream_path, 'rt', encoding='utf-8') as f:
        tree = ET.parse(f)
        root = tree.getroot()

        for component in root.findall('component'):
            if component.get('type') not in ('desktop', 'desktop-application'):
                continue

            app_id = component.find('id').text if component.find('id') is not None else None
            if not app_id:
                continue

            name = component.find('name').text if component.find('name') is not None else 'Unknown'
            summary = component.find('summary').text if component.find('summary') is not None else 'No summary'
            
            description_element = component.find('description')
            description = ''
            if description_element is not None:
                description = ''.join(description_element.itertext())
            else:
                description = 'No description'

            icon_element = component.find('icon[@type="cached"]')
            icon_name = icon_element.text if icon_element is not None else 'application-x-executable'

            developer = component.find('developer_name').text if component.find('developer_name') is not None else 'N/A'
            license_str = component.find('project_license').text if component.find('project_license') is not None else 'N/A'
            
            homepage_element = component.find('url[@type="homepage"]')
            homepage_url = homepage_element.text if homepage_element is not None else 'N/A'

            screenshots_list = []
            screenshots_element = component.find('screenshots')
            if screenshots_element is not None:
                for screenshot in screenshots_element.findall('screenshot/image'):
                    screenshots_list.append(screenshot.text)
            screenshots_json = json.dumps(screenshots_list)

            categories_list = []
            categories_element = component.find('categories')
            if categories_element is not None:
                for category in categories_element.findall('category'):
                    categories_list.append(category.text)
            category_json = json.dumps(categories_list) if categories_list else json.dumps(["Uncategorized"])

            flatpak_ref = app_id
            origin = 'flathub'

            c.execute('''
                INSERT OR REPLACE INTO apps 
                (id, name, summary, description, icon, developer, license, homepage, screenshots, category, flatpak_ref, origin, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (app_id, name, summary, description, icon_name, developer, license_str, homepage_url,
                  screenshots_json, category_json, flatpak_ref, origin, 'flatpak'))

    conn.commit()


def get_apps_by_category(conn, category, limit=6, source_type="local_appstream"):
    c = conn.cursor()
    if category == "Featured":
        if source_type == "nixpkgs":
            c.execute("SELECT id, name, summary, icon, source_type FROM apps WHERE source_type = 'local_appstream' OR source_type = 'nixpkgs_search' ORDER BY RANDOM() LIMIT ?", (limit,))
        elif source_type == "flatpak":
            c.execute("SELECT id, name, summary, icon, source_type FROM apps WHERE source_type = 'flatpak' ORDER BY RANDOM() LIMIT ?", (limit,))
        else:
            c.execute('SELECT id, name, summary, icon, source_type FROM apps ORDER BY RANDOM() LIMIT ?', (limit,))
    else:
        category_map = {
            "Games": "Game",
            "Socialize": "Network",
            "Work": "Office",
            "Development": "Development",
        }
        search_category = category_map.get(category, category)
        if source_type == "nixpkgs":
            c.execute("SELECT id, name, summary, icon, source_type FROM apps WHERE (source_type = 'local_appstream' OR source_type = 'nixpkgs_search') AND INSTR(LOWER(category), LOWER(?)) > 0 ORDER BY RANDOM() LIMIT ?",
                      (search_category, limit))
        elif source_type == "flatpak":
            c.execute("SELECT id, name, summary, icon, source_type FROM apps WHERE source_type = 'flatpak' AND INSTR(LOWER(category), LOWER(?)) > 0 ORDER BY RANDOM() LIMIT ?",
                      (search_category, limit))
        else:
            c.execute('SELECT id, name, summary, icon, source_type FROM apps WHERE INSTR(LOWER(category), LOWER(?)) > 0 ORDER BY RANDOM() LIMIT ?',
                      (search_category, limit))
    return c.fetchall()

def search_local_apps(conn, query, limit=6, source_type="local_appstream"):
    c = conn.cursor()
    search_pattern = f"%{query}%"
    if source_type == "nixpkgs":
        c.execute('''
            SELECT id, name, summary, icon, nix_package_attribute, source_type FROM apps
            WHERE (LOWER(name) LIKE LOWER(?) OR LOWER(summary) LIKE LOWER(?)) AND (source_type = 'local_appstream' OR source_type = 'nixpkgs_search')
            ORDER BY name LIMIT ?
        ''', (search_pattern, search_pattern, limit))
    elif source_type == "flatpak":
        c.execute('''
            SELECT id, name, summary, icon, nix_package_attribute, source_type FROM apps
            WHERE (LOWER(name) LIKE LOWER(?) OR LOWER(summary) LIKE LOWER(?)) AND source_type = 'flatpak'
            ORDER BY name LIMIT ?
        ''', (search_pattern, search_pattern, limit))
    else:
        c.execute('''
            SELECT id, name, summary, icon, nix_package_attribute, source_type FROM apps
            WHERE LOWER(name) LIKE LOWER(?) OR LOWER(summary) LIKE LOWER(?)
            ORDER BY name LIMIT ?
        ''', (search_pattern, search_pattern, limit))
    return c.fetchall()

def search_nixpkgs_apps(query, limit=6):
    results = []
    command = ["nix", "search", "--json", "nixpkgs", query]
    process = subprocess.run(command, capture_output=True, text=True, check=True)
    nix_output = json.loads(process.stdout)

    count = 0
    for attr_path, details in nix_output.items():
        if count >= limit:
            break

        package_name = attr_path.split('.')[-1]
        description = details.get('description', 'No description available.')
        version = details.get('version', '')

        results.append({
            'id': attr_path,
            'name': f"{package_name} ({version})",
            'summary': description,
            'icon': 'application-x-executable',
            'nix_package_attribute': package_name,
            'source_type': 'nixpkgs_search'
        })
        count += 1
    return results


def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    create_db(conn)

    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM apps")
    count = c.fetchone()[0]

    if count == 0:
        populate_db(conn)
        populate_flatpak_apps(conn)
        
    return conn


def create_landing(container, main_window, category="Featured", apps=None):
    grid = Gtk.Grid()
    grid.set_row_spacing(24)
    grid.set_column_spacing(24)
    grid.set_margin_start(24)
    grid.set_margin_end(24)
    grid.set_margin_top(24)
    grid.set_margin_bottom(24)
    grid.set_column_homogeneous(True)

    max_apps = 6
    if apps is None:
        conn = ensure_db()
        apps = get_apps_by_category(conn, category, max_apps * 3, main_window.current_source)
    
    app_count = 0
    for app_data in apps:
        if app_count >= max_apps:
            break

        app_id, display_name, description, icon_name, source_type = app_data

        icon_image = None
        placeholder_path = os.path.join(os.path.dirname(__file__), "..", "images", "placeholder.png")
        placeholder_exists = os.path.exists(placeholder_path)

        if icon_name in GENERIC_ICON_NAMES:
            if placeholder_exists:
                icon_image = Gtk.Image.new_from_file(placeholder_path)
        else:
            icon_path = _get_landing_icon_image(icon_name)
            if source_type == 'flatpak':
                flatpak_icon_path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'flatpak', 'appstream', 'flathub', 'x86_64', 'active', 'icons', '64x64', f"{icon_name}.png")
                if os.path.exists(flatpak_icon_path):
                    icon_image = Gtk.Image.new_from_file(flatpak_icon_path)

            if not icon_image and icon_path and os.path.exists(icon_path):
                icon_image = Gtk.Image.new_from_file(icon_path)

        if not icon_image:
            if placeholder_exists:
                icon_image = Gtk.Image.new_from_file(placeholder_path)
            else:
                icon_image = Gtk.Image.new_from_icon_name("image-missing")


        button = Gtk.Button()
        button.set_hexpand(True)
        button.set_vexpand(False)
        button.set_margin_top(6)
        button.set_margin_bottom(6)
        button.set_margin_start(6)
        button.set_margin_end(6)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_hexpand(True)

        icon_image.set_valign(Gtk.Align.CENTER)
        icon_image.set_pixel_size(64)

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

        hbox.append(icon_image)
        hbox.append(vbox)

        button.set_child(hbox)

        row = app_count // 3
        col = app_count % 3
        grid.attach(button, col, row, 1, 1)

        def on_button_clicked(btn, app_id=app_id, source_type=source_type):
            main_window.show_detail(app_id, source_type)

        button.connect("clicked", on_button_clicked)

        app_count += 1

    while app_count < max_apps:
        placeholder = Gtk.Box()
        placeholder.set_hexpand(True)
        placeholder.set_vexpand(False)
        row = app_count // 3
        col = app_count % 3
        grid.attach(placeholder, col, row, 1, 1)
        app_count += 1

    return grid
