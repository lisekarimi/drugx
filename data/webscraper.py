# data/webscraper.py
"""Download DDInter CSV files to data/raw/ directory.

Simple webscraper for initial data acquisition during development.
"""

from pathlib import Path

import requests

# Constants for DDInter data
BASE_URL = "https://ddinter.scbdd.com/static/media/download/ddinter_downloads_code_"
CHUNK_SIZE = 8192
DEFAULT_OUTPUT_DIR = "data/raw"
CONSOLIDATED_FILENAME = "ddinter_all.csv"


class DDInterWebscraper:
    """Download DDInter 2.0 datasets from official source."""

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR):
        """Initialize the webscraper with output directory."""
        self.output_dir = Path(output_dir)

        # DDInter 2.0 file definitions - just URLs
        self.files = {
            "A": f"{BASE_URL}A.csv",
            "B": f"{BASE_URL}B.csv",
            "D": f"{BASE_URL}D.csv",
            "H": f"{BASE_URL}H.csv",
            "L": f"{BASE_URL}L.csv",
            "P": f"{BASE_URL}P.csv",
            "R": f"{BASE_URL}R.csv",
            "V": f"{BASE_URL}V.csv",
        }

    def create_output_dir(self):
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {self.output_dir}")

    def download_file(self, url: str, filepath: Path, code: str) -> bool:
        """Download a single file with basic progress indication."""
        try:
            print(f"Downloading {code}...")

            response = requests.get(url, stream=True, verify=False)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Simple progress indication every 25%
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if (
                                int(percent) % 25 == 0
                                and downloaded % (total_size // 4) < CHUNK_SIZE
                            ):
                                print(f"  Progress: {percent:.0f}%")

            print(f"  Completed: {filepath.name}")
            return True

        except Exception as e:
            print(f"  Failed: {str(e)}")
            return False

    def consolidate_files(self, output_filename: str = CONSOLIDATED_FILENAME) -> Path:
        """Consolidate all downloaded CSVs into one file with category column."""
        import pandas as pd

        print("Consolidating files...")
        all_dfs = []

        for code in self.files.keys():
            filepath = self.output_dir / f"ddinter_downloads_code_{code}.csv"
            if filepath.exists() and filepath.stat().st_size > 0:
                try:
                    df = pd.read_csv(filepath, sep=",")
                    df["category"] = code
                    all_dfs.append(df)
                    print(f"  Added {len(df)} rows from {code}")
                except Exception as e:
                    print(f"  Failed to read {filepath}: {e}")

        if not all_dfs:
            raise RuntimeError("No files could be read for consolidation")

        consolidated = pd.concat(all_dfs, ignore_index=True)
        output_path = self.output_dir.parent / output_filename
        consolidated.to_csv(output_path, index=False)

        print(
            f"Consolidated {len(all_dfs)} files into {output_path} ({len(consolidated)} rows)"
        )
        return output_path

    def download_all(self) -> bool:
        """Download all DDInter CSV files and consolidate them."""
        print("DDInter Data Webscraper")
        print("=" * 50)

        self.create_output_dir()

        # Always download fresh files to ensure data integrity
        success_count = 0
        for code, url in self.files.items():
            filepath = self.output_dir / f"ddinter_downloads_code_{code}.csv"
            if self.download_file(url, filepath, code):
                success_count += 1

        print("=" * 50)
        if success_count != len(self.files):
            print(f"Download failed: {success_count}/{len(self.files)} files")
            return False

        # Consolidate into single file
        try:
            consolidated_path = self.consolidate_files()
            print(f"Success! Created {consolidated_path}")
            return True
        except Exception as e:
            print(f"Consolidation failed: {e}")
            return False


def main():
    """CLI interface for downloading DDInter data."""
    import argparse

    parser = argparse.ArgumentParser(description="Download DDInter CSV files")
    parser.add_argument(
        "--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory"
    )

    args = parser.parse_args()

    scraper = DDInterWebscraper(args.output_dir)
    success = scraper.download_all()

    if success:
        print("\nNext steps:")
        print("1. Run data exploration notebook")
        print("2. Process and clean the data")
        exit(0)
    else:
        print("\nSome downloads failed. Check your internet connection.")
        exit(1)


if __name__ == "__main__":
    main()
