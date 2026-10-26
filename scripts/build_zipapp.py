"""Build a dependency-free download from only the public tool package."""
from pathlib import Path
import shutil
import tempfile
import zipapp


def build():
    root = Path(__file__).resolve().parents[1]
    package = root / "tgden_tools"
    if not (package / "__main__.py").is_file():
        raise RuntimeError("The runnable tool package is missing.")
    output = root / "dist" / "tgden-tools.pyz"
    output.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        staging = Path(temporary)
        shutil.copytree(package, staging / "tgden_tools", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        shutil.copy2(root / "LICENSE", staging / "LICENSE")
        (staging / "__main__.py").write_text("from tgden_tools.__main__ import main\nraise SystemExit(main())\n")
        zipapp.create_archive(staging, output, interpreter="/usr/bin/env python3", compressed=True)
    print(output)
    return output


if __name__ == "__main__":
    build()
