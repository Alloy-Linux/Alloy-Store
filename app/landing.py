import subprocess
import gi
import concurrent.futures

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, GLib

executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def create_landing(container, initial_packages=None):
    grid = Gtk.Grid()
    grid.set_row_spacing(24)
    grid.set_column_spacing(24)
    grid.set_margin_start(24)
    grid.set_margin_end(24)
    grid.set_margin_top(24)
    grid.set_margin_bottom(24)

    grid.set_column_homogeneous(True)
    container.append(grid)

    def clear_grid_children():
        child = grid.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            grid.remove(child)
            child = next_child

    def update_grid(packages_str):
        clear_grid_children()
        packages = packages_str.split("\n")

        for i, pkg in enumerate(packages):
            display_name = pkg.split('.')[-1]

            button = Gtk.Button()
            button.set_hexpand(True)
            button.set_vexpand(False)
            button.set_margin_top(6)
            button.set_margin_bottom(6)
            button.set_margin_start(6)
            button.set_margin_end(6)

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_hexpand(True)

            icon = Gtk.Image.new_from_icon_name("application-x-executable")
            icon.set_valign(Gtk.Align.CENTER)
            icon.set_pixel_size(128)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            vbox.set_hexpand(True)

            title_label = Gtk.Label(label=display_name)
            title_label.set_xalign(0)
            title_label.add_css_class("title-3")
            title_label.set_hexpand(True)

            description_label = Gtk.Label(label=f"Description for {display_name}")
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

    if initial_packages:
        update_grid(initial_packages)
    else:
        def on_packages_ready(future):
            try:
                packages = future.result()
                GLib.idle_add(update_grid, packages)
            except Exception as e:
                GLib.idle_add(print, f"Error: {e}")

        future = executor.submit(get_random_packages)
        future.add_done_callback(on_packages_ready)


def get_random_packages(amount_of_packages: str = "6") -> str:
    try:
        p1 = subprocess.Popen(
            ["nix", "search", "nixpkgs", "--json", "^"],
            stdout=subprocess.PIPE
        )
        p2 = subprocess.Popen(
            ["jq", "-r", "keys[]"],
            stdin=p1.stdout, stdout=subprocess.PIPE
        )
        p3 = subprocess.Popen(
            ["shuf", "-n", amount_of_packages],
            stdin=p2.stdout, stdout=subprocess.PIPE
        )

        p1.stdout.close()
        p2.stdout.close()

        output = p3.communicate()[0].decode().strip()
        return output
    except Exception as e:
        return f"Error getting packages: {e}"
