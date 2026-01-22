#!/usr/bin/env python3
"""
Script pour importer toutes les images existantes du dossier utilisateur dans la base de données.
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from PIL import Image

def import_existing_images():
    """Importe toutes les images existantes dans la base de données."""
    from core.user_data import user_data
    image_manager = ImageManager()
    images_dir = user_data.get_images_dir()
    
    if not images_dir.exists():
        print(f"Le dossier {images_dir} n'existe pas.")
        return
    
    # Lister toutes les images
    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg"))
    
    print(f"Trouvé {len(image_files)} images à importer...")
    
    imported_count = 0
    skipped_count = 0
    
    for image_path in image_files:
        try:
            # Vérifier si l'image existe déjà dans la base de données
            existing_images = image_manager.db.list_images()
            already_exists = False
            
            for existing in existing_images:
                if existing.original_path and Path(existing.original_path) == image_path:
                    already_exists = True
                    break
            
            if already_exists:
                print(f"Déjà importée: {image_path.name}")
                skipped_count += 1
                continue
            
            # Ouvrir l'image pour obtenir les métadonnées
            with Image.open(image_path) as img:
                # Créer un nom de fichier unique
                dest_filename = f"{image_path.stem}_{image_path.suffix.lower()}"
                
                # Créer les métadonnées
                metadata = ImageMetadata(
                    id=image_path.stem,
                    path=dest_filename,
                    original_filename=image_path.name,
                    width=img.width,
                    height=img.height,
                    file_size=image_path.stat().st_size,
                    format=img.format or "PNG",
                    original_path=str(image_path)
                )
                
                # Ajouter à la base de données
                if image_manager.db.add_image(metadata):
                    print(f"Importée: {image_path.name}")
                    imported_count += 1
                else:
                    print(f"Échec: {image_path.name}")
                    skipped_count += 1
                    
        except Exception as e:
            print(f"Erreur avec {image_path.name}: {e}")
            skipped_count += 1
    
    print(f"\nImport terminé:")
    print(f"- {imported_count} images importées")
    print(f"- {skipped_count} images ignorées")

if __name__ == "__main__":
    import_existing_images() 