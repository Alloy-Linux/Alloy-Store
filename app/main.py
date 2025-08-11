import sys
import gi
import os
import gzip
import yaml
import pprint
import sqlite3
import json

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw
from landing import create_landing, ensure_db
from detail_page import DetailPage

APPSTREAM_YAML_PATH = os.environ.get("NIXOS_APPSTREAM_DATA")
DB_PATH = os.path.expanduser('~/.cache/alloy_store_apps.db')

def get_all_children(container):
    children = []
    child = container.get_first_child()
    while child is not None:
        children.append(child)
        child = child.get_next_sibling()
    return children

def remove_all_children(container):
    for child in get_all_children(container):
        container.remove(child)

def get_app_details_from_db(app_id):
    conn = ensure_db()
    c = conn.cursor()
    c.execute('SELECT name, summary, description, icon, developer, license, homepage, screenshots FROM apps WHERE id = ?', (app_id,))
    row = c.fetchone()
    conn.close()
    if row:
        name, summary, description, icon, developer, license, homepage, screenshots_json = row
        screenshots = json.loads(screenshots_json) if screenshots_json else []
        return {
            'name': name,
            'summary': summary,
            'description': description,
            'icon': icon,
            'developer': developer,
            'license': license,
            'homepage': homepage,
            'screenshots': screenshots
        }
    return None

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_resizable(True)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.main_box)

        self.create_sidebar()

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.append(self.content_box)

        self.detail_page = None

        create_landing(self.content_box, self)

    def create_sidebar(self):
        self.sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
            margin_top=10,
            margin_bottom=10,
            margin_start=10,
            margin_end=10
        )
        self.sidebar.set_size_request(180, -1)
        self.main_box.append(self.sidebar)

        header = Gtk.Label(label="Categories")
        header.add_css_class("title-2")
        header.set_halign(Gtk.Align.START)
        header.set_margin_bottom(10)
        self.sidebar.append(header)

        categories = [
            "Featured",
            "Games",
            "Socialize",
            "Work",
            "Development"
        ]

        for category in categories:
            button = Gtk.Button(
                label=category,
                halign=Gtk.Align.START
            )
            button.add_css_class("flat")
            button.set_margin_bottom(5)

            motion_ctrl = Gtk.EventControllerMotion.new()
            motion_ctrl.connect("enter", lambda ctrl, x, y, btn=button: btn.add_css_class("hover"))
            motion_ctrl.connect("leave", lambda ctrl, btn=button: btn.remove_css_class("hover"))
            button.add_controller(motion_ctrl)

            self.sidebar.append(button)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(10)
        self.sidebar.append(separator)

    def show_detail(self, app_id):
        app_info = get_app_details_from_db(app_id)
        if not app_info:
            print(f"[ERROR] App with ID {app_id} not found in database.", file=sys.stderr)
            return

        if self.detail_page:
            self.content_box.remove(self.detail_page)
            self.detail_page = None

        remove_all_children(self.content_box)

        self.detail_page = DetailPage(app_info, parent_window=self)
        self.content_box.append(self.detail_page)

    def show_landing(self):
        if self.detail_page:
            self.content_box.remove(self.detail_page)
            self.detail_page = None

        remove_all_children(self.content_box)
        create_landing(self.content_box, self)


class App(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.win = None
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


app = App(application_id="org.Alloy-Linux")
app.run(sys.argv)