import PyInstaller.__main__
import os
import sys
import shutil
import tempfile
import ctypes
from pathlib import Path
import time
import psutil
import winshell
from win32com.client import Dispatch
import subprocess

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def is_process_running(process_name):
    """Vérifie si un processus est en cours d'exécution"""
    for proc in psutil.process_iter(['name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def wait_for_file_access(file_path, timeout=10):
    """Attend que le fichier soit accessible"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'a+b'):
                    return True
            return True
        except PermissionError:
            time.sleep(0.5)
    return False

def safe_remove_file(file_path):
    """Supprime un fichier en gérant les erreurs de permission"""
    if not os.path.exists(file_path):
        return True
    
    try:
        if is_process_running("CestMonImage.exe"):
            print("L'application est en cours d'exécution. Veuillez la fermer d'abord.")
            return False
        
        # Attendre que le fichier soit accessible
        if not wait_for_file_access(file_path):
            print(f"Impossible d'accéder au fichier: {file_path}")
            return False
        
        os.remove(file_path)
        return True
    except Exception as e:
        print(f"Erreur lors de la suppression de {file_path}: {str(e)}")
        return False

def create_installation_directory():
    """Crée le dossier d'installation dans Documents"""
    try:
        # Utiliser le dossier Documents
        documents_path = os.path.expanduser("~\\Documents")
        install_dir = os.path.join(documents_path, "CestMonImage")
        
        # Créer le dossier s'il n'existe pas
        os.makedirs(install_dir, exist_ok=True)
        
        # Vérifier si l'ancien exécutable existe et le supprimer
        old_exe = os.path.join(install_dir, "CestMonImage.exe")
        if os.path.exists(old_exe):
            if not safe_remove_file(old_exe):
                raise Exception("Impossible de supprimer l'ancienne version. Veuillez fermer l'application si elle est en cours d'exécution.")
        
        # Tester les permissions en écrivant un fichier test
        test_file = os.path.join(install_dir, "test_permissions.txt")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except Exception as e:
            raise Exception(f"Impossible d'écrire dans le dossier d'installation: {str(e)}")
        
        return install_dir
    except Exception as e:
        raise Exception(f"Erreur lors de la création du dossier d'installation: {str(e)}")

def create_temp_workspace():
    """Crée un espace de travail temporaire"""
    try:
        temp_dir = tempfile.mkdtemp(prefix='watermark_build_')
        
        # Copier les fichiers nécessaires
        files_to_copy = ['watermark_app.py', 'version_info.txt']
        for file in files_to_copy:
            if os.path.exists(file):
                shutil.copy2(file, temp_dir)
        
        # Créer le dossier fonts
        fonts_dir = os.path.join(temp_dir, 'fonts')
        os.makedirs(fonts_dir, exist_ok=True)
        
        # Copier la police Arial
        arial_path = "C:\\Windows\\Fonts\\arial.ttf"
        if os.path.exists(arial_path):
            shutil.copy2(arial_path, os.path.join(fonts_dir, "arial.ttf"))
        
        return temp_dir
    except Exception as e:
        raise Exception(f"Erreur lors de la création de l'espace temporaire: {str(e)}")

def create_shortcut(target_path, shortcut_path):
    try:
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.save()
    except Exception as e:
        print(f"Erreur lors de la création du raccourci : {e}")

def clean_directory(dir_path):
    """Nettoie un répertoire s'il existe"""
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            time.sleep(1)  # Attendre que le système libère les ressources
        except Exception as e:
            print(f"Attention: Impossible de supprimer le dossier {dir_path}: {e}")
            return False
    return True

def clean_build():
    """Nettoie les dossiers de build"""
    for dir_to_clean in ['build', 'dist', 'exe_final']:
        if os.path.exists(dir_to_clean):
            try:
                shutil.rmtree(dir_to_clean)
                time.sleep(2)  # Attendre plus longtemps
            except Exception as e:
                print(f"Attention: Impossible de supprimer {dir_to_clean}: {e}")

def build_exe():
    """Crée l'exécutable avec PyInstaller"""
    try:
        # Nettoyage initial
        clean_build()
        
        # Créer les dossiers nécessaires
        os.makedirs('exe_final', exist_ok=True)
        os.makedirs('fonts', exist_ok=True)
        
        time.sleep(2)  # Attendre que les dossiers soient créés
        
        # Utiliser subprocess pour exécuter PyInstaller
        cmd = [
            'pyinstaller',
            '--name=Application_Copyright_Images',
            '--onefile',
            '--noconsole',
            '--clean',
            '--distpath=exe_final',
            '--add-data=fonts;fonts',
            'watermark_app.py'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Erreur lors de l'exécution de PyInstaller:")
            print(result.stderr)
            return False
        
        # Vérifier si l'exécutable a été créé
        exe_path = os.path.join('exe_final', 'Application_Copyright_Images.exe')
        if os.path.exists(exe_path):
            print(f"\nL'exécutable a été créé avec succès: {exe_path}")
            
            # Copier le dossier fonts
            fonts_dest = os.path.join('exe_final', 'fonts')
            if os.path.exists('fonts'):
                if os.path.exists(fonts_dest):
                    shutil.rmtree(fonts_dest)
                time.sleep(1)
                shutil.copytree('fonts', fonts_dest)
            
            return True
        else:
            print("\nErreur: L'exécutable n'a pas été créé")
            return False
            
    except Exception as e:
        print(f"\nErreur lors de la création de l'exécutable: {str(e)}")
        return False

def main():
    # Nettoyage des anciens fichiers
    for dir_to_clean in ['build', 'dist']:
        if os.path.exists(dir_to_clean):
            try:
                shutil.rmtree(dir_to_clean)
                print(f"Nettoyage du dossier {dir_to_clean}")
            except Exception as e:
                print(f"Erreur lors du nettoyage de {dir_to_clean}: {e}")

    # Création du dossier dist dans le projet
    dist_dir = os.path.join(os.getcwd(), "dist")
    os.makedirs(dist_dir, exist_ok=True)
    print(f"Dossier de distribution créé: {dist_dir}")

    try:
        # Vérifier si le dossier fonts existe
        fonts_dir = os.path.join(os.getcwd(), "fonts")
        if not os.path.exists(fonts_dir):
            os.makedirs(fonts_dir)
            print("Dossier fonts créé")

        # Configuration de PyInstaller
        PyInstaller.__main__.run([
            'watermark_app.py',
            '--name=Application_Copyright_Images',
            '--onefile',
            '--windowed',
            '--icon=fonts/copyright.ico',  # Assurez-vous d'avoir une icône dans ce chemin
            '--add-data=fonts;fonts',  # Inclure le dossier fonts
            '--clean',
            '--distpath=exe_final'
        ])

        # Vérification de l'exécutable
        exe_path = os.path.join(dist_dir, "CestMonImage.exe")
        if os.path.exists(exe_path):
            # Création du raccourci sur le bureau
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "CestMonImage.lnk")
            create_shortcut(exe_path, shortcut_path)
            print("\nInstallation terminée avec succès!")
            print(f"L'exécutable se trouve dans: {exe_path}")
            print("Un raccourci a été créé sur le bureau.")

            # Copier le dossier fonts dans le dossier exe_final
            if os.path.exists('fonts'):
                shutil.copytree('fonts', 'exe_final/fonts')

            print("L'exécutable a été créé avec succès dans le dossier 'exe_final'")
        else:
            raise FileNotFoundError(f"L'exécutable n'a pas été créé: {exe_path}")

    except Exception as e:
        print(f"Erreur lors de l'installation: {e}")

    input("\nAppuyez sur Entrée pour quitter...")

if __name__ == "__main__":
    if not is_admin():
        print("Relancement avec les droits administrateur...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    else:
        try:
            if build_exe():
                print("Build terminé avec succès!")
            else:
                print("Le build a échoué.")
                sys.exit(1)
        except Exception as e:
            print(f"Erreur critique: {str(e)}")
            sys.exit(1) 