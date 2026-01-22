#!/usr/bin/env python3
"""
Script pour corriger les chemins des images dans la base de données.
"""
import sys
from pathlib import Path
import json

# Ajouter le répertoire racine au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.image_manager import ImageManager
from core.image_db import ImageMetadata

def fix_image_paths():
    """Corrige les chemins des images dans la base de données."""
    image_manager = ImageManager()
    images_dir = Path("data/images")
    
    if not images_dir.exists():
        print("Le dossier data/images n'existe pas.")
        return
    
    # Lister toutes les images physiques
    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.jpeg"))
    print(f"Trouvé {len(image_files)} images dans data/images")
    
    # Créer un mapping des noms de fichiers vers les chemins
    file_mapping = {}
    for img_path in image_files:
        file_mapping[img_path.name] = img_path
    
    # Parcourir toutes les entrées de la base de données
    all_images = image_manager.db.list_images()
    print(f"Trouvé {len(all_images)} entrées dans la base de données")
    
    updated_count = 0
    not_found_count = 0
    
    for metadata in all_images:
        # Vérifier si l'image existe dans data/images
        if metadata.original_filename in file_mapping:
            # Mettre à jour le chemin
            new_path = file_mapping[metadata.original_filename]
            metadata.original_path = str(new_path)
            metadata.path = metadata.original_filename  # Utiliser le nom original
            
            # Mettre à jour dans la base de données
            image_manager.db.update_image(metadata.id, 
                                        original_path=metadata.original_path,
                                        path=metadata.path)
            print(f"Corrigé: {metadata.original_filename}")
            updated_count += 1
        else:
            print(f"Non trouvé: {metadata.original_filename}")
            not_found_count += 1
    
    print(f"\nCorrection terminée:")
    print(f"- {updated_count} chemins corrigés")
    print(f"- {not_found_count} images non trouvées")

if __name__ == "__main__":
    fix_image_paths() 