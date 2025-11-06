## Application de Copyright d'Images

Application Windows permettant d'ajouter facilement un ou plusieurs filigranes (copyright) sur des images, avec personnalisation avancée et traitement par lot.

### Aperçu

![Aperçu interface 1](Capture d’écran 2025-05-26 182531.png)

![Aperçu interface 2](Capture d’écran 2025-05-26 183517.png)

## Fonctionnalités principales

- **Sélection de dossier**: choisissez un dossier d'images à traiter
- **Texte et symbole**: personnalisez le texte et le symbole (©, ®, ™, etc.)
- **Style du texte**: couleur, opacité, police (dont Arial embarquée), gras, taille relative (%)
- **Positionnement**: coins, centre, ou **mode mosaïque** pour couvrir toute l'image
- **Multiples filigranes**: jusqu'à 10 filigranes en mode normal
- **Traitement par lot**: applique le filigrane à toutes les images du dossier
- **Formats supportés**: PNG, JPG, JPEG, BMP, GIF
- **Métadonnées EXIF (JPEG)**: écriture d'informations (copyright, signature, date)
- **Prévisualisation**: rendu en direct avant application

## Prérequis

- Windows 10/11
- Python 3.11 recommandé

## Installation (développement)

1) Créez un environnement virtuel (recommandé)

```bash
python -m venv .venv
.venv\\Scripts\\activate
```

2) Installez les dépendances

```bash
pip install -r requirements.txt
```

## Lancer l'application

```bash
python watermark_app.py
```

Etapes dans l'UI:
- Cliquez sur « Parcourir » pour sélectionner le dossier
- Réglez symbole, texte, police, couleur, opacité, taille (%)
- Choisissez la position ou activez le mode mosaïque
- Optionnel: ajoutez une signature (champ dédié)
- Cliquez sur « Appliquer le copyright »

Les nouvelles images sont sauvegardées dans le même dossier avec le préfixe `watermarked_`.

## Build de l'exécutable Windows

Deux options sont fournies:

- **Commande PyInstaller rapide**:

```bash
pyinstaller --name=Application_Copyright_Images --onefile --noconsole --clean --distpath=exe_final --add-data=fonts;fonts watermark_app.py
```

- **Script dédié**: `build_exe.py`

```bash
python build_exe.py
```

L'exécutable sera généré dans `exe_final/`.

## Détails techniques

- **Interface**: Tkinter/ttk
- **Traitement d'image**: Pillow (PIL)
- **EXIF**: piexif (JPEG uniquement)
- **Packaging**: PyInstaller
- **Windows Shell**: pywin32, winshell (raccourcis, intégration)
- **Processus système**: psutil

## Dépannage

- Si l'exécutable ne se génère pas, vérifiez les logs de PyInstaller et que `fonts/arial.ttf` est bien présent (copié au build). Vous pouvez aussi laisser l'application retomber sur la police système.
- Sur certaines images, la lecture/écriture EXIF peut échouer (fichiers non JPEG ou EXIF corrompu). Dans ce cas, l'application convertira en JPEG et/ou sauvegardera sans métadonnées.
- En cas d'erreur de permission sur Windows, exécutez le terminal en tant qu'administrateur pour le build.

## Contribution

1. Fork
2. Créez une branche: `git checkout -b feature/ma-fonctionnalite`
3. Commitez: `git commit -m "feat: ajoute ma fonctionnalité"`
4. Poussez: `git push origin feature/ma-fonctionnalite`
5. Ouvrez une Pull Request

## Licence

Ce projet est fourni tel quel. Ajoutez votre licence si besoin (MIT, Apache-2.0, etc.).

## Notes

- Les images originales ne sont pas modifiées; les résultats sont écrits avec le préfixe `watermarked_`.
- Le projet inclut un `.gitignore` pour exclure les artefacts de build (`build/`, `dist/`, `exe_final/`, `output/`, etc.).
