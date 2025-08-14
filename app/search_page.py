import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw

from landing import ICON_BASE_PATH, GENERIC_ICON_NAMES

class SearchPage(Gtk.Box):
    def __init__(self, apps, main_window, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        self.set_hexpand(True)
        self.set_vexpand(True)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_hexpand(True)
        content_box.set_vexpand(False)

        scrolled_window.set_child(content_box)
        self.append(scrolled_window)

        self.main_window = main_window

        if not apps:
            no_results_label = Gtk.Label(label="No results found.")
            no_results_label.add_css_class("title-2")
            no_results_label.set_halign(Gtk.Align.CENTER)
            content_box.append(no_results_label)
            return

        for app_data in apps:
            app_id = app_data.get('id')
            display_name = app_data.get('name')
            description = app_data.get('summary')
            icon_name = app_data.get('icon')
            source_type = app_data.get('source_type', 'local_appstream')

            if source_type == 'nixpkgs_search':
                display_name = f"{display_name} (Nixpkgs)"
            elif source_type == 'flatpak':
                display_name = f"{display_name} (Flatpak)"

            icon_path = None
            if ICON_BASE_PATH:
                candidate_name = icon_name
                if not icon_name.lower().endswith('.png'):
                    candidate_name = icon_name + ".png"
                candidate = os.path.join(ICON_BASE_PATH, candidate_name)
                if os.path.isfile(candidate):
                    icon_path = candidate

            icon_image = None
            placeholder_path = os.path.join(os.path.dirname(__file__), "..", "images", "placeholder.png")
            placeholder_exists = os.path.exists(placeholder_path)

            if icon_name in GENERIC_ICON_NAMES:
                if placeholder_exists:
                    icon_image = Gtk.Image.new_from_file(placeholder_path)
            else:
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

            icon_image.set_pixel_size(64)

            button = Gtk.Button()
            button.set_hexpand(True)
            button.set_vexpand(False)
            button.set_margin_top(6)
            button.set_margin_bottom(6)
            button.set_margin_start(6)
            button.set_margin_end(6)
            button.add_css_class("flat")

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_hexpand(True)

            icon = icon_image
            icon.set_valign(Gtk.Align.CENTER)

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
            description_label.set_max_width_chars(80)
            description_label.set_hexpand(True)

            vbox.append(title_label)
            vbox.append(description_label)

            hbox.append(icon)
            hbox.append(vbox)

            button.set_child(hbox)
            content_box.append(button)

            def on_button_clicked(btn, app_id=app_id, source_type=source_type):
                self.main_window.show_detail(app_id, source_type=source_type)

            button.connect("clicked", on_button_clicked)