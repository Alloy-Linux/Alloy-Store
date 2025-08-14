import os
import sys
import html
import re
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GdkPixbuf, GLib
from landing import GENERIC_ICON_NAMES

APPSTREAM_YAML_PATH = os.environ.get("NIXOS_APPSTREAM_DATA")

icons_base_dir = None
if APPSTREAM_YAML_PATH and os.path.isfile(APPSTREAM_YAML_PATH):
    share_app_info_dir = os.path.dirname(os.path.dirname(APPSTREAM_YAML_PATH))
    icons_base_dir = os.path.join(share_app_info_dir, "icons", "nixos", "64x64")
else:
    icons_base_dir = None

ICON_BASE_PATH = icons_base_dir


def html_to_pango(text):
    text = html.escape(text)

    text = re.sub(r'&lt;p&gt;', '\n', text)
    text = re.sub(r'&lt;/p&gt;', '\n', text)
    text = re.sub(r'&lt;br\s*/?&gt;', '\n', text)
    text = re.sub(r'&lt;/?ul&gt;', '', text)
    text = re.sub(r'&lt;li&gt;', '• ', text)
    text = re.sub(r'&lt;/li&gt;', '\n', text)

    text = re.sub(r'\n\s*\n+', '\n\n', text)

    return text.strip()


class DetailPage(Gtk.ScrolledWindow):
    def __init__(self, app_info, parent_window=None):
        super().__init__()
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_margin_top(10)
        self.set_margin_bottom(10)
        self.set_margin_start(10)
        self.set_margin_end(10)

        self.parent_window = parent_window

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_hexpand(True)
        main_box.set_vexpand(True)

        self.set_child(main_box)

        back_button = Gtk.Button(label="← Back")
        back_button.get_style_context().add_class("suggested-action")
        back_button.set_size_request(80, 30)
        back_button.set_halign(Gtk.Align.START)
        back_button.connect("clicked", self.on_back_clicked)
        main_box.append(back_button)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        header_box.set_hexpand(True)
        main_box.append(header_box)

        icon_path = None
        if ICON_BASE_PATH:
            candidate_name = app_info['icon']
            if not candidate_name.lower().endswith('.png'):
                candidate_name += ".png"
            candidate = os.path.join(ICON_BASE_PATH, candidate_name)
            if os.path.isfile(candidate):
                icon_path = candidate

        icon_image = None
        placeholder_path = os.path.join(os.path.dirname(__file__), "..", "images", "placeholder.png")
        placeholder_exists = os.path.exists(placeholder_path)
        source_type = app_info.get('source_type', 'local_appstream')
        icon_name = app_info['icon']

        if icon_name in GENERIC_ICON_NAMES:
            if placeholder_exists:
                icon_image = Gtk.Image.new_from_file(placeholder_path)
        else:
            if source_type == 'flatpak':
                flatpak_icon_path = os.path.join(os.path.expanduser('~'), '.local', 'share', 'flatpak', 'appstream', 'flathub', 'x86_64', 'active', 'icons', '128x128', f"{icon_name}.png")
                if os.path.exists(flatpak_icon_path):
                    icon_image = Gtk.Image.new_from_file(flatpak_icon_path)

            if not icon_image and icon_path and os.path.exists(icon_path):
                icon_image = Gtk.Image.new_from_file(icon_path)

        if not icon_image:
            if placeholder_exists:
                icon_image = Gtk.Image.new_from_file(placeholder_path)
            else:
                icon_image = Gtk.Image.new_from_icon_name("image-missing")

        icon_image.set_pixel_size(128)
        icon_image.set_valign(Gtk.Align.CENTER)
        header_box.append(icon_image)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_vexpand(True)
        header_box.append(info_box)

        name_label = Gtk.Label(label=f"{app_info['name']}")
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class("title-1")
        info_box.append(name_label)

        summary_label = Gtk.Label(label=app_info['summary'])
        summary_label.set_halign(Gtk.Align.START)
        summary_label.set_wrap(True)
        summary_label.get_style_context().add_class("dim-label")
        info_box.append(summary_label)

        developer_label = Gtk.Label(label=f"Developer: {app_info['developer']}")
        developer_label.set_halign(Gtk.Align.START)
        info_box.append(developer_label)

        license_label = Gtk.Label(label=f"License: {app_info['license']}")
        license_label.set_halign(Gtk.Align.START)
        info_box.append(license_label)

        if app_info['homepage'] and app_info['homepage'] != 'N/A':
            homepage_link = Gtk.LinkButton.new_with_label(app_info['homepage'], f"Homepage: {app_info['homepage']}")
            homepage_link.set_halign(Gtk.Align.START)
            info_box.append(homepage_link)

        install_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        install_box.set_valign(Gtk.Align.START)
        install_box.set_halign(Gtk.Align.END)
        header_box.append(install_box)

        source_type = app_info.get('source_type', 'local_appstream')

        def on_install_clicked(button):
            install_id = None
            method = ""

            if source_type == 'flatpak':
                install_id = app_info.get('flatpak_ref')
                method = 'flatpak'
            else:
                install_id = app_info.get('nix_package_attribute')
                method = f"nixpkgs ({self.install_method})"

            if install_id:
                print(f"Installing {install_id} ({method})")
            
            # TODO: Install logic

        if source_type == 'flatpak':
            install_button = Gtk.Button(label="Install")
            install_button.get_style_context().add_class("suggested-action")
            install_button.set_size_request(120, 30)
            install_button.connect("clicked", on_install_clicked)
            install_box.append(install_button)
        else: # It's a nix package
            install_button = Gtk.Button(label="Install (User)")
            install_button.get_style_context().add_class("suggested-action")
            install_button.set_size_request(120, 30)

            self.install_method = "user"
            self.nix_package_attribute = app_info.get('nix_package_attribute', 'N/A')

            install_button.connect("clicked", on_install_clicked)
            install_box.append(install_button)

            menu_button = Gtk.MenuButton()
            menu_button.set_tooltip_text("Choose installation method")

            menu = Gio.Menu()
            menu.append("User Installation", "app.install.user")
            menu.append("System Installer", "app.install.system")
            menu_button.set_menu_model(menu)

            def on_menu_item_selected(action, param):
                method = action.get_name().split('.')[-1]
                self.install_method = method
                install_button.set_label(f"Install ({method.capitalize()})")

            app = Gio.Application.get_default()
            if not app:
                app = Gio.Application()

            for method in ("user", "system"):
                action_name = f"install.{method}"
                action = Gio.SimpleAction.new(action_name, None)
                action.connect("activate", on_menu_item_selected)
                action.set_enabled(self.nix_package_attribute != 'N/A')
                app.add_action(action)

            install_box.append(menu_button)

        description_content = app_info.get('description') or ""
        desc_text = html_to_pango(description_content)
        desc_label = Gtk.Label(label=desc_text)
        desc_label.set_use_markup(True)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_wrap(True)
        desc_label.set_wrap_mode(Gtk.WrapMode.WORD)
        desc_label.set_justify(Gtk.Justification.LEFT)
        main_box.append(desc_label)

        if app_info['screenshots']:
            screenshots_title = Gtk.Label(label="Screenshots")
            screenshots_title.set_halign(Gtk.Align.START)
            screenshots_title.add_css_class("title-2")
            main_box.append(screenshots_title)

            screenshots_scrolled_window = Gtk.ScrolledWindow()
            screenshots_scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
            screenshots_scrolled_window.set_size_request(-1, 1200)
            main_box.append(screenshots_scrolled_window)

            screenshots_flowbox = Gtk.FlowBox()
            screenshots_flowbox.set_valign(Gtk.Align.START)
            screenshots_flowbox.set_max_children_per_line(5)
            screenshots_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
            screenshots_scrolled_window.set_child(screenshots_flowbox)

            for shot_url in app_info['screenshots']:
                img = Gtk.Image()

                def on_download_complete(source, result, img_to_update=img):
                    stream = Gio.File.read_finish(source, result)
                    if not stream:
                        return

                    pixbuf_loader = GdkPixbuf.PixbufLoader.new()

                    data = stream.read_bytes(4096, None)
                    while data.get_size() > 0:
                        pixbuf_loader.write(data.get_data())
                        data = stream.read_bytes(4096, None)

                    pixbuf_loader.close()

                    pixbuf = pixbuf_loader.get_pixbuf()
                    if pixbuf:
                        width = pixbuf.get_width()
                        height = pixbuf.get_height()

                        fixed_width = 800
                        fixed_height = 450

                        scaled_pixbuf = pixbuf.scale_simple(fixed_width, fixed_height,
                                                                GdkPixbuf.InterpType.BILINEAR)
                        img_to_update.set_from_pixbuf(scaled_pixbuf)
                        img_to_update.set_size_request(fixed_width, fixed_height)

                    stream.close()

                cancellable = Gio.Cancellable.new()
                file = Gio.File.new_for_uri(shot_url)
                file.read_async(GLib.PRIORITY_DEFAULT, cancellable, on_download_complete, img)

                screenshots_flowbox.append(img)

    def on_back_clicked(self, button):
        if self.parent_window:
            self.parent_window.go_back()