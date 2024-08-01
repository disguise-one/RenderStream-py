import os
import urllib.request
import zipfile
from pathlib import Path
from OpenGL import __path__ as pyopengl_path

freeglut_url = "https://www.transmissionzero.co.uk/files/software/development/GLUT/freeglut-MSVC.zip"

# Determine the installation folder for PyOpenGL
install_folder = Path(pyopengl_path[0]).parent
freeglut_dll_target = install_folder / 'OpenGL' / 'DLLs' / 'freeglut64.vc14.dll'

if not freeglut_dll_target.exists():
    print("Fixing OpenGL...")

    temp_dir = os.environ.get('TEMP', '/tmp')
    freeglut_zip = os.path.join(temp_dir, 'freeglut.zip')
    freeglut_dll_source = 'freeglut/bin/x64/freeglut.dll'

    # Download the FreeGlut ZIP file
    urllib.request.urlretrieve(freeglut_url, freeglut_zip)

    # Ensure the target directory exists
    target_dll_folder = freeglut_dll_target.parent
    target_dll_folder.mkdir(parents=True, exist_ok=True)

    # Extract the DLL file from the ZIP
    with zipfile.ZipFile(freeglut_zip, 'r') as zip_ref:
        if freeglut_dll_source in zip_ref.namelist():
            source_dll_path = zip_ref.extract(freeglut_dll_source, temp_dir)
            Path(source_dll_path).replace(freeglut_dll_target)
        else:
            print(f"Error: {freeglut_dll_source} not found in the ZIP archive.")
