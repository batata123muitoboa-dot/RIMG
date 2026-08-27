import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import shutil
import subprocess
from PIL import Image, ImageTk
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from rimg import (
    load_rimg,
    png_to_rimg,
    rimg_to_png
)


BG = "#111111"
SIDEBAR = "#181818"
CARD = "#202020"
TEXT = "#ffffff"
SUBTEXT = "#999999"
ACCENT = "#7c5cff"

class RVisualizer:
    def __init__(self, root):
        self.root = root

        self.root.title("RVisualizer")
        self.root.geometry("1100x700")
        self.root.minsize(800, 500)

        self.image = None
        self.tk_image = None
        self.filename = None

        self.zoom = 1.0

        self.create_ui()

    # ========================================================
    # UI
    # ========================================================

    def create_ui(self):

        self.root.configure(fg_color=BG)

        # ----------------------------------------------------
        # Sidebar
        # ----------------------------------------------------

        self.sidebar = ctk.CTkFrame(
            self.root,
            fg_color=SIDEBAR,
            width=230,
            corner_radius=0
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)

        # Logo

        logo = ctk.CTkLabel(
            self.sidebar,
            text="RVisualizer",
            text_color=TEXT,
            font=("TkDefaultFont", 20, "bold")
        )

        logo.pack(
            anchor="w",
            padx=25,
            pady=(25, 5)
        )

        subtitle = ctk.CTkLabel(
            self.sidebar,
            text="Image Viewer",
            text_color=SUBTEXT,
            font=("TkDefaultFont", 10)
        )

        subtitle.pack(
            anchor="w",
            padx=27
        )

        # Open button

        self.open_button = ctk.CTkButton(
            self.sidebar,
            text="＋  Abrir imagem",
            command=self.open_image,
            fg_color=ACCENT,
            hover_color="#6b4de0",
            text_color="white",
            font=("TkDefaultFont", 11, "bold"),
            corner_radius=10,
            cursor="hand2"
        )

        self.open_button.pack(
            fill="x",
            padx=20,
            pady=(30, 10),
            ipady=4
        )

        # Info title

        ctk.CTkLabel(
            self.sidebar,
            text="INFORMAÇÕES",
            text_color=SUBTEXT,
            font=("TkDefaultFont", 9, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 8)
        )

        self.info_name = self.create_info(
            "Arquivo",
            "—"
        )

        self.info_format = self.create_info(
            "Formato",
            "—"
        )

        self.info_resolution = self.create_info(
            "Resolução",
            "—"
        )

        self.info_size = self.create_info(
            "Tamanho",
            "—"
        )

                # ----------------------------------------------------
        # Converter
        # ----------------------------------------------------

        ctk.CTkLabel(
            self.sidebar,
            text="CONVERTER",
            text_color=SUBTEXT,
            font=("TkDefaultFont", 9, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 8)
        )

        ctk.CTkButton(
            self.sidebar,
            text="PNG → RIMG",
            command=self.convert_png_to_rimg,
            fg_color=CARD,
            hover_color="#2b2b2b",
            text_color=TEXT,
            corner_radius=8
        ).pack(
            fill="x",
            padx=20,
            pady=4
        )

        ctk.CTkButton(
            self.sidebar,
            text="RIMG → PNG",
            command=self.convert_rimg_to_png,
            fg_color=CARD,
            hover_color="#2b2b2b",
            text_color=TEXT,
            corner_radius=8
        ).pack(
            fill="x",
            padx=20,
            pady=4
        )

        # ----------------------------------------------------
        # Main
        # ----------------------------------------------------

        self.main = ctk.CTkFrame(
            self.root,
            fg_color=BG,
            corner_radius=0
        )

        self.main.pack(
            side="left",
            fill="both",
            expand=True
        )

        # Header

        self.header = ctk.CTkFrame(
            self.main,
            fg_color=BG,
            height=60,
            corner_radius=0
        )

        self.header.pack(
            fill="x"
        )

        self.title_label = ctk.CTkLabel(
            self.header,
            text="Nenhuma imagem aberta",
            text_color=TEXT,
            font=("TkDefaultFont", 13, "bold")
        )

        self.title_label.pack(
            side="left",
            padx=25,
            pady=20
        )

        # ----------------------------------------------------
        # Preview
        # ----------------------------------------------------

        self.preview_frame = ctk.CTkFrame(
            self.main,
            fg_color=CARD,
            corner_radius=12
        )

        self.preview_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 15)
        )

        self.canvas = tk.Canvas(
            self.preview_frame,
            bg=CARD,
            highlightthickness=0
        )

        self.canvas.pack(
            fill="both",
            expand=True,
            padx=2,
            pady=2
        )

        self.canvas.bind(
            "<Configure>",
            lambda event: self.display_image()
        )

        self.canvas.bind(
            "<MouseWheel>",
            self.on_scroll
        )

        self.canvas.bind(
            "<Button-4>",
            self.on_scroll
        )

        self.canvas.bind(
            "<Button-5>",
            self.on_scroll
        )

        # ----------------------------------------------------
        # Bottom controls
        # ----------------------------------------------------

        bottom = ctk.CTkFrame(
            self.main,
            fg_color=BG,
            height=50,
            corner_radius=0
        )

        bottom.pack(
            fill="x",
            padx=20,
            pady=(0, 15)
        )

        self.zoom_label = ctk.CTkLabel(
            bottom,
            text="100%",
            text_color=SUBTEXT
        )

        self.zoom_label.pack(
            side="right",
            padx=10
        )

        ctk.CTkButton(
            bottom,
            text="−",
            command=lambda: self.change_zoom(0.8),
            fg_color=CARD,
            hover_color="#2b2b2b",
            text_color=TEXT,
            corner_radius=8,
            width=40
        ).pack(side="right")

        ctk.CTkButton(
            bottom,
            text="+",
            command=lambda: self.change_zoom(1.25),
            fg_color=CARD,
            hover_color="#2b2b2b",
            text_color=TEXT,
            corner_radius=8,
            width=40
        ).pack(side="right")

        ctk.CTkButton(
            bottom,
            text="100%",
            command=self.reset_zoom,
            fg_color=CARD,
            hover_color="#2b2b2b",
            text_color=TEXT,
            corner_radius=8,
            width=55
        ).pack(side="right")

        return None

    # ========================================================
    # SYSTEM FILE DIALOG
    # ========================================================

    def _run_dialog(
        self,
        command
    ):

        try:

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        except (
            OSError,
            subprocess.SubprocessError
        ):

            return None

        if result.returncode != 0:
            return None

        filename = result.stdout.strip()

        if not filename:
            return None

        return filename

    def _kdialog(
        self,
        title,
        extensions,
        save=False
    ):

        if not shutil.which("kdialog"):
            return None

        patterns = " ".join(
            f"*{extension}"
            for extension in extensions
        )

        if save:

            command = [
                "kdialog",
                "--getsavefilename",
                str(
                    Path.home()
                    / f"imagem{extensions[0]}"
                ),
                patterns,
                "--title",
                title
            ]

        else:

            command = [
                "kdialog",
                "--getopenfilename",
                str(Path.home()),
                patterns,
                "--title",
                title
            ]

        return self._run_dialog(command)

    def _zenity(
        self,
        title,
        extensions,
        save=False
    ):

        if not shutil.which("zenity"):
            return None

        command = [
            "zenity",
            "--file-selection",
            "--title",
            title
        ]

        if save:

            command.extend([
                "--save",
                "--confirm-overwrite"
            ])

        else:

            patterns = " ".join(
                f"*{extension}"
                for extension in extensions
            )

            command.extend([
                "--file-filter",
                f"Arquivos | {patterns}"
            ])

        return self._run_dialog(command)

    def _yad(
        self,
        title,
        extensions,
        save=False
    ):

        if not shutil.which("yad"):
            return None

        command = [
            "yad",
            "--file-selection",
            f"--title={title}"
        ]

        if save:

            command.extend([
                "--save",
                "--confirm-overwrite"
            ])

        else:

            patterns = " ".join(
                f"*{extension}"
                for extension in extensions
            )

            command.append(
                f"--file-filter=Arquivos | {patterns}"
            )

        return self._run_dialog(command)

    def choose_file(
        self,
        title,
        extensions
    ):

        # KDE / KDialog
        filename = self._kdialog(
            title,
            extensions,
            save=False
        )

        if filename:
            return filename

        # GTK/Zenity
        filename = self._zenity(
            title,
            extensions,
            save=False
        )

        if filename:
            return filename

        # YAD
        filename = self._yad(
            title,
            extensions,
            save=False
        )

        if filename:
            return filename

        return None

    def save_file(
        self,
        title,
        extension
    ):

        extensions = [extension]

        # KDE / KDialog
        filename = self._kdialog(
            title,
            extensions,
            save=True
        )

        if filename:
            return filename

        # GTK/Zenity
        filename = self._zenity(
            title,
            extensions,
            save=True
        )

        if filename:
            return filename

        # YAD
        filename = self._yad(
            title,
            extensions,
            save=True
        )

        if filename:
            return filename

        return None

    # ========================================================
    # INFO
    # ========================================================

    def create_info(self, title, value):

        frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent",
            corner_radius=0
        )

        frame.pack(
            fill="x",
            padx=25,
            pady=6
        )

        ctk.CTkLabel(
            frame,
            text=title,
            text_color=SUBTEXT
        ).pack(anchor="w")

        label = ctk.CTkLabel(
            frame,
            text=value,
            text_color=TEXT,
            font=("TkDefaultFont", 10, "bold")
        )

        label.pack(anchor="w")

        return label

    # ========================================================
    # OPEN
    # ========================================================

    def open_image(self):

        filename = self.choose_file(
            "Abrir imagem",
            [".rimg", ".png", ".jpg", ".jpeg"]
        )

        if not filename:
            return

        try:

            extension = Path(
                filename
            ).suffix.lower()

            if extension == ".rimg":

                image = load_rimg(filename)
                format_name = "RIMG"

            else:

                image = Image.open(filename)
                format_name = image.format or extension[1:].upper()

            self.image = image.convert("RGBA")
            self.filename = filename
            self.zoom = 1.0

            self.title_label.configure(
                text=Path(filename).name
            )

            self.info_name.configure(
                text=Path(filename).name
            )

            self.info_format.configure(
                text=format_name
            )

            self.info_resolution.configure(
                text=f"{self.image.width} × {self.image.height}"
            )

            size = Path(filename).stat().st_size

            if size >= 1024 * 1024:

                size_text = f"{size / 1024 / 1024:.2f} MB"

            elif size >= 1024:

                size_text = f"{size / 1024:.1f} KB"

            else:

                size_text = f"{size} B"

            self.info_size.configure(
                text=size_text
            )

            self.display_image()

        except Exception as e:

            messagebox.showerror(
                "Erro",
                str(e)
            )

    # ========================================================
    # CONVERSÃO
    # ========================================================

    def convert_png_to_rimg(self):

        filename = self.choose_file(
            "Selecionar PNG",
            [".png"]
        )

        if not filename:
            return

        output = self.save_file(
            "Salvar RIMG",
            ".rimg"
        )

        if not output:
            return

        # Garante que a extensão correta está no final do arquivo
        if not output.lower().endswith(".rimg"):
            output += ".rimg"

        try:

            png_to_rimg(
                filename,
                output
            )

            messagebox.showinfo(
                "Conversão concluída",
                f"RIMG criado com sucesso!\n\n{output}"
            )

        except Exception as e:

            messagebox.showerror(
                "Erro",
                str(e)
            )

    def convert_rimg_to_png(self):

        filename = self.choose_file(
            "Selecionar RIMG",
            [".rimg"]
        )

        if not filename:
            return

        output = self.save_file(
            "Salvar PNG",
            ".png"
        )

        if not output:
            return

        # Garante que a extensão correta está no final do arquivo
        if not output.lower().endswith(".png"):
            output += ".png"

        try:

            rimg_to_png(
                filename,
                output
            )

            messagebox.showinfo(
                "Conversão concluída",
                f"PNG criado com sucesso!\n\n{output}"
            )

        except Exception as e:

            messagebox.showerror(
                "Erro",
                str(e)
            )

    # ========================================================
    # DISPLAY
    # ========================================================

    def display_image(self):

        if self.image is None:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            return

        width = max(
            1,
            int(self.image.width * self.zoom)
        )

        height = max(
            1,
            int(self.image.height * self.zoom)
        )

        resized = self.image.resize(
            (width, height),
            Image.Resampling.NEAREST
        )

        self.tk_image = ImageTk.PhotoImage(
            resized
        )

        self.canvas.delete("all")

        self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.tk_image,
            anchor="center"
        )

        self.zoom_label.configure(
            text=f"{self.zoom * 100:.0f}%"
        )

    # ========================================================
    # ZOOM
    # ========================================================

    def on_scroll(self, event):

        if self.image is None:
            return

        if hasattr(event, "delta") and event.delta != 0:

            if event.delta > 0:
                factor = 1.1
            else:
                factor = 0.9

        elif event.num == 4:
            factor = 1.1

        elif event.num == 5:
            factor = 0.9

        else:
            return

        self.change_zoom(factor)

    def change_zoom(self, factor):

        if self.image is None:
            return

        self.zoom *= factor

        self.zoom = max(
            0.05,
            min(self.zoom, 20)
        )

        self.display_image()

    def reset_zoom(self):

        if self.image is None:
            return

        self.zoom = 1.0

        self.display_image()


# ============================================================
# START
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()

app = RVisualizer(root)

root.mainloop()
