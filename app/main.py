import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import gi
import json
import threading

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Pango, GLib

from landing import create_landing, ensure_db, get_apps_by_category, search_local_apps, search_nixpkgs_apps
from detail_page import DetailPage
from search_page import SearchPage

APPSTREAM_YAML_PATH = os.environ.get("NIXOS_APPSTREAM_DATA")
DB_PATH = os.path.expanduser('~/.cache/alloy_store_apps.db')


def get_app_details_from_db(app_id):
    conn = ensure_db()
    c = conn.cursor()
    c.execute(
        'SELECT name, summary, description, icon, developer, license, homepage, screenshots, nix_package_attribute, flatpak_ref, origin, source_type '
        'FROM apps WHERE id = ?',
        (app_id,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        name, summary, description, icon, developer, license, homepage, screenshots_json, nix_package_attribute, flatpak_ref, origin, source_type = row
        screenshots = json.loads(screenshots_json) if screenshots_json else []
        return {
            'name': name,
            'summary': summary,
            'description': description,
            'icon': icon,
            'developer': developer,
            'license': license,
            'homepage': homepage,
            'screenshots': screenshots,
            'nix_package_attribute': nix_package_attribute,
            'flatpak_ref': flatpak_ref,
            'origin': origin,
            'source_type': source_type
        }
    return None


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_resizable(True)
        self.set_default_size(900, 600)

        self.root_vbox = Gtk.Box()
        self.root_vbox.set_spacing(0)
        self.root_vbox.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_child(self.root_vbox)

        self.search_bar = Gtk.SearchBar()
        self.search_bar.add_css_class("inline")
        self.search_bar.set_halign(Gtk.Align.CENTER)
        self.search_bar.set_vexpand(False)
        self.search_bar.set_hexpand(True)
        self.root_vbox.append(self.search_bar)

        self.main_box = Gtk.Box()
        self.main_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.main_box.set_spacing(0)
        self.root_vbox.append(self.main_box)

        self.create_sidebar()

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_box.append(self.content_box)

        self.detail_page = None
        self.category_cache = {}
        self.current_view = None
        self.previous_view = None

        self.current_category = "Featured"
        self.current_source = "nixpkgs"
        conn = ensure_db()
        initial_apps = get_apps_by_category(conn, self.current_category, 18, self.current_source)
        self.category_cache[self.current_category] = initial_apps
        self.current_view = create_landing(self.content_box, self, category=self.current_category, apps=initial_apps)
        self.content_box.append(self.current_view)

        self.header = Gtk.HeaderBar()
        self.header.set_show_title_buttons(True)
        self.header.set_decoration_layout(":minimize,maximize,close")

        title_label = self.create_title_label("Alloy Store")
        self.header.set_title_widget(title_label)

        self.header.add_css_class("flat")
        self.header.add_css_class("default-decoration")

        self.set_titlebar(self.header)

        search_entry = Gtk.SearchEntry()
        self.search_bar.set_child(search_entry)
        self.search_bar.connect_entry(search_entry)

        search_button = Gtk.ToggleButton()
        search_button.set_icon_name("system-search-symbolic")
        search_button.connect("toggled", self.on_search_button_toggled)
        self.header.pack_start(search_button)

        self.source_selection_model = Gtk.StringList.new(["Nixpkgs", "Flatpak"])
        self.source_dropdown = Gtk.DropDown.new(self.source_selection_model, None)
        self.source_dropdown.set_selected(0)
        self.source_dropdown.set_tooltip_text("Select app source (Nixpkgs or Flatpak)")
        self.source_dropdown.connect("notify::selected-item", self.on_source_selected)
        self.header.pack_start(self.source_dropdown)

        search_entry.connect("search-changed", self.on_search_text_changed)

        self.source_dropdown.set_selected(0)
        self.current_source = "nixpkgs"

    def _clear_content_views(self):
        if self.detail_page and self.detail_page.get_parent():
            self.content_box.remove(self.detail_page)
            self.detail_page = None
        if self.current_view and self.current_view.get_parent():
            self.content_box.remove(self.current_view)
            self.current_view = None

    def create_title_label(self, text):
        label = Gtk.Label(label=text)
        label.add_css_class("title-2")
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_xalign(0.5)
        return label

    def on_search_button_toggled(self, button):
        self.search_bar.set_search_mode(button.get_active())

    def on_search_text_changed(self, search_entry):
        query = search_entry.get_text().strip()

        self._clear_content_views()

        conn = ensure_db()
        if query:
            self._clear_content_views()
            loading_label = Gtk.Label(label="Searching... Please wait.")
            loading_label.add_css_class("title-2")
            loading_label.set_halign(Gtk.Align.CENTER)
            loading_label.set_valign(Gtk.Align.CENTER)
            self.content_box.append(loading_label)
            loading_label.show()
            self.current_view = loading_label

            def run_search_in_background():
                thread_conn = ensure_db()
                local_apps = search_local_apps(thread_conn, query, 25, self.current_source)
                
                nixpkgs_apps = []
                if self.current_source == "nixpkgs":
                    nixpkgs_apps = search_nixpkgs_apps(query, 25)

                combined_apps = []
                for app_data in local_apps:
                    combined_apps.append({
                        'id': app_data[0],
                        'name': app_data[1],
                        'summary': app_data[2],
                        'icon': app_data[3],
                        'nix_package_attribute': app_data[4],
                        'source_type': app_data[5]
                    })
                
                if self.current_source == "nixpkgs":
                    combined_apps.extend(nixpkgs_apps)

                GLib.idle_add(self.update_search_results_ui, combined_apps)

            search_thread = threading.Thread(target=run_search_in_background)
            search_thread.start()

        else:
            if self.current_category in self.category_cache:
                apps = self.category_cache[self.current_category]
            else:
                apps = get_apps_by_category(conn, self.current_category, 18, self.current_source)
                self.category_cache[self.current_category] = apps
            self.current_view = create_landing(self.content_box, self, category=self.current_category, apps=apps)
            self.content_box.append(self.current_view)

    def update_search_results_ui(self, combined_apps):
        self._clear_content_views()

        self.current_view = SearchPage(combined_apps, self)
        self.content_box.append(self.current_view)
        self.current_view.show()
        return GLib.SOURCE_REMOVE

    def on_source_selected(self, dropdown, pspec):
        selected_item = dropdown.get_selected_item()
        if selected_item:
            selected_source_text = selected_item.get_string()
            if selected_source_text == "Nixpkgs":
                self.current_source = "nixpkgs"
            elif selected_source_text == "Flatpak":
                self.current_source = "flatpak"
            
            if self.current_category in self.category_cache:
                del self.category_cache[self.current_category]

            active_category_button = None
            for btn in self.category_buttons:
                if btn.get_active():
                    active_category_button = btn
                    break
            
            if active_category_button:
                self.on_category_toggled(active_category_button)

    def create_sidebar(self):
        self.sidebar = Gtk.Box()
        self.sidebar.set_orientation(Gtk.Orientation.VERTICAL)
        self.sidebar.set_spacing(10)
        self.sidebar.set_margin_top(10)
        self.sidebar.set_margin_bottom(10)
        self.sidebar.set_margin_start(10)
        self.sidebar.set_margin_end(10)
        self.sidebar.set_size_request(180, -1)
        self.main_box.append(self.sidebar)

        header = Gtk.Label()
        header.set_label("Categories")
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

        self.category_buttons = []
        for i, category in enumerate(categories):
            btn = Gtk.ToggleButton()
            btn.set_label(category)
            btn.set_halign(Gtk.Align.START)
            btn.add_css_class("flat")
            btn.set_margin_bottom(5)

            if i == 0:
                btn.set_active(True)

            btn.connect("toggled", self.on_category_toggled)
            self.category_buttons.append(btn)
            self.sidebar.append(btn)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(10)
        self.sidebar.append(separator)

    def on_category_toggled(self, toggled_btn):
        if toggled_btn.get_active():
            for btn in self.category_buttons:
                if btn is not toggled_btn:
                    btn.set_active(False)

            category = toggled_btn.get_label()
            self.current_category = category

            self._clear_content_views()

            conn = ensure_db()
            apps = get_apps_by_category(conn, category, 18, self.current_source)
            self.category_cache[category] = apps

            self.current_view = create_landing(self.content_box, self, category=self.current_category, apps=apps)
            self.content_box.append(self.current_view)

    def show_detail(self, app_id, source_type='local_appstream'):
        app_info = None
        if source_type == 'local_appstream' or source_type == 'flatpak':
            app_info = get_app_details_from_db(app_id)
        elif source_type == 'nixpkgs_search':
            package_name = app_id.split('.')[-1]
            app_info = {
                'name': package_name,
                'summary': f"No summary found for {package_name}'.",
                'description': f"No description found for {package_name}'.",
                'icon': 'application-x-executable',
                'developer': 'None',
                'license': 'N/A',
                'homepage': 'No home page found.',
                'screenshots': [],
                'nix_package_attribute': package_name
            }

        if not app_info:
            return

        if hasattr(self, 'current_view') and self.current_view:
            self.previous_view = self.current_view

        self._clear_content_views()

        self.detail_page = DetailPage(app_info, parent_window=self)
        self.content_box.append(self.detail_page)

    def show_landing(self):
        self._clear_content_views()

        if hasattr(self, 'current_view') and self.current_view and self.current_view.get_parent() is None:
            self.content_box.append(self.current_view)

    def go_back(self):
        self._clear_content_views()

        if self.previous_view:
            self.current_view = self.previous_view
            self.content_box.append(self.current_view)
            self.previous_view = None
        else:
            conn = ensure_db()
            apps = get_apps_by_category(conn, self.current_category, 18, self.current_source)
            self.current_view = create_landing(self.content_box, self, category=self.current_category, apps=apps)
            self.content_box.append(self.current_view)


class App(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.win = None
        

    def do_activate(self):
        self.win = MainWindow()
        self.win.set_application(app)
        self.win.present()


app = App()
app.run(sys.argv)
