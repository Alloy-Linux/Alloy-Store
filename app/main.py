import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw

from landing import create_landing

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.main_box)
        self.set_resizable(True)

        self.create_sidebar()
        create_landing(self.main_box)

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
        header.set_xalign(0)
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
