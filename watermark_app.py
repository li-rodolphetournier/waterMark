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
            self.copyright_text = tk.StringVar(value="Certification de la qualité")
            self.signature_text = tk.StringVar(value="")  # Nouvelle variable pour la signature
            self.opacity = tk.IntVar(value=50)
            self.position = tk.StringVar(value="bottom-right")
            self.num_watermarks = tk.IntVar(value=1)
            self.mosaic_mode = tk.BooleanVar(value=False)
            self.font_size_percent = tk.DoubleVar(value=5.0)
            self.copyright_symbol = tk.StringVar(value="©")
            
            # Nouvelles variables pour le style de texte
            self.is_bold = tk.BooleanVar(value=False)
            self.selected_font = tk.StringVar(value="Arial")
            
            # Liste des symboles de copyright disponibles
            self.copyright_symbols = ["©", "®", "™", "(c)", "All Rights Reserved"]
            
            # Charger les polices disponibles
            self.available_fonts = self.get_available_fonts()
            
            self.create_widgets()
            
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
        fonts = ["Arial", "Comic Sans MS"]  # Polices par défaut
        fonts_dir = os.path.join(os.environ["WINDIR"], "Fonts")
        
        # Ajouter les polices courantes
        common_fonts = [
            "Arial", "Times New Roman", "Verdana", "Calibri", 
            "Georgia", "Tahoma", "Trebuchet MS", "Comic Sans MS"
        ]
        
        # Vérifier les polices système
        for font in common_fonts:
            ttf_path = os.path.join(fonts_dir, f"{font}.ttf")
            if os.path.exists(ttf_path):
                if font not in fonts:
                    fonts.append(font)
        
        return sorted(fonts)
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Section Sélection du dossier
        folder_frame = ttk.LabelFrame(main_frame, text="Sélection du dossier", 
                                    style="Section.TLabelframe")
        folder_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=70).pack(side="left", 
                                                                             padx=5, pady=5)
        ttk.Button(folder_frame, text="Parcourir", 
                  command=self.browse_folder).pack(side="left", padx=5, pady=5)
        
        # Section Copyright
        copyright_frame = ttk.LabelFrame(main_frame, text="Options du Copyright", 
                                       style="Section.TLabelframe")
        copyright_frame.pack(fill="x", pady=(0, 10))
        
        # Grille pour les options de copyright
        copyright_grid = ttk.Frame(copyright_frame)
        copyright_grid.pack(fill="x", padx=5, pady=5)
        
        # Première ligne - Copyright
        ttk.Label(copyright_grid, text="Symbole:").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Combobox(copyright_grid, textvariable=self.copyright_symbol, 
                    values=self.copyright_symbols, width=10).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Label(copyright_grid, text="Texte:").grid(row=0, column=2, sticky="w", padx=5)
        ttk.Entry(copyright_grid, textvariable=self.copyright_text, 
                 width=40).grid(row=0, column=3, sticky="ew", padx=5)

        # Deuxième ligne - Signature
        ttk.Label(copyright_grid, text="Signature:").grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(10,0))
        ttk.Entry(copyright_grid, textvariable=self.signature_text, 
                 width=40).grid(row=1, column=2, columnspan=2, sticky="ew", padx=5, pady=(10,0))

        # Troisième ligne - Nombre et Mode mosaïque
        ttk.Label(copyright_grid, text="Nombre:").grid(row=2, column=0, sticky="w", padx=5, pady=10)
        num_frame = ttk.Frame(copyright_grid)
        num_frame.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5)
        
        num_scale = ttk.Scale(num_frame, from_=1, to=10, variable=self.num_watermarks, 
                            orient="horizontal", command=lambda v: self.update_num_label())
        num_scale.pack(side="left", fill="x", expand=True)
        self.num_label = ttk.Label(num_frame, text="1")
        self.num_label.pack(side="right", padx=5)

        ttk.Checkbutton(copyright_grid, text="Mode mosaïque", 
                       variable=self.mosaic_mode).grid(row=2, column=3, sticky="w", padx=5)
        
        # Section Style de Texte (nouvelle section)
        text_style_frame = ttk.LabelFrame(main_frame, text="Style de Texte", 
                                        style="Section.TLabelframe")
        text_style_frame.pack(fill="x", pady=(0, 10))
        
        text_style_grid = ttk.Frame(text_style_frame)
        text_style_grid.pack(fill="x", padx=5, pady=5)
        
        # Police de caractères
        ttk.Label(text_style_grid, text="Police:").grid(row=0, column=0, sticky="w", padx=5)
        font_combo = ttk.Combobox(text_style_grid, textvariable=self.selected_font,
                                values=self.available_fonts, width=30)
        font_combo.grid(row=0, column=1, sticky="ew", padx=5)
        
        # Option Gras
        ttk.Checkbutton(text_style_grid, text="Texte en gras",
                       variable=self.is_bold).grid(row=0, column=2, sticky="w", padx=20)
        
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
        positions = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]
        ttk.Combobox(appearance_grid, textvariable=self.position, 
                    values=positions).grid(row=0, column=2, sticky="ew", padx=5)
        
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
        folder = self.folder_path.get()
        if not folder:
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier")
            return
            
        try:
            # Obtenir le chemin de la police sélectionnée
            font_name = self.selected_font.get()
            is_bold = self.is_bold.get()
            
            # Construire le nom du fichier de police
            font_filename = font_name
            if is_bold and font_name != "Juice":  # Ne pas ajouter Bold pour Juice
                font_filename += " Bold"
            font_filename += ".ttf"
            
            # Chercher d'abord dans les polices personnalisées
            custom_font_path = get_resource_path(os.path.join("fonts", font_filename))
            if os.path.exists(custom_font_path):
                font_path = custom_font_path
            else:
                # Sinon chercher dans les polices système
                font_path = os.path.join(os.environ["WINDIR"], "Fonts", font_filename)
                if not os.path.exists(font_path):
                    # Fallback sur Arial si la police n'est pas trouvée
                    font_path = os.path.join(os.environ["WINDIR"], "Fonts", "arial.ttf")
            
            text = f"{self.copyright_symbol.get()} {self.copyright_text.get()}"
            opacity = self.opacity.get() / 100
            position = self.position.get()
            num_watermarks = self.num_watermarks.get()
            is_mosaic = self.mosaic_mode.get()
            font_size_percent = self.font_size_percent.get() / 100
            
            # Préparer les métadonnées détaillées
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
                "application": "Certification de propriété et de droits",
                "version": "1.0"
            }
            
            # Convertir en bytes pour EXIF
            watermark_bytes = json.dumps(watermark_info).encode('utf-8')
            
            # Filtrer pour exclure les images déjà watermarkées
            image_files = [f for f in os.listdir(folder) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
                         and not f.startswith('watermarked_')]
            total_images = len(image_files)
            
            if total_images == 0:
                messagebox.showwarning("Attention", 
                                     "Aucune image trouvée dans le dossier sélectionné ou toutes les images ont déjà été watermarkées")
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
                for index, filename in enumerate(image_files):
                    try:
                        progress_bar['value'] = (index + 1) / total_images * 100
                        progress_label['text'] = f"Traitement de {filename}..."
                        progress_window.update()
                        
                        image_path = os.path.join(folder, filename)
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
                            # Calculer la taille du watermark avec une marge
                            margin = 1.5  # Facteur de marge pour éviter les chevauchements
                            watermark_width = int(text_width * margin)
                            watermark_height = int(text_height * margin)
                            
                            # Calculer le nombre de watermarks nécessaires
                            num_horizontal = max(1, img.size[0] // watermark_width)
                            num_vertical = max(1, img.size[1] // watermark_height)
                            
                            # Calculer l'espacement
                            spacing_x = img.size[0] / num_horizontal
                            spacing_y = img.size[1] / num_vertical
                            
                            # Créer le motif de mosaïque
                            for i in range(num_horizontal):
                                for j in range(num_vertical):
                                    # Calculer la position avec décalage pour les lignes paires
                                    x = i * spacing_x
                                    y = j * spacing_y
                                    
                                    if j % 2 == 0:
                                        x += spacing_x / 2
                                    
                                    # Créer une image temporaire pour la rotation
                                    temp_size = int(max(text_width, text_height) * 1.5)
                                    txt_img = Image.new('RGBA', (temp_size, temp_size), (0, 0, 0, 0))
                                    txt_draw = ImageDraw.Draw(txt_img)
                                    
                                    # Dessiner le texte au centre
                                    txt_draw.text(
                                        (temp_size/2 - text_width/2, temp_size/2 - text_height/2),
                                        text,
                                        font=font,
                                        fill=(*self.hex_to_rgb(self.color), int(255 * opacity))
                                    )
                                    
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
                                
                                draw.text(pos, text, font=font, 
                                        fill=(*self.hex_to_rgb(self.color), int(255 * opacity)))
                                
                                # Ajouter la signature si elle existe
                                signature = self.signature_text.get().strip()
                                if signature:
                                    # Calculer la taille de la signature
                                    signature_bbox = draw.textbbox((0, 0), signature, font=font)
                                    signature_width = signature_bbox[2] - signature_bbox[0]
                                    signature_height = signature_bbox[3] - signature_bbox[1]
                                    
                                    # Positionner la signature juste en dessous du copyright
                                    sig_pos = (pos[0], pos[1] + text_height + 5)
                                    
                                    # Ajuster la position horizontale si nécessaire
                                    if position.endswith("right"):
                                        sig_pos = (img.size[0] - signature_width - 10, sig_pos[1])
                                    elif position == "center":
                                        sig_pos = ((img.size[0] - signature_width) // 2, sig_pos[1])
                                    
                                    draw.text(sig_pos, signature, font=font,
                                            fill=(*self.hex_to_rgb(self.color), int(255 * opacity)))
                            
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
                            
                            # Sauvegarder l'image avec les métadonnées
                            output_path = os.path.join(folder, f"watermarked_{filename}")
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

                                # Ajouter nos métadonnées personnalisées
                                exif_dict["Exif"][piexif.ExifIFD.UserComment] = watermark_bytes
                                
                                # Ajouter le copyright et la signature dans les champs standards
                                copyright_text = text
                                if self.signature_text.get().strip():
                                    copyright_text += " - " + self.signature_text.get().strip()
                                exif_dict["0th"][piexif.ImageIFD.Copyright] = copyright_text.encode('utf-8')
                                
                                # Ajouter l'auteur si une signature est présente
                                if self.signature_text.get().strip():
                                    exif_dict["0th"][piexif.ImageIFD.Artist] = self.signature_text.get().strip().encode('utf-8')
                                else:
                                    exif_dict["0th"][piexif.ImageIFD.Artist] = "CestMonImage User".encode('utf-8')
                                
                                # Ajouter la date et le logiciel
                                exif_dict["0th"][piexif.ImageIFD.Software] = "CestMonImage".encode('utf-8')
                                exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = \
                                    datetime.now().strftime("%Y:%m:%d %H:%M:%S").encode('utf-8')
                                
                                # Ajouter un identifiant unique pour la signature
                                signature_id = f"CMI-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                                if self.signature_text.get().strip():
                                    signature_id += f"-{self.signature_text.get().strip()}"
                                exif_dict["0th"][piexif.ImageIFD.ImageDescription] = signature_id.encode('utf-8')
                                
                                # Ajouter des commentaires supplémentaires
                                exif_dict["0th"][piexif.ImageIFD.XPComment] = signature_id.encode('utf-16le')
                                exif_dict["0th"][piexif.ImageIFD.DocumentName] = \
                                    f"Watermarked_{filename}".encode('utf-8')
                                
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
                                output_path = os.path.join(folder, f"watermarked_{filename}")
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

    def update_num_label(self):
        """Met à jour le label du nombre de watermarks"""
        self.num_label.config(text=str(self.num_watermarks.get()))
    
    def update_opacity_label(self):
        """Met à jour le label de l'opacité"""
        self.opacity_label.config(text=f"{self.opacity.get()}%")
    
    def update_font_size_label(self):
        """Met à jour le label de la taille de la police"""
        self.font_size_label.config(text=f"{self.font_size_percent.get():.1f}%")

    def update_preview(self):
        """Met à jour la prévisualisation du watermark"""
        try:
            # Effacer le canvas
            self.preview_canvas.delete("all")
            
            # Vérifier si un dossier est sélectionné
            folder = self.folder_path.get()
            if not folder:
                self.preview_label.config(text="Sélectionnez un dossier pour voir la prévisualisation")
                return
            
            # Chercher la première image dans le dossier
            image_files = [f for f in os.listdir(folder) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))
                         and not f.startswith('watermarked_')]
            
            if not image_files:
                self.preview_label.config(text="Aucune image trouvée dans le dossier")
                return
            
            # Ouvrir la première image
            image_path = os.path.join(folder, image_files[0])
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
            position = self.position.get()
            is_mosaic = self.mosaic_mode.get()
            font_size_percent = self.font_size_percent.get() / 100
            
            # Calculer la taille de la police
            font_size = int(img.size[0] * font_size_percent)
            try:
                font_name = self.selected_font.get()
                font_filename = font_name
                if self.is_bold.get():
                    font_filename += " Bold"
                font_filename += ".ttf"
                
                font_path = os.path.join(os.environ["WINDIR"], "Fonts", font_filename)
                if not os.path.exists(font_path):
                    font_path = os.path.join(os.environ["WINDIR"], "Fonts", "arial.ttf")
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
            
            # Obtenir les dimensions du texte
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Calculer la position
            if position == "top-left":
                pos = (10, 10)
            elif position == "top-right":
                pos = (img.size[0] - text_width - 10, 10)
            elif position == "bottom-left":
                pos = (10, img.size[1] - text_height - 10)
            elif position == "bottom-right":
                pos = (img.size[0] - text_width - 10, img.size[1] - text_height - 10)
            else:  # center
                pos = ((img.size[0] - text_width) // 2, (img.size[1] - text_height) // 2)
            
            # Dessiner le watermark
            draw.text(pos, text, font=font, fill=(*self.hex_to_rgb(self.color), int(255 * opacity)))
            
            # Ajouter la signature si elle existe
            signature = self.signature_text.get().strip()
            if signature:
                sig_bbox = draw.textbbox((0, 0), signature, font=font)
                sig_width = sig_bbox[2] - sig_bbox[0]
                sig_height = sig_bbox[3] - sig_bbox[1]
                
                sig_pos = (pos[0], pos[1] + text_height + 5)
                if position.endswith("right"):
                    sig_pos = (img.size[0] - sig_width - 10, sig_pos[1])
                elif position == "center":
                    sig_pos = ((img.size[0] - sig_width) // 2, sig_pos[1])
                
                draw.text(sig_pos, signature, font=font,
                         fill=(*self.hex_to_rgb(self.color), int(255 * opacity)))
            
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
                text=f"Prévisualisation sur: {image_files[0]}"
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