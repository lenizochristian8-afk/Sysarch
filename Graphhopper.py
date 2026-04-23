import os
import requests
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# =========================================
# CONFIG
# =========================================
ROUTE_URL = "https://graphhopper.com/api/1/route?"
API_KEY = ("a7165d35-6383-44cd-b07d-4f6ce277403d")

# Distance Converter feature.
DISTANCE_DISPLAY_OPTIONS = ["miles only", "kilometers only", "both"]


# =========================================
# API FUNCTIONS
# =========================================
def geocoding(location, key):
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode(
        {"q": location, "limit": 1, "key": key}
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        status = response.status_code
    except requests.exceptions.RequestException as e:
        return None, None, None, None, f"Geocoding request failed: {e}"
    except ValueError:
        return None, None, None, None, "Geocoding response could not be decoded."

    if status == 200 and len(data.get("hits", [])) > 0:
        hit = data["hits"][0]
        lat = hit["point"]["lat"]
        lng = hit["point"]["lng"]
        name = hit.get("name", location)
        country = hit.get("country", "")
        state = hit.get("state", "")

        if state and country:
            full_name = f"{name}, {state}, {country}"
        elif country:
            full_name = f"{name}, {country}"
        else:
            full_name = name

        return status, lat, lng, full_name, None

    if status != 200:
        return status, None, None, None, data.get("message", "Unknown geocoding error.")

    return status, None, None, None, "No matching location found."


def get_route(orig, dest, vehicle, key):
    op = "&point=" + str(orig[1]) + "%2C" + str(orig[2])
    dp = "&point=" + str(dest[1]) + "%2C" + str(dest[2])

    route_request_url = (
        ROUTE_URL
        + urllib.parse.urlencode({"key": key, "vehicle": vehicle})
        + op
        + dp
    )

    try:
        response = requests.get(route_request_url, timeout=10)
        data = response.json()
        status = response.status_code
    except requests.exceptions.RequestException as e:
        return None, f"Routing request failed: {e}"
    except ValueError:
        return None, "Routing response could not be decoded."

    if status != 200:
        return None, data.get("message", "Unknown routing error.")

    return data, None


# =========================================
# GUI APP
# =========================================
class GraphHopperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GraphHopper Route Planner")
        self.root.geometry("900x700")
        self.root.configure(bg="#f4f6f8")

        self.build_styles()
        self.build_ui()
        # Track whether the currently displayed route has been saved to disk.
        # This lets us skip the "save before exit" prompt when it's unnecessary.
        self.route_saved = False

    def build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TLabel", font=("Arial", 11), background="#f4f6f8")
        style.configure("Title.TLabel", font=("Arial", 20, "bold"), foreground="#1f4e79", background="#f4f6f8")
        style.configure("Header.TLabel", font=("Arial", 12, "bold"), foreground="#0b5394", background="#f4f6f8")

        style.configure("TButton", font=("Arial", 11, "bold"), padding=8)
        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=6)

        style.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        style.configure("Summary.TLabel", font=("Courier New", 11), background="white", foreground="#222")

    def build_ui(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text="GraphHopper Route Planner", style="Title.TLabel")
        title.pack(pady=(0, 15))

        # Input card
        input_card = ttk.Frame(main, style="Card.TFrame", padding=15)
        input_card.pack(fill="x", pady=(0, 15))

        ttk.Label(input_card, text="Route Input", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(input_card, text="Starting Location:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        self.start_entry = ttk.Entry(input_card, width=45)
        self.start_entry.grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(input_card, text="Destination:").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        self.dest_entry = ttk.Entry(input_card, width=45)
        self.dest_entry.grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Label(input_card, text="Vehicle Profile:").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=6)
        self.vehicle_combo = ttk.Combobox(input_card, values=["car", "bike", "foot"], state="readonly", width=20)
        self.vehicle_combo.grid(row=3, column=1, sticky="w", pady=6)
        self.vehicle_combo.set("car")

        ttk.Label(input_card, text="Distance Display:").grid(row=4, column=0, sticky="w", padx=(0, 10), pady=6)
        self.distance_display_combo = ttk.Combobox(
            input_card,
            values=DISTANCE_DISPLAY_OPTIONS,
            state="readonly",
            width=20,
        )
        self.distance_display_combo.grid(row=4, column=1, sticky="w", pady=6)
        self.distance_display_combo.set("both")

        input_card.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(input_card)
        button_frame.grid(row=5, column=0, columnspan=2, pady=(12, 0), sticky="w")

        ttk.Button(button_frame, text="Get Route", command=self.get_route_gui).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Clear", command=self.clear_fields).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Save Route", command=self.save_route).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Exit", command=self.confirm_next_action).pack(side="left")

        # Summary card
        summary_card = ttk.Frame(main, style="Card.TFrame", padding=15)
        summary_card.pack(fill="x", pady=(0, 15))

        ttk.Label(summary_card, text="Trip Summary", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        self.summary_label = ttk.Label(
            summary_card,
            text="No route loaded yet.",
            style="Summary.TLabel",
            justify="left"
        )
        self.summary_label.pack(anchor="w")

        # Directions card
        directions_card = ttk.Frame(main, style="Card.TFrame", padding=15)
        directions_card.pack(fill="both", expand=True)

        ttk.Label(directions_card, text="Turn-by-Turn Directions", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        self.directions_text = scrolledtext.ScrolledText(
            directions_card,
            wrap="word",
            font=("Arial", 11),
            height=18
        )
        self.directions_text.pack(fill="both", expand=True)
        self.directions_text.config(state="disabled")

        self.last_route_data = None

    def get_route_gui(self):
        start = self.start_entry.get().strip()
        dest = self.dest_entry.get().strip()
        vehicle = self.vehicle_combo.get().strip().lower()
        distance_display = self.distance_display_combo.get().strip().lower()

        if API_KEY == "YOUR_API_KEY_HERE":
            messagebox.showwarning("Missing API Key", "Please set your GraphHopper API key first.")
            return

        if not start:
            messagebox.showwarning("Input Error", "Starting location cannot be blank.")
            return

        if not dest:
            messagebox.showwarning("Input Error", "Destination cannot be blank.")
            return

        if vehicle not in ["car", "bike", "foot"]:
            vehicle = "car"
            self.vehicle_combo.set("car")

        if distance_display not in DISTANCE_DISPLAY_OPTIONS:
            messagebox.showwarning("Input Error", "Please select a valid distance display option.")
            return

        self.summary_label.config(text="Processing route...")
        self.set_directions_text("Loading directions...\n")

        orig = geocoding(start, API_KEY)
        if orig[0] != 200 or orig[1] is None:
            messagebox.showerror("Geocoding Error", orig[4] or "Invalid starting location.")
            self.summary_label.config(text="No route loaded.")
            self.set_directions_text("")
            return

        dest_data = geocoding(dest, API_KEY)
        if dest_data[0] != 200 or dest_data[1] is None:
            messagebox.showerror("Geocoding Error", dest_data[4] or "Invalid destination.")
            self.summary_label.config(text="No route loaded.")
            self.set_directions_text("")
            return

        route_data, error = get_route(orig, dest_data, vehicle, API_KEY)
        if error:
            messagebox.showerror("Routing Error", error)
            self.summary_label.config(text="No route loaded.")
            self.set_directions_text("")
            return

        self.display_route(orig, dest_data, vehicle, distance_display, route_data)

    def format_distance(self, km_value, miles_value, display_mode):
        if display_mode == "miles only":
            return f"{miles_value:.1f} miles"
        if display_mode == "kilometers only":
            return f"{km_value:.1f} km"
        return f"{miles_value:.1f} miles / {km_value:.1f} km"

    def display_route(self, orig, dest, vehicle, distance_display, route_data):
        path_info = route_data["paths"][0]

        miles = path_info["distance"] / 1000 / 1.61
        km = path_info["distance"] / 1000
        sec = int(path_info["time"] / 1000 % 60)
        mins = int(path_info["time"] / 1000 / 60 % 60)
        hrs = int(path_info["time"] / 1000 / 60 / 60)
        instructions = path_info["instructions"]

        summary = (
            f"Starting Location : {orig[3]}\n"
            f"Destination       : {dest[3]}\n"
            f"Vehicle Profile   : {vehicle}\n"
            f"Distance Display  : {distance_display.title()}\n"
            f"Distance          : {self.format_distance(km, miles, distance_display)}\n"
            f"Duration          : {hrs:02d}:{mins:02d}:{sec:02d}"
        )
        self.summary_label.config(text=summary)

        directions_output = []
        for i, step in enumerate(instructions, start=1):
            text = step["text"]
            step_km = step["distance"] / 1000
            step_miles = step_km / 1.61
            directions_output.append(
                f"{i:02d}. {text}\n"
                f"    Distance: {self.format_distance(step_km, step_miles, distance_display)}\n"
            )

        self.set_directions_text("\n".join(directions_output))

        self.last_route_data = {
            "origin": orig[3],
            "destination": dest[3],
            "vehicle": vehicle,
            "distance_display": distance_display,
            "miles": miles,
            "km": km,
            "hrs": hrs,
            "mins": mins,
            "sec": sec,
            "instructions": instructions,
        }
        # Mark the newly displayed route as not-yet-saved
        self.route_saved = False

        # After displaying a route, prompt the user whether they want to
        # search another route. If they answer Yes, clear the inputs so they
        # can enter a new search. If No, leave the result displayed.
        def _ask_search_another():
            try:
                search_again = messagebox.askyesno(
                    "Search another route",
                    "Search another route?\n\nYes = search another route\nNo = stay on this screen",
                )
            except Exception:
                search_again = False

            if search_again:
                self.clear_fields()
                try:
                    self.start_entry.focus_set()
                except Exception:
                    pass

        try:
            # Schedule after a short delay to let the UI update and show the
            # displayed route before the dialog appears.
            self.root.after(100, _ask_search_another)
        except Exception:
            _ask_search_another()

    def set_directions_text(self, text):
        self.directions_text.config(state="normal")
        self.directions_text.delete("1.0", tk.END)
        self.directions_text.insert(tk.END, text)
        self.directions_text.config(state="disabled")

    def clear_fields(self):
        self.start_entry.delete(0, tk.END)
        self.dest_entry.delete(0, tk.END)
        self.vehicle_combo.set("car")
        self.distance_display_combo.set("both")
        self.summary_label.config(text="No route loaded yet.")
        self.set_directions_text("")
        self.last_route_data = None

    def save_route(self):
        if not self.last_route_data:
            messagebox.showwarning("No Data", "There is no route to save yet.")
            return

        filename = "route_result.txt"

        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write("GRAPHHOPPER ROUTE RESULT\n")
                file.write("=" * 50 + "\n")
                file.write(f"Starting Location : {self.last_route_data['origin']}\n")
                file.write(f"Destination       : {self.last_route_data['destination']}\n")
                file.write(f"Vehicle Profile   : {self.last_route_data['vehicle']}\n")
                file.write(
                    f"Distance          : "
                    f"{self.format_distance(self.last_route_data['km'], self.last_route_data['miles'], self.last_route_data['distance_display'])}\n"
                )
                file.write(
                    f"Duration          : {self.last_route_data['hrs']:02d}:"
                    f"{self.last_route_data['mins']:02d}:"
                    f"{self.last_route_data['sec']:02d}\n"
                )

            messagebox.showinfo("Saved", f"Route saved to {filename}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save file:\n{e}")

    def confirm_next_action(self):
        """Confirm exit when the Exit button is pressed.

        First ask the user to confirm exit. If they confirm and a route is
        currently loaded, ask whether to save the route before quitting.
        If no route is loaded, just quit immediately after confirmation.
        """
        try:
            confirm_exit = messagebox.askyesno(
                "Confirm Exit",
                "Are you sure you want to exit?",
            )
        except Exception:
            confirm_exit = False

        if not confirm_exit:
            # User cancelled exit; do nothing
            return

        # User confirmed exit. If there's a route loaded, ask if they want to save it.
        if self.last_route_data:
            try:
                save_before_exit = messagebox.askyesno(
                    "Save before exit",
                    "A route is loaded. Do you want to save the current route before exiting?",
                )
            except Exception:
                save_before_exit = False

            if save_before_exit:
                try:
                    self.save_route()
                except Exception:
                    # save_route shows its own dialogs; ignore failures here
                    pass

        try:
            self.root.quit()
        except Exception:
            try:
                self.root.destroy()
            except Exception:
                pass


# =========================================
# MAIN
# =========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = GraphHopperApp(root)
    root.mainloop()
