# Atlas Search CLI

A command-line interface for querying MongoDB Atlas Search.

## Installation

This project uses a `setup.py` file to make the CLI installable. This allows you to run the CLI from anywhere in your terminal using the `atlas-search` command.

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/atlas-search-cli.git
   cd atlas-search-cli
   ```

2. Create a virtual environment and install the CLI:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install .
   ```

   For development, you can install the package in editable mode. This allows you to make changes to the code and have them reflected immediately without reinstalling:
   ```bash
   pip install -e .
   ```

## Usage

To use the CLI, you need to provide a connection string, database name, collection name, and a search query.

```bash
atlas-search "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>"
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
atlas-search "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>" --searchAggFile search.json --verbose
```

### Performing a Vector Search

To perform a vector search, use the `--vector` flag and specify the field to search with the `--vectorField` flag.

**Note:** This feature assumes you have a vector search index named `vector_index`. The CLI uses Atlas Vector Search's auto-embedding feature, so you only need to provide a text query.

**Command:**

```bash
atlas-search "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>" --vector --vectorField "<your_vector_field>"
```

### Specifying Search Fields

By default, the text search will use a wildcard path (`*`). To specify which fields to search, you can use the `--searchField` flag multiple times.

**Command:**

```bash
atlas-search "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>" --searchField "title" --searchField "plot"
```

### Projecting Fields

To specify which fields to return in the results, you can use the `--projectField` flag multiple times.

**Command:**

```bash
atlas-search "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>" --projectField "title" --projectField "plot"
```

**A Note on Automatic Field Projection:**

The best way to handle field projection without user input is to not project any fields by default. This returns the full document, and you can then use tools like `jq` to parse the JSON and extract the fields you need. This is a common and flexible approach for command-line tools.

### Embedding with Voyage AI

To embed your query using Voyage AI and perform a vector search with the generated vector, use the `--embedWithVoyage` flag. You will need to provide your Voyage AI API key via the `VOYAGE_API_KEY` environment variable or the `--voyageAIAPIKey` flag.

**Command:**

```bash
export VOYAGE_API_KEY="<your_voyage_ai_api_key>"
atlas-search "your search query" --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>" --vector --vectorField "<your_vector_field>" --embedWithVoyage
```

### Arguments

- `query`: The search query string.
- `--connectionString`: Your MongoDB connection string.
- `--db`: The name of the database to connect to.
- `--coll`: The name of the collection to query.
- `--searchAggFile`: (Optional) The path to a JSON file containing a custom search aggregation pipeline.
- `--vector`: (Optional) Perform a vector search.
- `--vectorField`: (Optional) The field to search for vectors. Required when `--vector` is used.
- `--searchField`: (Optional) The field to search for text. Can be specified multiple times.
- `--projectField`: (Optional) The field to project. Can be specified multiple times.
- `--index`: (Optional) The name of the search index to use.
- `--numCandidates`: (Optional) Number of candidates to consider for approximate vector search. Defaults to 10.
- `--limit`: (Optional) Number of results to return. Defaults to 10.
- `--embedWithVoyage`: (Optional) Embed the query with Voyage AI.
- `--voyageAIModel`: (Optional) The Voyage AI model to use for embedding. Defaults to `voyage-2`.
- `--voyageAIAPIKey`: (Optional) The Voyage AI API key. Defaults to the `VOYAGE_API_KEY` environment variable.
- `--verbose`: (Optional) Enable verbose logging to see the executed aggregation pipeline.