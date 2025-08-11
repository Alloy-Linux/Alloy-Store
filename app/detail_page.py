import gi
import os
import sys
import html
import re
from gi.repository import Gtk, GdkPixbuf, Gio, GLib

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

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

        try:
            if icon_path:
                icon_image = Gtk.Image.new_from_file(icon_path)
            else:
                icon_image = Gtk.Image.new_from_icon_name(app_info['icon'])
        except Exception:
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

        desc_text = html_to_pango(app_info['description'])
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
                try:
                    img = Gtk.Image()

                    def on_download_complete(source, result, img_to_update=img):
                        try:
                            stream = Gio.File.read_finish(source, result)
                            if not stream:
                                print("[DEBUG] Stream is None")
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
                                print(f"[DEBUG] Original image size: {width}x{height}")

                                fixed_width = 800
                                fixed_height = 450
                                print(f"[DEBUG] Scaling image to fixed size: {fixed_width}x{fixed_height}")

                                scaled_pixbuf = pixbuf.scale_simple(fixed_width, fixed_height,
                                                                    GdkPixbuf.InterpType.BILINEAR)
                                img_to_update.set_from_pixbuf(scaled_pixbuf)
                                img_to_update.set_size_request(fixed_width, fixed_height)
                                print(f"[DEBUG] Set image size request to: {fixed_width}x{fixed_height}")

                            stream.close()
                        except Exception as e:
                            print(f"[ERROR] Failed to load image from URL: {e}", file=sys.stderr)

                    cancellable = Gio.Cancellable.new()
                    file = Gio.File.new_for_uri(shot_url)
                    file.read_async(GLib.PRIORITY_DEFAULT, cancellable, on_download_complete, img)

                    screenshots_flowbox.append(img)
                except Exception as e:
                    print(f"[ERROR] Could not load screenshot {shot_url}: {e}", file=sys.stderr)

    def on_back_clicked(self, button):
        if self.parent_window:
            self.parent_window.show_landing()