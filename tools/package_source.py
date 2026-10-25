"""Create a portable source-only hand-in, excluding local accounts and secrets."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / 'artifacts' / 'Fridgewise-source.zip'
ROOT_FILES = ['.gitignore', '.env.example', 'README.md', 'requirements.txt', 'manage.py', 'setup.ps1', 'start.ps1', 'start-gmail.ps1']
SOURCE_DIRS = ['fridgewise', 'kitchen', 'templates', 'static', 'docs', 'tools']

def main():
    files = [ROOT / name for name in ROOT_FILES]
    for directory in SOURCE_DIRS:
        files.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'})
    DESTINATION.parent.mkdir(exist_ok=True)
    with ZipFile(DESTINATION, 'w', ZIP_DEFLATED) as archive:
        for source in sorted(files):
            archive.write(source, Path('Fridgewise') / source.relative_to(ROOT))
    print(f'Packaged {len(files)} source files: {DESTINATION}')

if __name__ == '__main__':
    main()
