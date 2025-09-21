# data/data_processor.py
"""Process consolidated DDInter CSV file for PostgreSQL storage.

Groups same drug pairs and aggregates categories into comma-separated strings.
"""

from pathlib import Path

import pandas as pd

# Constants
INPUT_FILE = "ddinter_all.csv"
OUTPUT_FILE = "ddinter_pg.csv"


class DDInterProcessor:
    """Process DDInter data for PostgreSQL storage."""

    def __init__(self, data_dir: str = "data"):
        """Initialize processor with data directory."""
        self.data_dir = Path(data_dir)
        self.input_path = self.data_dir / INPUT_FILE
        self.output_path = self.data_dir / OUTPUT_FILE

    def validate_input(self) -> None:
        """Validate that input file exists and has expected columns."""
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        # Load and check columns
        df = pd.read_csv(self.input_path)
        expected_columns = [
            "DDInterID_A",
            "Drug_A",
            "DDInterID_B",
            "Drug_B",
            "Level",
            "category",
        ]
        missing = [col for col in expected_columns if col not in df.columns]

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        print(f"Input validation passed: {len(df)} rows, {len(df.columns)} columns")

    def process_data(self) -> pd.DataFrame:
        """Load, group, and aggregate DDInter data."""
        print("Loading input data...")
        df = pd.read_csv(self.input_path)

        print(f"Initial data: {len(df)} rows")

        # Group by unique drug pairs and aggregate categories
        print("Grouping by drug pairs and aggregating categories...")
        grouped = (
            df.groupby(["DDInterID_A", "Drug_A", "DDInterID_B", "Drug_B", "Level"])
            .agg({"category": lambda x: ",".join(sorted(set(x)))})
            .reset_index()
        )

        # Rename columns for PostgreSQL schema
        grouped.columns = [
            "ddinter_id_a",
            "drug_a",
            "ddinter_id_b",
            "drug_b",
            "severity",
            "categories",
        ]

        print(f"Processed data: {len(grouped)} rows")
        print(f"Deduplication removed: {len(df) - len(grouped)} rows")

        return grouped

    def save_output(self, df: pd.DataFrame) -> None:
        """Save processed data to CSV file."""
        df.to_csv(self.output_path, index=False)
        print(f"Saved processed data to: {self.output_path}")

    def show_summary(self, df: pd.DataFrame) -> None:
        """Display processing summary."""
        print("\n" + "=" * 50)
        print("PROCESSING SUMMARY")
        print("=" * 50)
        print(f"Output file: {self.output_path}")
        print(f"Total interactions: {len(df)}")
        print(f"Unique severities: {df['severity'].value_counts().to_dict()}")

        # Category distribution
        all_categories = []
        for cats in df["categories"]:
            all_categories.extend(cats.split(","))
        category_counts = pd.Series(all_categories).value_counts()
        print(f"Category distribution: {category_counts.to_dict()}")

        # Sample with multiple categories
        multi_cat = df[df["categories"].str.contains(",")]
        if not multi_cat.empty:
            print(f"Interactions with multiple categories: {len(multi_cat)}")
            print("Sample multi-category interactions:")
            for _, row in multi_cat.head(3).iterrows():
                print(f"  {row['drug_a']} + {row['drug_b']}: {row['categories']}")

    def process(self) -> Path:
        """Process the data for PostgreSQL storage."""
        print("DDInter Data Processor")
        print("=" * 50)

        # Validate input
        self.validate_input()

        # Process data
        processed_df = self.process_data()

        # Save output
        self.save_output(processed_df)

        # Show summary
        self.show_summary(processed_df)

        return self.output_path


def main():
    """CLI interface for data processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Process DDInter data for PostgreSQL")
    parser.add_argument("--data-dir", default="data", help="Data directory path")

    args = parser.parse_args()

    try:
        processor = DDInterProcessor(args.data_dir)
        output_file = processor.process()

        print(f"\nSuccess! PostgreSQL-ready file created: {output_file}")
        print("\nNext steps:")
        print("1. Update database.py to load the new file")
        print("2. Test database setup with cleaned data")

    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
