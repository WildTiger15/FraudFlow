"""Download the public synthetic PaySim dataset (about 490 MB).

PaySim is a simulator of mobile money transactions (Lopez-Rojas et al., 2016).
Every row is synthetic: there are no real customers in it.
Original source: https://www.kaggle.com/datasets/ealaxi/paysim1
This script uses a public Hugging Face mirror so no Kaggle login is needed.
"""
import urllib.request

from config import RAW_CSV

MIRROR_URL = "https://huggingface.co/datasets/theman10/paysim/resolve/main/paysim.csv"


def main():
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    if RAW_CSV.exists():
        print(f"Already downloaded: {RAW_CSV}")
        return
    print(f"Downloading {MIRROR_URL} ...")
    urllib.request.urlretrieve(MIRROR_URL, RAW_CSV)
    print(f"Saved to {RAW_CSV}")


if __name__ == "__main__":
    main()
