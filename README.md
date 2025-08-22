# Atlas Search CLI

A command-line interface for querying MongoDB Atlas Search. Written by Google Gemini CLI. Guided by John Underwood.

## Installation
You can download compiled binaries or build from source.

### Download
The binaries are built from the Go source code.
1. Download the binary for your operating system from: https://github.com/JohnGUnderwood/atlas-search-cli/releases
2. Extract the downloaded tar
3. Rename the binary file to 'atlas-search'
4. Modify the binary permissions to be executable
5. You should now be able to execute from the command line using `atlas-search` or `.\atlas-search` or some variant

#### Security Permissions for MacOS
I don't have $99 a year to spend on Apple Developer Program so this code is notarized. These are your options to circumvent Apple Gatekeeper (if you trust me):

##### Bypass via Right-Click:
 * Locate the atlas-search binary in your Finder.
 * Right-click (or Control-click) on the binary.
 * Select "Open" from the contextual menu.
 * A dialog box will appear, asking if you're sure you want to open it. Click "Open" again.
 * This will run the application and usually adds an exception for it, allowing subsequent runs without the warning (unless the quarantine attribute is re-applied).

##### Bypass via System Settings:
 * Attempt to open the binary normally (double-click). You'll see the "unidentified developer" warning.
 * Go to System Settings (or System Preferences on older macOS versions).
 * Navigate to Privacy & Security.
 * Scroll down to the "Security" section. You should see a message like "atlas-search was blocked from use because it is not from an identified developer."
 * Click the "Open Anyway" button next to this message.
 * Confirm your choice in the subsequent dialog.

##### Remove Quarantine Attribute (Command Line):
You can manually remove the quarantine attribute from the binary using the xattr command in your terminal.

`xattr -d com.apple.quarantine /path/to/your/atlas-search`

Replace /path/to/your/atlas-search with the actual path to your downloaded executable. After running this, you should be able to execute the binary normally.

### Building From Source

This CLI is available in two variants: Python and Go.

#### Python Variant

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

#### Go Variant

The Go variant provides a single compiled executable.

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/atlas-search-cli.git
   cd atlas-search-cli
   ```

2. Build the Go executable:
   ```bash
   cd go
   go mod tidy
   go build -o atlas-search
   cd ..
   ```

3. Run the executable:
   ```bash
   ./go/atlas-search
   ```
   (Optional) For easier access, you can move the `atlas-search` executable to a directory in your system's PATH.

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

### Getting a Configuration

To display the details of a saved configuration, use the `config get` command:

```bash
atlas-search config get my_default_config
```

**Arguments for `config get`:**

- `name`: The name of the configuration to display.

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
- `--searchStageFi;e`: Path to a `$search` definition json file. Inserts query string into the file.
- `--connectionString`: MongoDB connection string. Overrides the configured value.
- `--db`: Database name. Overrides the configured value.
- `--coll`: Collection name. Overrides the configured value.
- `--verbose`: Enable verbose logging.

#### `--searchStageFile`
Path to a custom `$search` stage definition JSON file. When you pass this flag:

- The CLI will load your JSON and look for any of the following operators anywhere in the document: `text`, `phrase`, `autocomplete`.
- It will **recursively** inject your `query` string into every matching operator’s `"query"` field.
- If an operator is missing a `"path"` key, it will add `"path": <your field or default wildcard>`.
- If your top‐level object has no `"index"`, it will add the chosen index name.

This makes it easy to provide a fully custom `$search` stage—your file can include nesting, compound operators, or any Atlas Search syntax. The CLI handles inserting your query and path in the right places.

Example `search.json`:

```json
{
    "compound": {
        "minimumShouldMatch": 1,
        "should": [
            { "phrase": { "score": { "boost": {"value": 3 } } }},
            { "text": { "path": "description", "score": { "boost": {"value": 2 } } }},
            { "text": {} }
    ]
  }
}
```

Running
```bash
atlas-search-cli lexical "mongodb" \
  --searchStageFile mySearchStage.json \
  --field title --index myIndex
```

Will produce an aggregation stage equivalent to:
```json
{
   "$search":{
      "index":"myIndex",
      "compoun":{
         "minimumShouldMatch":1,
         "should":[
            { "phrase":{
                  "query":"mongodb","path":"title",
                  "score": { "boost": {"value": 3 } }
               }
            },
            { "text": {
                  "query":"mongodb", "path": "description",
                  "score": { "boost": {"value": 2 } }
               }
            },
            { "text": {"query":"mongodb","path":"title"} }
         ]
      }
   }
}
```

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
