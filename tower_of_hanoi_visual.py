import tkinter as tk
from tkinter import ttk, messagebox
import time, io
from PIL import Image
import imageio

class HanoiVisualizer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tower of Hanoi Visualizer")
        self.resizable(False, False)
        self.canvas_width = 720
        self.canvas_height = 360
        self.peg_positions = []
        self.disk_items = []
        self.move_sequence = []
        self.is_running = False
        self.is_paused = False
        self.current_move_index = 0
        self.after_id = None

        # For recording
        self.frames = []

        self._build_ui()

    def _build_ui(self):
        control_frame = ttk.Frame(self, padding=8)
        control_frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(control_frame, text="Disks (1-10):").grid(row=0, column=0, sticky="w")
        self.disk_var = tk.IntVar(value=4)
        self.disk_spin = ttk.Spinbox(control_frame, from_=1, to=12, width=5, textvariable=self.disk_var)
        self.disk_spin.grid(row=0, column=1, sticky="w", padx=(4,12))

        ttk.Label(control_frame, text="Speed (ms):").grid(row=0, column=2, sticky="w")
        self.speed_var = tk.IntVar(value=300)
        self.speed_scale = ttk.Scale(control_frame, from_=50, to=1000, orient="horizontal", command=self._sync_speed_entry)
        self.speed_scale.set(self.speed_var.get())
        self.speed_scale.grid(row=0, column=3, sticky="ew", padx=(4,12))
        control_frame.columnconfigure(3, weight=1)

        self.speed_entry = ttk.Entry(control_frame, width=6, textvariable=self.speed_var)
        self.speed_entry.grid(row=0, column=4, sticky="w")

        self.start_btn = ttk.Button(control_frame, text="Start", command=self.start)
        self.start_btn.grid(row=0, column=5, padx=6)

        self.pause_btn = ttk.Button(control_frame, text="Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=0, column=6)

        self.reset_btn = ttk.Button(control_frame, text="Reset", command=self.reset, state="disabled")
        self.reset_btn.grid(row=0, column=7, padx=(6,0))

        # Canvas
        self.canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, bg="#f7f7f7")
        self.canvas.grid(row=1, column=0, padx=8, pady=(0,8))

        info_frame = ttk.Frame(self, padding=(8,0,8,8))
        info_frame.grid(row=2, column=0, sticky="ew")

        self.move_label = ttk.Label(info_frame, text="Moves: 0")
        self.move_label.grid(row=0, column=0, sticky="w")

        self.status_label = ttk.Label(info_frame, text="Status: Idle")
        self.status_label.grid(row=0, column=1, sticky="w", padx=12)

        ttk.Label(info_frame, text="Move list:").grid(row=1, column=0, sticky="nw", pady=(6,0))
        self.moves_text = tk.Text(info_frame, width=60, height=6, state="disabled")
        self.moves_text.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4,0))

    def _sync_speed_entry(self, ev):
        try:
            val = int(float(self.speed_scale.get()))
            self.speed_var.set(val)
        except Exception:
            pass

    def start(self):
        if self.is_running:
            return
        try:
            n = int(self.disk_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid number of disks.")
            return
        if n < 1 or n > 12:
            messagebox.showerror("Invalid input", "Please enter disks between 1 and 12 (recommended 1-10).")
            return
        self.n = n
        self._setup_pegs_and_disks(n)
        self.move_sequence = []
        self._generate_moves(n, 0, 1, 2)
        self._show_move_list()
        self.is_running = True
        self.is_paused = False
        self.current_move_index = 0
        self.frames = []  # reset frames
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.reset_btn.config(state="normal")
        self.status_label.config(text="Status: Running")
        self._schedule_next_move()

    def reset(self):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.is_running = False
        self.is_paused = False
        self.current_move_index = 0
        self.move_sequence = []
        self.disk_items = []
        self.canvas.delete("all")
        self.peg_positions = []
        self.move_label.config(text="Moves: 0")
        self.status_label.config(text="Status: Idle")
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="Pause")
        self.reset_btn.config(state="disabled")
        self.moves_text.config(state="normal")
        self.moves_text.delete("1.0", tk.END)
        self.moves_text.config(state="disabled")

    def toggle_pause(self):
        if not self.is_running:
            return
        if not self.is_paused:
            if self.after_id:
                self.after_cancel(self.after_id)
                self.after_id = None
            self.is_paused = True
            self.pause_btn.config(text="Resume")
            self.status_label.config(text="Status: Paused")
        else:
            self.is_paused = False
            self.pause_btn.config(text="Pause")
            self.status_label.config(text="Status: Running")
            self._schedule_next_move()

    def _setup_pegs_and_disks(self, n):
        self.canvas.delete("all")
        margin = 40
        spacing = (self.canvas_width - margin*2) // 3
        base_y = self.canvas_height - 30
        peg_height = 180
        peg_width = 8
        peg_top = base_y - peg_height
        self.peg_positions = []
        for i in range(3):
            x = margin + i*spacing + spacing//2
            self.peg_positions.append(x)
            self.canvas.create_rectangle(x-60, base_y, x+60, base_y+8, fill="#ddd", outline="")
            self.canvas.create_rectangle(x-peg_width//2, peg_top, x+peg_width//2, base_y, fill="#b36500", outline="")

        self.stacks = [[], [], []]
        self.disk_items = []
        max_disk_width = 160
        min_disk_width = 40
        disk_height = 18
        palette = ["#ff6666","#ffb366","#ffd966","#b3ff66","#66ffb3",
                   "#66d9ff","#7c66ff","#ff66d9","#c0c0c0","#ff8c66"]
        for size in range(n, 0, -1):
            width = int(min_disk_width + (max_disk_width - min_disk_width) * (size-1)/(n-1 if n>1 else 1))
            color = palette[(size-1) % len(palette)]
            x = self.peg_positions[0]
            y = base_y - disk_height * (len(self.stacks[0]) + 1)
            item = self.canvas.create_rectangle(x - width//2, y - disk_height, x + width//2, y, fill=color, outline="black")
            text = self.canvas.create_text(x, y - disk_height//2, text=str(size), fill="black")
            self.disk_items.append((item, text, width, disk_height))
            self.stacks[0].append(len(self.disk_items)-1)

    def _generate_moves(self, n, src, aux, dst):
        if n == 1:
            self.move_sequence.append((src, dst))
        else:
            self._generate_moves(n-1, src, dst, aux)
            self.move_sequence.append((src, dst))
            self._generate_moves(n-1, aux, src, dst)

    def _show_move_list(self):
        self.moves_text.config(state="normal")
        self.moves_text.delete("1.0", tk.END)
        for i, (a,b) in enumerate(self.move_sequence, start=1):
            self.moves_text.insert(tk.END, f"{i}: {a+1}->{b+1}\n")
        self.moves_text.config(state="disabled")

    def _schedule_next_move(self):
        if self.current_move_index >= len(self.move_sequence):
            self.status_label.config(text="Status: Completed")
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled")

            # Save video when done
            if self.frames:
                imageio.mimsave("hanoi.mp4", self.frames, fps=30)
                messagebox.showinfo("Saved", "Animation saved as hanoi.mp4")

            return
        delay = max(10, int(self.speed_var.get()))
        self.after_id = self.after(delay, self._perform_move_step)

    def _perform_move_step(self):
        if self.is_paused:
            return
        if self.current_move_index >= len(self.move_sequence):
            return
        src, dst = self.move_sequence[self.current_move_index]
        self._animate_move(src, dst)
        self.current_move_index += 1
        self.move_label.config(text=f"Moves: {self.current_move_index} / {len(self.move_sequence)}")
        self._schedule_next_move()

    def _animate_move(self, src, dst):
        if not self.stacks[src]:
            return
        disk_idx = self.stacks[src].pop()
        item_id, text_id, width, height = self.disk_items[disk_idx]
        src_x = self.peg_positions[src]
        dst_x = self.peg_positions[dst]
        base_y = self.canvas_height - 30
        src_y = base_y - height * (len(self.stacks[src]) + 1)
        dst_y = base_y - height * (len(self.stacks[dst]) + 1)

        lift_y = src_y - 60
        steps = 18
        delay = max(6, int(self.speed_var.get() // 8))

        # move up
        x1, y1, x2, y2 = self.canvas.coords(item_id)
        dy = (lift_y - y2) / steps
        for _ in range(steps):
            self.canvas.move(item_id, 0, dy)
            self.canvas.move(text_id, 0, dy)
            self.canvas.update()
            self._save_frame()
            time.sleep(delay/1000.0)

        # move horizontally
        x1, y1, x2, y2 = self.canvas.coords(item_id)
        cur_x = (x1 + x2) / 2
        dx = (dst_x - cur_x) / steps
        for _ in range(steps):
            self.canvas.move(item_id, dx, 0)
            self.canvas.move(text_id, dx, 0)
            self.canvas.update()
            self._save_frame()
            time.sleep(delay/1000.0)

        # drop down
        x1, y1, x2, y2 = self.canvas.coords(item_id)
        cur_bottom = y2
        dy = (dst_y - cur_bottom) / steps
        for _ in range(steps):
            self.canvas.move(item_id, 0, dy)
            self.canvas.move(text_id, 0, dy)
            self.canvas.update()
            self._save_frame()
            time.sleep(delay/1000.0)

        self.stacks[dst].append(disk_idx)

    def _save_frame(self):
        ps = self.canvas.postscript(colormode="color")
        img = Image.open(io.BytesIO(ps.encode("utf-8")))
        self.frames.append(img)

def main():
    app = HanoiVisualizer()
    app.mainloop()

if __name__ == "__main__":
    main()

