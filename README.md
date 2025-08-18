# Atlas Search CLI

A command-line interface for querying MongoDB Atlas Search. Written by Google Gemini CLI. Guided by John Underwood.

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

The CLI now supports named configurations. You can set and manage different sets of connection details and search parameters.

### Setting a Configuration

Use the `config set` command to create or update a named configuration. This will save the configuration to a file in `~/.atlas-search-cli/configs/<name>.json`.

```bash
atlas-search config set my_default_config \
  --connectionString "<your_connection_string>" \
  --db "<database_name>" \
  --coll "<collection_name>" \
  --index "my_search_index" \
  --field "title" \
  --projectField "title" --projectField "plot"
```

**Arguments for `config set`:**

- `name`: The name of the configuration (e.g., `my_default_config`).
- `--connectionString`: MongoDB connection string.
- `--db`: Database name.
- `--coll`: Collection name.
- `--index`: The name of the search index to use.
- `--field`: The field to search. Can be specified multiple times.
- `--projectField`: The field to project. Can be specified multiple times.
- `--voyageAPIKey`: The Voyage AI API key.
- `--voyageModel`: The Voyage AI model to use for embedding.

### Listing Configurations

To see all your saved configurations, use the `config list` command:

```bash
atlas-search config list
```

## Usage

The CLI has two main commands for searching: `lexical` and `vector`.

### Using a Named Configuration

You can use a saved configuration with the `lexical` or `vector` commands using the `--config` flag. Any command-line arguments you provide will override the values from the named configuration.

```bash
atlas-search lexical "your search query" --config my_default_config
```

### Lexical Search

To perform a lexical search, use the `lexical` command:

```bash
atlas-search lexical "your search query"
```

**Arguments:**

- `query`: The search query string.
- `--config`: The name of the configuration to use.
- `--field`: The field to search. Can be specified multiple times. Defaults to wildcard (`*`).
- `--projectField`: The field to project. Can be specified multiple times. If a configuration is used, these fields will be added to any `projectField` values defined in the configuration.
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
- `--config`: The name of the configuration to use.
- `--field`: The field to search for vectors. This is a required argument.
- `--projectField`: The field to project. Can be specified multiple times. If a configuration is used, these fields will be added to any `projectField` values defined in the configuration.
- `--index`: The name of the search index to use. Defaults to `vector_index`.
- `--numCandidates`: Number of candidates to consider for approximate vector search. Defaults to 100 (or 10x 'limit' if set).
- `--limit`: Number of results to return. Defaults to 10.
- `--embedWithVoyage`: Embed the query with Voyage AI.
- `--voyageModel`: The Voyage AI model to use for embedding. If not specified, it will attempt to use the value from the configuration, or default to `voyage-3.5`.
- `--voyageAPIKey`: The Voyage AI API key. Defaults to the `VOYAGE_API_KEY` environment variable.
- `--connectionString`: MongoDB connection string. Overrides the configured value.
- `--db`: Database name. Overrides the configured value.
- `--coll`: Collection name. Overrides the configured value.
- `--verbose`: Enable verbose logging.
