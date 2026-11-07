from pathlib import Path
import shutil
import kagglehub


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_creditcard():
    downloaded_path = Path(kagglehub.dataset_download("mlg-ulb/creditcardfraud"))
    csv_files = list(downloaded_path.rglob("creditcard.csv"))
    if not csv_files:
        raise FileNotFoundError("creditcard.csv was not found in the Kaggle dataset.")

    destination = DATA_DIR / "creditcard.csv"
    if destination.exists():
        print(f"Already exists: {destination}")
    else:
        shutil.copy2(csv_files[0], destination)
        print(f"Saved: {destination}")


if __name__ == "__main__":
    download_creditcard()
