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

## Configuration

Before you can run searches, you need to configure the CLI with your MongoDB connection details. You can do this using the `config` command:

```bash
atlas-search config --connectionString "<your_connection_string>" --db "<database_name>" --coll "<collection_name>"
```

This will save the configuration to a file in `~/.atlas-search-cli/config.json`. You can override these settings at any time by passing the corresponding flags to the `lexical` or `vector` commands.

## Usage

The CLI has two main commands for searching: `lexical` and `vector`.

### Lexical Search

To perform a lexical search, use the `lexical` command:

```bash
atlas-search lexical "your search query"
```

**Arguments:**

- `query`: The search query string.
- `--field`: The field to search. Can be specified multiple times. Defaults to wildcard (`*`).
- `--projectField`: The field to project. Can be specified multiple times.
- `--index`: The name of the search index to use. Defaults to `default`.
- `--connectionString`: MongoDB connection string. Overrides the configured value.
- `--db`: Database name. Overrides the configured value.
- `--coll`: Collection name. Overrides the configured value.
- `--verbose`: Enable verbose logging.

### Vector Search

To perform a vector search, use the `vector` command:

```bash
atlas-search vector "your search query" --field "<your_vector_field>"
```

**Arguments:**

- `query`: The search query string.
- `--field`: The field to search for vectors. This is a required argument.
- `--projectField`: The field to project. Can be specified multiple times.
- `--index`: The name of the search index to use. Defaults to `vector_index`.
- `--numCandidates`: Number of candidates to consider for approximate vector search. Defaults to 10.
- `--limit`: Number of results to return. Defaults to 10.
- `--embedWithVoyage`: Embed the query with Voyage AI.
- `--voyageModel`: The Voyage AI model to use for embedding. Defaults to `voyage-3.5`.
- `--voyageAPIKey`: The Voyage AI API key. Defaults to the `VOYAGE_API_KEY` environment variable.
- `--connectionString`: MongoDB connection string. Overrides the configured value.
- `--db`: Database name. Overrides the configured value.
- `--coll`: Collection name. Overrides the configured value.
- `--verbose`: Enable verbose logging.
