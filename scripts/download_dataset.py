
from pathlib import Path
import shutil
import kagglehub

# Project directories
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATASET = "ealaxi/paysim1"

def download_paysim():
    print("Downloading PaySim dataset from Kaggle...")

    # Download to KaggleHub's local cache
    downloaded_path = Path(
        kagglehub.dataset_download(DATASET)
    )

    print(f"Downloaded to: {downloaded_path}")

    # Find PaySim CSV files
    csv_files = list(downloaded_path.rglob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            "No CSV files found in downloaded dataset."
        )

    for source in csv_files:
        destination = DATA_DIR / source.name

        if destination.exists():
            print(f"Already exists: {destination}")
            continue

        print(f"Copying {source.name}...")
        shutil.copy2(source, destination)

        print(f"Saved to: {destination}")

    print("PaySim dataset is ready!")

if __name__ == "__main__":
    download_paysim()
