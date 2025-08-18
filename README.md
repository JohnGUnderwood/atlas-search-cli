# Atlas Search CLI

A command-line interface for querying MongoDB Atlas Search.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/atlas-search-cli.git
   cd atlas-search-cli
   ```

2. Create a virtual environment and install the dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Usage

To use the CLI, you need to provide a connection string, database name, collection name, and a search query.

```bash
source venv/bin/activate
./main.py "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>"
```

### Using a custom aggregation pipeline

You can also use a custom aggregation pipeline from a JSON file. The file must contain a valid JSON array (pipeline) and a `%%SEARCH_QUERY%%` placeholder, which will be replaced with your search query.

**Example `search.json`:**

```json
[
    {
        "$search": {
            "index": "default",
            "text": {
                "query": "%%SEARCH_QUERY%%",
                "path": {
                    "wildcard": "*"
                }
            }
        }
    },
    {
        "$project": {
            "_id": 0,
            "title": 1,
            "plot": 1
        }
    }
]
```

**Command:**

```bash
source venv/bin/activate
./main.py "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>" --searchAggFile search.json --verbose
```

### Arguments

- `query`: The search query string.
- `--connectionString`: Your MongoDB connection string.
- `--db`: The name of the database to connect to.
- `--coll`: The name of the collection to query.
- `--searchAggFile`: (Optional) The path to a JSON file containing a custom search aggregation pipeline.
- `--verbose`: (Optional) Enable verbose logging to see the executed aggregation pipeline.