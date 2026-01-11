import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import datetime
import os
import math
import sys
import json
import traceback
import piexif
from piexif import ImageIFD, ExifIFD
import glob

# Gestion des imports optionnels
try:
    from PIL.ExifTags import TAGS
    HAS_EXIF = True
except ImportError:
    HAS_EXIF = False

def show_error_and_exit(title, message):
    """Affiche une erreur et quitte l'application"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except:
        print(f"ERREUR - {title}: {message}")
    sys.exit(1)

def get_resource_path(relative_path):
    """Obtient le chemin absolu vers une ressource"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    full_path = os.path.join(base_path, relative_path)
    return full_path

class WatermarkApp:
    def __init__(self, root):
        try:
            self.root = root
            self.root.title("Certification de propriété et de droits")
            self.root.geometry("600x900")  # Hauteur augmentée pour les nouvelles options
            
            # Créer un canvas avec scrollbar
            self.main_canvas = tk.Canvas(self.root)
            self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
            self.scrollable_frame = ttk.Frame(self.main_canvas)
            
            # Configurer le scrolling
            self.scrollable_frame.bind(
                "<Configure>",
                lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
            )
            
            # Créer une fenêtre dans le canvas pour le frame
            self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
            
            # Configurer le grid
            self.root.grid_rowconfigure(0, weight=1)
            self.root.grid_columnconfigure(0, weight=1)
            
            # Placer le canvas et la scrollbar
            self.main_canvas.grid(row=0, column=0, sticky="nsew")
            self.scrollbar.grid(row=0, column=1, sticky="ns")
            
            # Configurer le scrolling avec la molette de la souris
            self.main_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            
            # Frame principal dans le scrollable_frame
            main_frame = ttk.Frame(self.scrollable_frame, padding="10")
            main_frame.pack(fill="both", expand=True)
            
            # Essayer de définir une icône
            try:
                self.root.iconbitmap(get_resource_path(os.path.join("assets", "icon.ico")))
            except:
                pass  # Ignorer si l'icône n'est pas trouvée
            
            # Variables
            self.folder_path = tk.StringVar()
            self.single_image_path = tk.StringVar()  # Chemin d'une image unique
            self.selection_mode = tk.StringVar(value="folder")  # "folder" ou "image"
            self.output_basename = tk.StringVar(value="image")  # Nom de base pour les fichiers de sortie
            self.copyright_text = tk.StringVar(value="Certification de la qualité")
            self.signature_text = tk.StringVar(value="")  # Signature / Auteur
            
            # Variables pour les métadonnées EXIF
            self.meta_title = tk.StringVar(value="")  # Titre de l'image
            self.meta_comment = tk.StringVar(value="")  # Commentaires
            self.meta_subject = tk.StringVar(value="")  # Objet / Sujet
            
            self.opacity = tk.IntVar(value=50)
            self.position = tk.StringVar(value="Bas-Droite")
            self.num_watermarks = tk.IntVar(value=1)
            self.mosaic_mode = tk.BooleanVar(value=False)
            self.font_size_percent = tk.DoubleVar(value=5.0)
            self.copyright_symbol = tk.StringVar(value="©")
            
            # Variables pour l'espacement en mode mosaïque (facteur multiplicateur)
            self.mosaic_spacing_h = tk.DoubleVar(value=2.5)  # Espacement horizontal
            self.mosaic_spacing_v = tk.DoubleVar(value=2.5)  # Espacement vertical
            
            # Nouvelles variables pour le style de texte
            self.is_bold = tk.BooleanVar(value=False)
            self.selected_font = tk.StringVar(value="Arial")
            
            # Liste des symboles de copyright disponibles
            self.copyright_symbols = ["©", "®", "™", "(c)", "All Rights Reserved"]
            
            # Mapping des positions (français -> anglais interne)
            self.positions_fr = ["Haut-Gauche", "Haut-Droite", "Bas-Gauche", "Bas-Droite", "Centre"]
            self.positions_mapping = {
                "Haut-Gauche": "top-left",
                "Haut-Droite": "top-right",
                "Bas-Gauche": "bottom-left",
                "Bas-Droite": "bottom-right",
                "Centre": "center"
            }
            self.positions_reverse = {v: k for k, v in self.positions_mapping.items()}
            
            # Mapping des noms de polices vers leurs fichiers système (normal et bold)
            self.font_file_mapping = {
                "Arial": ("arial.ttf", "arialbd.ttf"),
                "Times New Roman": ("times.ttf", "timesbd.ttf"),
                "Verdana": ("verdana.ttf", "verdanab.ttf"),
                "Calibri": ("calibri.ttf", "calibrib.ttf"),
                "Georgia": ("georgia.ttf", "georgiab.ttf"),
                "Tahoma": ("tahoma.ttf", "tahomabd.ttf"),
                "Trebuchet MS": ("trebuc.ttf", "trebucbd.ttf"),
                "Comic Sans MS": ("comic.ttf", "comicbd.ttf"),
                "Juice ITC": ("JUICE___.TTF", None),  # Pas de version Bold
            }
            
            # Charger les polices disponibles
            self.available_fonts = self.get_available_fonts()
            
            self.create_widgets()
            
            # Initialiser l'état des contrôles
            self.toggle_mosaic_mode()
            self.toggle_selection_mode()
            
            # Configuration du thème
            style = ttk.Style()
            style.configure("TButton", padding=6)
            style.configure("TLabel", padding=4)
            style.configure("TFrame", padding=4)
            style.configure("Section.TLabelframe", padding=10)
            
            # Gestion des erreurs globales
            self.root.report_callback_exception = self.show_error
            
        except Exception as e:
            show_error_and_exit("Erreur d'initialisation", 
                              f"Impossible de démarrer l'application:\n{str(e)}")
    
    def show_error(self, exc_type, exc_value, exc_traceback):
        """Affiche les erreurs de manière plus conviviale"""
        error_msg = f"Type: {exc_type.__name__}\n"
        error_msg += f"Message: {str(exc_value)}\n"
        error_msg += "Détails techniques:\n"
        error_msg += "".join(traceback.format_tb(exc_traceback))
        
        messagebox.showerror("Erreur", error_msg)
    
    def get_available_fonts(self):
        """Récupère la liste des polices disponibles"""
        fonts = ["Arial"]  # Police par défaut
        fonts_dir = os.path.join(os.environ["WINDIR"], "Fonts")
        
        # Vérifier les polices du mapping système
        for font_name, (normal_file, bold_file) in self.font_file_mapping.items():
            ttf_path = os.path.join(fonts_dir, normal_file)
            if os.path.exists(ttf_path) and font_name not in fonts:
                fonts.append(font_name)
        
        # Ajouter les polices personnalisées du dossier fonts/
        custom_fonts_dir = get_resource_path("fonts")
        if os.path.exists(custom_fonts_dir):
            for file in os.listdir(custom_fonts_dir):
                if file.lower().endswith('.ttf'):
                    font_name = os.path.splitext(file)[0]
                    # Retirer " Bold" du nom si présent
                    if font_name.endswith(" Bold"):
                        font_name = font_name[:-5]
                    if font_name not in fonts:
                        fonts.append(font_name)
        
        return sorted(fonts)
    
    def get_font_path(self, font_name: str, is_bold: bool = False) -> str:
        """Obtient le chemin vers le fichier de police.
        
        Args:
            font_name: Nom de la police (ex: "Arial", "Juice ITC")
            is_bold: Si True, cherche la version Bold
            
        Returns:
            Chemin complet vers le fichier .ttf
        """
        fonts_dir = os.path.join(os.environ["WINDIR"], "Fonts")
        
        # Vérifier si c'est une police avec un fichier mappé
        if font_name in self.font_file_mapping:
            normal_file, bold_file = self.font_file_mapping[font_name]
            
            # Si Bold demandé et fichier Bold disponible
            if is_bold and bold_file:
                bold_path = os.path.join(fonts_dir, bold_file)
                if os.path.exists(bold_path):
                    return bold_path
            
            # Sinon retourner la version normale
            return os.path.join(fonts_dir, normal_file)
        
        # Police standard ou personnalisée
        font_filename = font_name
        if is_bold:
            font_filename += " Bold"
        font_filename += ".ttf"
        
        # Chercher d'abord dans les polices personnalisées
        custom_font_path = get_resource_path(os.path.join("fonts", font_filename))
        if os.path.exists(custom_font_path):
            return custom_font_path
        
        # Sinon chercher dans les polices système
        system_path = os.path.join(fonts_dir, font_filename)
        if os.path.exists(system_path):
            return system_path
        
        # Fallback sur Arial (ou Arial Bold)
        if is_bold:
            return os.path.join(fonts_dir, "arialbd.ttf")
        return os.path.join(fonts_dir, "arial.ttf")
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Section Sélection source
        source_frame = ttk.LabelFrame(main_frame, text="Sélection des images", 
                                    style="Section.TLabelframe")
        source_frame.pack(fill="x", pady=(0, 10))
        
        source_grid = ttk.Frame(source_frame)
        source_grid.pack(fill="x", padx=5, pady=5)
        
        # Radio boutons pour le mode de sélection
        ttk.Radiobutton(source_grid, text="Dossier", variable=self.selection_mode, 
                       value="folder", command=self.toggle_selection_mode).grid(row=0, column=0, sticky="w", padx=5)
        self.folder_entry = ttk.Entry(source_grid, textvariable=self.folder_path, width=55)
        self.folder_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.folder_btn = ttk.Button(source_grid, text="Parcourir", command=self.browse_folder)
        self.folder_btn.grid(row=0, column=2, padx=5, pady=2)
        
        ttk.Radiobutton(source_grid, text="Image", variable=self.selection_mode, 
                       value="image", command=self.toggle_selection_mode).grid(row=1, column=0, sticky="w", padx=5)
        self.image_entry = ttk.Entry(source_grid, textvariable=self.single_image_path, width=55)
        self.image_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.image_btn = ttk.Button(source_grid, text="Parcourir", command=self.browse_image)
        self.image_btn.grid(row=1, column=2, padx=5, pady=2)
        
        # Nom de base pour les fichiers de sortie
        ttk.Label(source_grid, text="Nom de sortie:").grid(row=2, column=0, sticky="w", padx=5, pady=(10, 2))
        ttk.Entry(source_grid, textvariable=self.output_basename, width=30).grid(row=2, column=1, sticky="w", padx=5, pady=(10, 2))
        ttk.Label(source_grid, text="(ex: image → image_001.jpg)").grid(row=2, column=2, sticky="w", padx=5, pady=(10, 2))
        
        source_grid.columnconfigure(1, weight=1)
        
        # Section Copyright
        copyright_frame = ttk.LabelFrame(main_frame, text="Options du Copyright", 
                                       style="Section.TLabelframe")
        copyright_frame.pack(fill="x", pady=(0, 10))
        
        # Grille pour les options de copyright
        copyright_grid = ttk.Frame(copyright_frame)
        copyright_grid.pack(fill="x", padx=5, pady=5)
        
        # Première ligne - Copyright
        ttk.Label(copyright_grid, text="Symbole:").grid(row=0, column=0, sticky="w", padx=5)
        symbol_combo = ttk.Combobox(copyright_grid, textvariable=self.copyright_symbol, 
                    values=self.copyright_symbols, width=10)
        symbol_combo.grid(row=0, column=1, sticky="w", padx=5)
        symbol_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        
        ttk.Label(copyright_grid, text="Texte:").grid(row=0, column=2, sticky="w", padx=5)
        copyright_entry = ttk.Entry(copyright_grid, textvariable=self.copyright_text, width=40)
        copyright_entry.grid(row=0, column=3, sticky="ew", padx=5)
        copyright_entry.bind("<KeyRelease>", lambda e: self.update_preview())

        # Deuxième ligne - Auteur (métadonnées uniquement)
        ttk.Label(copyright_grid, text="Auteur:").grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(10,0))
        ttk.Entry(copyright_grid, textvariable=self.signature_text, width=40).grid(
            row=1, column=2, columnspan=2, sticky="ew", padx=5, pady=(10,0))
        
        # Troisième ligne - Titre
        ttk.Label(copyright_grid, text="Titre:").grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(5,0))
        ttk.Entry(copyright_grid, textvariable=self.meta_title, 
                 width=40).grid(row=2, column=2, columnspan=2, sticky="ew", padx=5, pady=(5,0))
        
        # Quatrième ligne - Objet
        ttk.Label(copyright_grid, text="Objet:").grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=(5,0))
        ttk.Entry(copyright_grid, textvariable=self.meta_subject, 
                 width=40).grid(row=3, column=2, columnspan=2, sticky="ew", padx=5, pady=(5,0))
        
        # Cinquième ligne - Commentaires
        ttk.Label(copyright_grid, text="Commentaires:").grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=(5,0))
        ttk.Entry(copyright_grid, textvariable=self.meta_comment, 
                 width=40).grid(row=4, column=2, columnspan=2, sticky="ew", padx=5, pady=(5,0))

        # Sixième ligne - Nombre et Mode mosaïque
        self.num_label_title = ttk.Label(copyright_grid, text="Nombre:")
        self.num_label_title.grid(row=5, column=0, sticky="w", padx=5, pady=10)
        num_frame = ttk.Frame(copyright_grid)
        num_frame.grid(row=5, column=1, columnspan=2, sticky="ew", padx=5)
        
        self.num_scale = ttk.Scale(num_frame, from_=1, to=10, variable=self.num_watermarks, 
                            orient="horizontal", command=lambda v: self.update_num_label())
        self.num_scale.pack(side="left", fill="x", expand=True)
        self.num_label = ttk.Label(num_frame, text="1")
        self.num_label.pack(side="right", padx=5)

        ttk.Checkbutton(copyright_grid, text="Mode mosaïque", 
                       variable=self.mosaic_mode,
                       command=self.toggle_mosaic_mode).grid(row=5, column=3, sticky="w", padx=5)
        
        # Section Options Mosaïque
        self.mosaic_frame = ttk.LabelFrame(main_frame, text="Options Mosaïque", 
                                          style="Section.TLabelframe")
        self.mosaic_frame.pack(fill="x", pady=(0, 10))
        
        mosaic_grid = ttk.Frame(self.mosaic_frame)
        mosaic_grid.pack(fill="x", padx=5, pady=5)
        
        # Espacement horizontal
        self.spacing_h_label_title = ttk.Label(mosaic_grid, text="Espacement horizontal:")
        self.spacing_h_label_title.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        spacing_h_frame = ttk.Frame(mosaic_grid)
        spacing_h_frame.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.spacing_h_scale = ttk.Scale(spacing_h_frame, from_=0.1, to=5.0, 
                                         variable=self.mosaic_spacing_h,
                                         orient="horizontal", 
                                         command=lambda v: self.update_spacing_labels())
        self.spacing_h_scale.pack(side="left", fill="x", expand=True)
        self.spacing_h_label = ttk.Label(spacing_h_frame, text="2.5x", width=5)
        self.spacing_h_label.pack(side="right", padx=5)
        
        # Espacement vertical
        self.spacing_v_label_title = ttk.Label(mosaic_grid, text="Espacement vertical:")
        self.spacing_v_label_title.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        spacing_v_frame = ttk.Frame(mosaic_grid)
        spacing_v_frame.grid(row=1, column=1, sticky="ew", padx=5)
        
        self.spacing_v_scale = ttk.Scale(spacing_v_frame, from_=0.1, to=5.0, 
                                         variable=self.mosaic_spacing_v,
                                         orient="horizontal", 
                                         command=lambda v: self.update_spacing_labels())
        self.spacing_v_scale.pack(side="left", fill="x", expand=True)
        self.spacing_v_label = ttk.Label(spacing_v_frame, text="2.5x", width=5)
        self.spacing_v_label.pack(side="right", padx=5)
        
        # Configurer la grille pour qu'elle s'étende
        mosaic_grid.columnconfigure(1, weight=1)
        
        # Section Style de Texte (nouvelle section)
        text_style_frame = ttk.LabelFrame(main_frame, text="Style de Texte", 
                                        style="Section.TLabelframe")
        text_style_frame.pack(fill="x", pady=(0, 10))
        
        text_style_grid = ttk.Frame(text_style_frame)
        text_style_grid.pack(fill="x", padx=5, pady=5)
        
        # Police de caractères
        ttk.Label(text_style_grid, text="Police:").grid(row=0, column=0, sticky="w", padx=5)
        font_combo = ttk.Combobox(text_style_grid, textvariable=self.selected_font,
                                values=self.available_fonts, width=30, state="readonly")
        font_combo.grid(row=0, column=1, sticky="ew", padx=5)
        font_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        
        # Option Gras
        ttk.Checkbutton(text_style_grid, text="Texte en gras",
                       variable=self.is_bold,
                       command=self.update_preview).grid(row=0, column=2, sticky="w", padx=20)
        
        # Section Apparence
        appearance_frame = ttk.LabelFrame(main_frame, text="Apparence", 
                                        style="Section.TLabelframe")
        appearance_frame.pack(fill="x", pady=(0, 10))
        
        # Grille pour les options d'apparence
        appearance_grid = ttk.Frame(appearance_frame)
        appearance_grid.pack(fill="x", padx=5, pady=5)
        
        # Première ligne - Couleur et Position
        ttk.Button(appearance_grid, text="Choisir la couleur", 
                  command=self.choose_color).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        ttk.Label(appearance_grid, text="Position:").grid(row=0, column=1, sticky="w", padx=5)
        self.position_combo = ttk.Combobox(appearance_grid, textvariable=self.position, 
                    values=self.positions_fr, state="readonly")
        self.position_combo.grid(row=0, column=2, sticky="ew", padx=5)
        self.position_combo.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        
        # Deuxième ligne - Transparence
        ttk.Label(appearance_grid, text="Transparence:").grid(row=1, column=0, 
                                                            sticky="w", padx=5, pady=10)
        opacity_frame = ttk.Frame(appearance_grid)
        opacity_frame.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
        
        opacity_scale = ttk.Scale(opacity_frame, from_=0, to=100, variable=self.opacity, 
                                orient="horizontal", command=lambda v: self.update_opacity_label())
        opacity_scale.pack(side="left", fill="x", expand=True)
        self.opacity_label = ttk.Label(opacity_frame, text="50%")
        self.opacity_label.pack(side="right", padx=5)
        
        # Troisième ligne - Taille de la police
        ttk.Label(appearance_grid, text="Taille de la police (%):").grid(row=2, column=0, 
                                                                        sticky="w", padx=5)
        font_size_frame = ttk.Frame(appearance_grid)
        font_size_frame.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5)
        
        font_size_scale = ttk.Scale(font_size_frame, from_=1, to=20, variable=self.font_size_percent, 
                                  orient="horizontal", command=lambda v: self.update_font_size_label())
        font_size_scale.pack(side="left", fill="x", expand=True)
        self.font_size_label = ttk.Label(font_size_frame, text="5%")
        self.font_size_label.pack(side="right", padx=5)
        
        # Section Prévisualisation
        preview_frame = ttk.LabelFrame(main_frame, text="Prévisualisation", 
                                     style="Section.TLabelframe")
        preview_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Canvas pour la prévisualisation
        self.preview_canvas = tk.Canvas(preview_frame, width=400, height=300, bg='white')
        self.preview_canvas.pack(pady=10)
        
        # Label pour les messages de prévisualisation
        self.preview_label = ttk.Label(preview_frame, text="Sélectionnez un dossier pour voir la prévisualisation")
        self.preview_label.pack(pady=5)
        
        # Bouton de mise à jour de la prévisualisation
        ttk.Button(preview_frame, text="Actualiser la prévisualisation",
                  command=self.update_preview).pack(pady=5)
        
        # Frame pour le bouton d'application
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        # Bouton d'application avec style amélioré
        apply_button = ttk.Button(button_frame, 
                                text="Appliquer le copyright",
                                command=self.apply_watermark,
                                style="Apply.TButton")
        apply_button.pack(pady=10, padx=20, ipadx=10, ipady=5)
        
        # Configuration du style du bouton
        style = ttk.Style()
        style.configure("Apply.TButton",
                       font=("Arial", 10, "bold"),
                       padding=10)
    
    def toggle_selection_mode(self):
        """Active/désactive les champs selon le mode de sélection"""
        if self.selection_mode.get() == "folder":
            self.folder_entry.state(['!disabled'])
            self.folder_btn.state(['!disabled'])
            self.image_entry.state(['disabled'])
            self.image_btn.state(['disabled'])
        else:
            self.folder_entry.state(['disabled'])
            self.folder_btn.state(['disabled'])
            self.image_entry.state(['!disabled'])
            self.image_btn.state(['!disabled'])
        self.update_preview()
    
    def browse_image(self):
        """Sélectionne une image unique et met à jour la prévisualisation"""
        filetypes = [
            ("Images", "*.png *.jpg *.jpeg *.bmp *.gif"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("Tous les fichiers", "*.*")
        ]
        image_path = filedialog.askopenfilename(filetypes=filetypes)
        if image_path:
            self.single_image_path.set(image_path)
            # Proposer le nom du fichier comme nom de base
            basename = os.path.splitext(os.path.basename(image_path))[0]
            self.output_basename.set(basename)
            self.update_preview()
    
    def browse_folder(self):
        """Sélectionne un dossier et met à jour la prévisualisation"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.update_preview()  # Mettre à jour la prévisualisation
    
    def choose_color(self):
        """Choisit une couleur et met à jour la prévisualisation"""
        color = colorchooser.askcolor(title="Choisir la couleur du copyright")
        if color[1]:
            self.color = color[1]
            self.update_preview()  # Mettre à jour la prévisualisation
    
    def apply_watermark(self):
        # Déterminer le mode de sélection et les fichiers à traiter
        selection_mode = self.selection_mode.get()
        
        if selection_mode == "folder":
            folder = self.folder_path.get()
            if not folder:
                messagebox.showerror("Erreur", "Veuillez sélectionner un dossier")
                return
            output_folder = folder
            # Liste des fichiers à traiter
            image_files = [os.path.join(folder, f) for f in os.listdir(folder) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
                         and not f.startswith(self.output_basename.get())]
        else:
            image_path = self.single_image_path.get()
            if not image_path or not os.path.exists(image_path):
                messagebox.showerror("Erreur", "Veuillez sélectionner une image valide")
                return
            output_folder = os.path.dirname(image_path)
            image_files = [image_path]
        
        total_images = len(image_files)
        
        if total_images == 0:
            messagebox.showwarning("Attention", 
                                 "Aucune image trouvée à traiter")
            return
            
        try:
            # Obtenir le chemin de la police sélectionnée
            font_name = self.selected_font.get()
            is_bold = self.is_bold.get()
            font_path = self.get_font_path(font_name, is_bold)
            
            text = f"{self.copyright_symbol.get()} {self.copyright_text.get()}"
            opacity = self.opacity.get() / 100
            position = self.get_position_internal()
            num_watermarks = self.num_watermarks.get()
            is_mosaic = self.mosaic_mode.get()
            font_size_percent = self.font_size_percent.get() / 100
            
            # Nom de base pour les fichiers de sortie
            output_basename = self.output_basename.get().strip()
            if not output_basename:
                output_basename = "image"
            
            # Préparer les métadonnées détaillées
            watermark_info = {
                "text": text,
                "author": self.signature_text.get().strip(),
                "title": self.meta_title.get().strip(),
                "subject": self.meta_subject.get().strip(),
                "comment": self.meta_comment.get().strip(),
                "date_applied": datetime.now().isoformat(),
                "opacity": opacity,
                "position": position,
                "is_mosaic": is_mosaic,
                "num_watermarks": num_watermarks,
                "font": font_name,
                "is_bold": is_bold,
                "font_size_percent": font_size_percent,
                "application": "Certification de propriété et de droits",
                "version": "1.0"
            }
            
            # Convertir en bytes pour EXIF
            watermark_bytes = json.dumps(watermark_info).encode('utf-8')
            
            if total_images == 0:
                messagebox.showwarning("Attention", 
                                     "Aucune image trouvée à traiter")
                return
            
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Progression")
            progress_window.geometry("300x150")
            progress_window.transient(self.root)
            
            progress_label = ttk.Label(progress_window, 
                                     text="Traitement des images en cours...")
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, length=200, 
                                         mode='determinate')
            progress_bar.pack(pady=10)
            
            try:
                for index, image_path in enumerate(image_files):
                    try:
                        filename = os.path.basename(image_path)
                        progress_bar['value'] = (index + 1) / total_images * 100
                        progress_label['text'] = f"Traitement de {filename}..."
                        progress_window.update()
                        img = Image.open(image_path)
                        
                        # Créer un calque pour le watermark
                        watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
                        draw = ImageDraw.Draw(watermark)
                        
                        # Calculer la taille du texte
                        font_size = int(img.size[0] * font_size_percent)
                        try:
                            font = ImageFont.truetype(font_path, font_size)
                        except:
                            font = ImageFont.load_default()
                        
                        # Obtenir les dimensions du texte
                        text_bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        
                        if is_mosaic:
                            # Calculer la taille après rotation (-15°)
                            angle_rad = math.radians(15)
                            rotated_width = abs(text_width * math.cos(angle_rad)) + abs(text_height * math.sin(angle_rad))
                            rotated_height = abs(text_width * math.sin(angle_rad)) + abs(text_height * math.cos(angle_rad))
                            
                            # Espacement directement basé sur les sliders utilisateur
                            spacing_factor_h = self.mosaic_spacing_h.get()
                            spacing_factor_v = self.mosaic_spacing_v.get()
                            spacing_x = rotated_width * spacing_factor_h
                            spacing_y = rotated_height * spacing_factor_v
                            
                            # Calculer le nombre de watermarks nécessaires pour couvrir l'image
                            num_horizontal = max(1, int(img.size[0] / spacing_x) + 2)
                            num_vertical = max(1, int(img.size[1] / spacing_y) + 2)
                            
                            # Créer le motif de mosaïque
                            for i in range(num_horizontal):
                                for j in range(num_vertical):
                                    # Calculer la position avec décalage pour les lignes impaires
                                    x = i * spacing_x
                                    y = j * spacing_y
                                    
                                    # Décalage alterné pour les lignes impaires
                                    if j % 2 == 1:
                                        x += spacing_x / 2
                                    
                                    # Créer une image temporaire pour la rotation
                                    temp_size = int(max(text_width, text_height) * 1.5)
                                    txt_img = Image.new('RGBA', (temp_size, temp_size), (0, 0, 0, 0))
                                    txt_draw = ImageDraw.Draw(txt_img)
                                    
                                    # Dessiner le texte au centre (avec faux gras si nécessaire)
                                    text_pos = (temp_size/2 - text_width/2, temp_size/2 - text_height/2)
                                    text_fill = (*self.hex_to_rgb(self.color), int(255 * opacity))
                                    if is_bold and self.needs_fake_bold(font_name):
                                        self.draw_text_with_fake_bold(txt_draw, text_pos, text, font, text_fill)
                                    else:
                                        txt_draw.text(text_pos, text, font=font, fill=text_fill)
                                    
                                    # Rotation
                                    txt_img = txt_img.rotate(-15, expand=True, resample=Image.BICUBIC)
                                    
                                    # Calculer la position de collage
                                    paste_x = int(x - txt_img.size[0]/2)
                                    paste_y = int(y - txt_img.size[1]/2)
                                    
                                    # Coller le watermark
                                    if (paste_x + txt_img.size[0] > 0 and 
                                        paste_x < img.size[0] and 
                                        paste_y + txt_img.size[1] > 0 and 
                                        paste_y < img.size[1]):
                                        watermark.paste(txt_img, (paste_x, paste_y), txt_img)
                        else:
                            # Mode normal avec plusieurs watermarks
                            for i in range(num_watermarks):
                                # Calculer la position pour chaque watermark
                                if position == "top-left":
                                    pos = (10, 10 + i * (text_height + 10))
                                elif position == "top-right":
                                    pos = (img.size[0] - text_width - 10, 10 + i * (text_height + 10))
                                elif position == "bottom-left":
                                    pos = (10, img.size[1] - (num_watermarks - i) * (text_height + 10))
                                elif position == "bottom-right":
                                    pos = (img.size[0] - text_width - 10, 
                                         img.size[1] - (num_watermarks - i) * (text_height + 10))
                                else:  # center
                                    pos = ((img.size[0] - text_width) // 2, 
                                         ((img.size[1] - (num_watermarks * text_height)) // 2) + 
                                         i * (text_height + 10))
                                
                                text_fill = (*self.hex_to_rgb(self.color), int(255 * opacity))
                                if is_bold and self.needs_fake_bold(font_name):
                                    self.draw_text_with_fake_bold(draw, pos, text, font, text_fill)
                                else:
                                    draw.text(pos, text, font=font, fill=text_fill)
                            
                        # Fusionner les images
                        try:
                            if img.mode != 'RGBA':
                                img = img.convert('RGBA')
                            img = Image.alpha_composite(img, watermark)
                            
                            # Préparation des métadonnées EXIF
                            exif_dict = {"0th":{}, "Exif":{}, "GPS":{}, "1st":{}}
                            
                            # Préparer les informations de watermark et signature
                            watermark_info = {
                                "text": text,
                                "signature": self.signature_text.get().strip(),
                                "date_applied": datetime.now().isoformat(),
                                "opacity": opacity,
                                "position": position,
                                "is_mosaic": is_mosaic,
                                "num_watermarks": num_watermarks,
                                "font": font_name,
                                "is_bold": is_bold,
                                "font_size_percent": font_size_percent,
                                "application": "CestMonImage",
                                "version": "1.0"
                            }
                            
                            # Convertir en bytes pour EXIF
                            watermark_bytes = json.dumps(watermark_info).encode('utf-8')
                            
                            # Sauvegarder l'image avec le nouveau nom
                            output_path = self.get_unique_filename(output_folder, output_basename, index + 1, ".jpg")
                            img = img.convert('RGB')  # Convertir en RGB pour le JPEG
                            
                            # Vérifier si le format d'origine est JPEG
                            if filename.lower().endswith(('.jpg', '.jpeg')):
                                # Copier les métadonnées EXIF existantes si possible
                                try:
                                    exif_data = piexif.load(image_path)
                                    for ifd in ("0th", "Exif", "GPS", "1st"):
                                        if ifd in exif_data:
                                            exif_dict[ifd].update(exif_data[ifd])
                                except Exception:
                                    # Ignorer silencieusement les erreurs de lecture EXIF
                                    pass

                                # Ajouter nos métadonnées personnalisées (JSON complet)
                                exif_dict["Exif"][piexif.ExifIFD.UserComment] = watermark_bytes
                                
                                # Ajouter le copyright dans le champ standard
                                copyright_text = text
                                if self.signature_text.get().strip():
                                    copyright_text += " - " + self.signature_text.get().strip()
                                exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright_text.encode('utf-8')
                                
                                # Ajouter l'auteur
                                author = self.signature_text.get().strip() or "CestMonImage User"
                                exif_dict["0th"][piexif.ImageIFD.Artist] = author.encode('utf-8')
                                
                                # Ajouter le titre (ImageDescription pour EXIF, XPTitle pour Windows)
                                meta_title = self.meta_title.get().strip()
                                if meta_title:
                                    exif_dict["0th"][piexif.ImageIFD.ImageDescription] = meta_title.encode('utf-8')
                                    exif_dict["0th"][piexif.ImageIFD.XPTitle] = meta_title.encode('utf-16le')
                                
                                # Ajouter l'objet/sujet (XPSubject pour Windows)
                                meta_subject = self.meta_subject.get().strip()
                                if meta_subject:
                                    exif_dict["0th"][piexif.ImageIFD.XPSubject] = meta_subject.encode('utf-16le')
                                
                                # Ajouter les commentaires (XPComment pour Windows)
                                meta_comment = self.meta_comment.get().strip()
                                if meta_comment:
                                    exif_dict["0th"][piexif.ImageIFD.XPComment] = meta_comment.encode('utf-16le')
                                
                                # Ajouter la date et le logiciel
                                exif_dict["0th"][piexif.ImageIFD.Software] = "CestMonImage".encode('utf-8')
                                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = \
                                    datetime.now().strftime("%Y:%m:%d %H:%M:%S").encode('utf-8')
                                
                                # Nom du document
                                exif_dict["0th"][piexif.ImageIFD.DocumentName] = \
                                    os.path.basename(output_path).encode('utf-8')
                                
                                # Convertir le dictionnaire EXIF en bytes
                                exif_bytes = piexif.dump(exif_dict)
                                
                                # Sauvegarder avec les métadonnées EXIF
                                img.save(output_path, 'JPEG', quality=95, exif=exif_bytes)
                                print(f"✓ Image {filename}: Sauvegardée avec métadonnées EXIF (copyright, signature, date)")
                            else:
                                # Pour les autres formats, convertir en JPEG sans métadonnées EXIF
                                output_path = os.path.splitext(output_path)[0] + '.jpg'
                                img.save(output_path, 'JPEG', quality=95)
                                print(f"ℹ Image {filename}: Convertie en JPEG (sans métadonnées EXIF)")
                            
                        except Exception as e:
                            print(f"⚠ Erreur lors du traitement de l'image {filename}: {str(e)}")
                            try:
                                # Tentative de sauvegarde sans métadonnées
                                output_path = self.get_unique_filename(output_folder, output_basename, index + 1, ".jpg")
                                img = img.convert('RGB')
                                img.save(output_path, quality=95)
                                print(f"⚠ Image {filename}: Sauvegardée sans métadonnées (mode de secours)")
                            except Exception as save_error:
                                print(f"❌ Erreur lors de la sauvegarde de secours de {filename}: {str(save_error)}")
                                raise
                    except Exception as e:
                        print(f"❌ Erreur lors du traitement de {filename}: {str(e)}")
                        continue
                
                progress_window.destroy()
                
                # Afficher un résumé des opérations
                summary = f"Traitement terminé :\n"
                summary += f"- {total_images} images traitées\n"
                if any(f.lower().endswith(('.jpg', '.jpeg')) for f in image_files):
                    summary += "- Métadonnées EXIF ajoutées aux fichiers JPEG\n"
                if any(not f.lower().endswith(('.jpg', '.jpeg')) for f in image_files):
                    summary += "- Les images non-JPEG ont été converties en JPEG\n"
                
                messagebox.showinfo("Succès", summary)
                
            except Exception as e:
                # S'assurer que la fenêtre de progression est fermée en cas d'erreur
                try:
                    progress_window.destroy()
                except:
                    pass
                    
                error_msg = f"Une erreur s'est produite lors du traitement:\n{str(e)}"
                if not isinstance(e, (OSError, IOError)):
                    error_msg += f"\n\nDétails techniques:\n{traceback.format_exc()}"
                messagebox.showerror("Erreur", error_msg)
            
        except Exception as e:
            error_msg = f"Une erreur s'est produite lors du traitement:\n{str(e)}"
            if not isinstance(e, (OSError, IOError)):
                error_msg += f"\n\nDétails techniques:\n{traceback.format_exc()}"
            messagebox.showerror("Erreur", error_msg)
    
    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def get_position_internal(self) -> str:
        """Convertit la position française en valeur interne anglaise."""
        pos_fr = self.position.get()
        return self.positions_mapping.get(pos_fr, "bottom-right")
    
    def draw_text_with_fake_bold(self, draw, pos, text, font, fill, bold_offset=1):
        """Dessine du texte avec un effet de faux gras (pour polices sans version Bold).
        
        Args:
            draw: Objet ImageDraw
            pos: Position (x, y)
            text: Texte à dessiner
            font: Police à utiliser
            fill: Couleur de remplissage (r, g, b, a)
            bold_offset: Décalage en pixels pour l'effet gras
        """
        x, y = pos
        # Dessiner le texte plusieurs fois avec de légers décalages
        for dx in range(bold_offset + 1):
            for dy in range(bold_offset + 1):
                draw.text((x + dx, y + dy), text, font=font, fill=fill)
    
    def needs_fake_bold(self, font_name: str) -> bool:
        """Vérifie si une police nécessite un faux gras (pas de fichier Bold)."""
        if font_name in self.font_file_mapping:
            _, bold_file = self.font_file_mapping[font_name]
            return bold_file is None
        return False
    
    def get_unique_filename(self, folder: str, basename: str, index: int, extension: str = ".jpg") -> str:
        """Génère un nom de fichier unique avec numéro incrémenté.
        
        Args:
            folder: Dossier de destination
            basename: Nom de base (ex: "image")
            index: Numéro de l'image (1, 2, 3...)
            extension: Extension du fichier
            
        Returns:
            Chemin complet vers un fichier qui n'existe pas encore
        """
        # Format: basename_001.jpg
        filename = f"{basename}_{index:03d}{extension}"
        filepath = os.path.join(folder, filename)
        
        # Si le fichier existe, ajouter un suffixe
        suffix = 1
        while os.path.exists(filepath):
            filename = f"{basename}_{index:03d}_{suffix}{extension}"
            filepath = os.path.join(folder, filename)
            suffix += 1
        
        return filepath

    def update_num_label(self):
        """Met à jour le label du nombre de watermarks et la prévisualisation"""
        self.num_label.config(text=str(self.num_watermarks.get()))
        self.update_preview()
    
    def toggle_mosaic_mode(self):
        """Active/désactive les contrôles selon le mode mosaïque"""
        if self.mosaic_mode.get():
            # Mode mosaïque activé : désactiver le slider Nombre
            self.num_scale.state(['disabled'])
            self.num_label.config(foreground='gray')
            self.num_label_title.config(foreground='gray')
            # Activer les options mosaïque
            self.spacing_h_scale.state(['!disabled'])
            self.spacing_v_scale.state(['!disabled'])
            self.spacing_h_label.config(foreground='')
            self.spacing_v_label.config(foreground='')
            self.spacing_h_label_title.config(foreground='')
            self.spacing_v_label_title.config(foreground='')
        else:
            # Mode normal : activer le slider Nombre
            self.num_scale.state(['!disabled'])
            self.num_label.config(foreground='')
            self.num_label_title.config(foreground='')
            # Désactiver les options mosaïque
            self.spacing_h_scale.state(['disabled'])
            self.spacing_v_scale.state(['disabled'])
            self.spacing_h_label.config(foreground='gray')
            self.spacing_v_label.config(foreground='gray')
            self.spacing_h_label_title.config(foreground='gray')
            self.spacing_v_label_title.config(foreground='gray')
        
        # Mettre à jour la prévisualisation
        self.update_preview()
    
    def update_spacing_labels(self):
        """Met à jour les labels d'espacement et la prévisualisation"""
        self.spacing_h_label.config(text=f"{self.mosaic_spacing_h.get():.1f}x")
        self.spacing_v_label.config(text=f"{self.mosaic_spacing_v.get():.1f}x")
        self.update_preview()
    
    def update_opacity_label(self):
        """Met à jour le label de l'opacité et la prévisualisation"""
        self.opacity_label.config(text=f"{self.opacity.get()}%")
        self.update_preview()
    
    def update_font_size_label(self):
        """Met à jour le label de la taille de la police et la prévisualisation"""
        self.font_size_label.config(text=f"{self.font_size_percent.get():.1f}%")
        self.update_preview()

    def update_preview(self):
        """Met à jour la prévisualisation du watermark"""
        try:
            # Effacer le canvas
            self.preview_canvas.delete("all")
            
            # Déterminer l'image à prévisualiser selon le mode
            selection_mode = self.selection_mode.get()
            
            if selection_mode == "image":
                # Mode image unique
                image_path = self.single_image_path.get()
                if not image_path or not os.path.exists(image_path):
                    self.preview_label.config(text="Sélectionnez une image pour voir la prévisualisation")
                    return
                preview_filename = os.path.basename(image_path)
            else:
                # Mode dossier
                folder = self.folder_path.get()
                if not folder:
                    self.preview_label.config(text="Sélectionnez un dossier pour voir la prévisualisation")
                    return
                
                # Chercher la première image dans le dossier
                output_basename = self.output_basename.get().strip() or "image"
                image_files = [f for f in os.listdir(folder) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
                             and not f.startswith(output_basename)]
                
                if not image_files:
                    self.preview_label.config(text="Aucune image trouvée dans le dossier")
                    return
                
                image_path = os.path.join(folder, image_files[0])
                preview_filename = image_files[0]
            
            img = Image.open(image_path)
            
            # Redimensionner l'image pour la prévisualisation
            canvas_width = 400
            canvas_height = 300
            img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            
            # Créer un calque pour le watermark
            watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark)
            
            # Obtenir les paramètres actuels
            text = f"{self.copyright_symbol.get()} {self.copyright_text.get()}"
            opacity = self.opacity.get() / 100
            position = self.get_position_internal()
            is_mosaic = self.mosaic_mode.get()
            font_size_percent = self.font_size_percent.get() / 100
            
            # Calculer la taille de la police
            font_size = int(img.size[0] * font_size_percent)
            font_name = self.selected_font.get()
            is_bold = self.is_bold.get()
            try:
                font_path = self.get_font_path(font_name, is_bold)
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            
            # Obtenir les dimensions du texte
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            if is_mosaic:
                # Calculer la taille après rotation (-15°)
                angle_rad = math.radians(15)
                rotated_width = abs(text_width * math.cos(angle_rad)) + abs(text_height * math.sin(angle_rad))
                rotated_height = abs(text_width * math.sin(angle_rad)) + abs(text_height * math.cos(angle_rad))
                
                # Espacement directement basé sur les sliders utilisateur
                spacing_factor_h = self.mosaic_spacing_h.get()
                spacing_factor_v = self.mosaic_spacing_v.get()
                spacing_x = rotated_width * spacing_factor_h
                spacing_y = rotated_height * spacing_factor_v
                
                # Calculer le nombre de watermarks nécessaires pour couvrir l'image
                num_horizontal = max(1, int(img.size[0] / spacing_x) + 2)
                num_vertical = max(1, int(img.size[1] / spacing_y) + 2)
                
                for i in range(num_horizontal):
                    for j in range(num_vertical):
                        x = i * spacing_x
                        y = j * spacing_y
                        
                        # Décalage alterné pour les lignes impaires
                        if j % 2 == 1:
                            x += spacing_x / 2
                        
                        # Créer une image temporaire pour la rotation
                        temp_size = int(max(text_width, text_height) * 1.5)
                        txt_img = Image.new('RGBA', (temp_size, temp_size), (0, 0, 0, 0))
                        txt_draw = ImageDraw.Draw(txt_img)
                        
                        text_pos = (temp_size/2 - text_width/2, temp_size/2 - text_height/2)
                        text_fill = (*self.hex_to_rgb(self.color), int(255 * opacity))
                        if is_bold and self.needs_fake_bold(font_name):
                            self.draw_text_with_fake_bold(txt_draw, text_pos, text, font, text_fill)
                        else:
                            txt_draw.text(text_pos, text, font=font, fill=text_fill)
                        
                        # Rotation de -15 degrés
                        txt_img = txt_img.rotate(-15, expand=True, resample=Image.BICUBIC)
                        
                        paste_x = int(x - txt_img.size[0]/2)
                        paste_y = int(y - txt_img.size[1]/2)
                        
                        if (paste_x + txt_img.size[0] > 0 and 
                            paste_x < img.size[0] and 
                            paste_y + txt_img.size[1] > 0 and 
                            paste_y < img.size[1]):
                            watermark.paste(txt_img, (paste_x, paste_y), txt_img)
            else:
                # Mode normal : plusieurs watermarks selon le slider Nombre
                num_watermarks = self.num_watermarks.get()
                
                for i in range(num_watermarks):
                    # Calculer la position pour chaque watermark
                    if position == "top-left":
                        pos = (10, 10 + i * (text_height + 10))
                    elif position == "top-right":
                        pos = (img.size[0] - text_width - 10, 10 + i * (text_height + 10))
                    elif position == "bottom-left":
                        pos = (10, img.size[1] - (num_watermarks - i) * (text_height + 10))
                    elif position == "bottom-right":
                        pos = (img.size[0] - text_width - 10, 
                             img.size[1] - (num_watermarks - i) * (text_height + 10))
                    else:  # center
                        pos = ((img.size[0] - text_width) // 2, 
                             ((img.size[1] - (num_watermarks * text_height)) // 2) + 
                             i * (text_height + 10))
                    
                    # Dessiner le watermark (avec faux gras si nécessaire)
                    text_fill = (*self.hex_to_rgb(self.color), int(255 * opacity))
                    if is_bold and self.needs_fake_bold(font_name):
                        self.draw_text_with_fake_bold(draw, pos, text, font, text_fill)
                    else:
                        draw.text(pos, text, font=font, fill=text_fill)
            
            # Fusionner les images
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img = Image.alpha_composite(img, watermark)
            img = img.convert('RGB')
            
            # Convertir en PhotoImage pour l'affichage
            self.preview_image = ImageTk.PhotoImage(img)
            
            # Afficher l'image
            self.preview_canvas.create_image(
                canvas_width//2, canvas_height//2,
                image=self.preview_image,
                anchor="center"
            )
            
            # Mettre à jour le label
            self.preview_label.config(
                text=f"Prévisualisation sur: {preview_filename}"
            )
            
        except Exception as e:
            self.preview_label.config(
                text=f"Erreur de prévisualisation: {str(e)}"
            )

    def _on_mousewheel(self, event):
        """Gère le défilement avec la molette de la souris"""
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

if __name__ == "__main__":
    try:
        # Vérifier la version de Windows
        if sys.platform != 'win32':
            show_error_and_exit("Erreur système", 
                              "Cette application nécessite Windows")
            sys.exit(1)
        
        # Créer la fenêtre principale avec gestion d'erreur
        try:
            root = tk.Tk()
            app = WatermarkApp(root)
            root.mainloop()
        except Exception as e:
            show_error_and_exit("Erreur critique", 
                              f"Erreur lors du démarrage de l'application:\n{str(e)}")
            
    except Exception as e:
        show_error_and_exit("Erreur fatale", 
                          f"Une erreur critique s'est produite:\n{str(e)}")
        sys.exit(1) 