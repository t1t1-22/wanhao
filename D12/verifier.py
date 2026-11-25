"""Contrôles du fichier obtenu pour la zone application du STM32F407."""
from pathlib import Path
import hashlib
import struct
import sys

image = Path(sys.argv[1]).read_bytes()
base = 0x0800C000
if not 8 < len(image) <= 512 * 1024 - 48 * 1024:
    sys.exit("Taille incompatible avec la limite de 512 Kio retenue.")
sp, reset = struct.unpack_from("<II", image)
if not (0x20000000 < sp <= 0x20020000 and sp % 4 == 0):
    sys.exit("Pile initiale invalide.")
if not (reset & 1 and base <= (reset & ~1) < base + len(image)):
    sys.exit("Vecteur de démarrage invalide.")
if b"2.1.2.1 D12-P1" not in image or b"Baby Z: %s mm" not in image:
    sys.exit("Identifiant ou affichage babystep absent.")
print("SHA-256", hashlib.sha256(image).hexdigest())
