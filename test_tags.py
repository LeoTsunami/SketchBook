#!/usr/bin/env python3
"""
Script de test pour ajouter des tags et vérifier l'autocomplétion.
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from core.image_manager import ImageManager

def add_test_tags():
    """Ajoute quelques tags de test pour vérifier l'autocomplétion."""
    image_manager = ImageManager()
    
    # Lister quelques images
    all_images = image_manager.db.list_images()
    print(f"Trouvé {len(all_images)} images dans la base de données")
    
    # Ajouter quelques tags de test
    test_tags = ["portrait", "paysage", "nature", "urbain", "art", "dessin", "peinture"]
    
    # Ajouter des tags à quelques images
    for i, metadata in enumerate(all_images[:10]):  # Premières 10 images
        if i < len(test_tags):
            tag = test_tags[i]
            print(f"Ajout du tag '{tag}' à l'image {metadata.original_filename}")
            image_manager.add_tags(metadata.id, [tag])
    
    # Afficher tous les tags disponibles
    all_tags = image_manager.get_all_tags()
    print(f"\nTags disponibles: {sorted(all_tags)}")

if __name__ == "__main__":
    add_test_tags() 