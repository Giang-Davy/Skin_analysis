import os
import subprocess
import sys


if __name__ == "__main__":
    project_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(project_dir, "test")

    if not os.path.isdir(test_dir):
        raise FileNotFoundError(f"Dossier de tests introuvable : {test_dir}")

    test_files = sorted(
        os.path.join(test_dir, name)
        for name in os.listdir(test_dir)
        if name.startswith("test") and name.endswith(".py")
    )

    print("Exécution de tous les tests...")
    print("Fichiers de tests détectés :")
    for test_file in test_files:
        print("-", os.path.basename(test_file))

    cmd = [sys.executable, "-m", "pytest", "-q"] + test_files
    display_cmd = [os.path.basename(sys.executable), "-m", "pytest", "-q"] + [
        os.path.basename(test_file) for test_file in test_files
    ]
    print("\nCommande :")
    for part in display_cmd:
        print("", part)
    result = subprocess.run(cmd, cwd=project_dir)
    sys.exit(result.returncode)
