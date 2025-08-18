#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import voyageai

CONFIG_DIR = os.path.expanduser("~/.atlas-search-cli")
CONFIGS_DIR = os.path.join(CONFIG_DIR, "configs")

def get_config(config_name="default"):
    config_path = os.path.join(CONFIGS_DIR, f"{config_name}.json")
    if not os.path.exists(config_path):
        return {}
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config_name, config):
    if not os.path.exists(CONFIGS_DIR):
        os.makedirs(CONFIGS_DIR)
    config_path = os.path.join(CONFIGS_DIR, f"{config_name}.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

def handle_config_set(args):
    config = get_config(args.name)
    if args.connectionString:
        config['connectionString'] = args.connectionString
    if args.db:
        config['db'] = args.db
    if args.coll:
        config['coll'] = args.coll
    if args.index:
        config['index'] = args.index
    if args.field:
        config['field'] = args.field
    if args.projectField:
        config['projectField'] = args.projectField
    if args.voyageAPIKey:
        config['voyageAPIKey'] = args.voyageAPIKey
    if args.voyageModel:
        config['voyageModel'] = args.voyageModel
    save_config(args.name, config)
    print(f"Configuration '{args.name}' saved.")

def handle_config_list(args):
    if not os.path.exists(CONFIGS_DIR):
        print("No configurations saved yet.")
        return
    configs = [f.replace(".json", "") for f in os.listdir(CONFIGS_DIR) if f.endswith(".json")]
    if not configs:
        print("No configurations saved yet.")
    else:
        print("Saved configurations:")
        for name in configs:
            print(f"- {name}")

def handle_lexical_search(args):
    current_config = get_config(args.config) if args.config else {}

    connection_string = args.connectionString if args.connectionString else current_config.get('connectionString')
    db_name = args.db if args.db else current_config.get('db')
    coll_name = args.coll if args.coll else current_config.get('coll')

    if not connection_string or not db_name or not coll_name:
        print("Error: Connection details not configured. Please run 'atlas-search config set <name>' first.", file=sys.stderr)
        sys.exit(1)

    path = args.field if args.field else current_config.get('field', {"wildcard": "*"})
    index = args.index if args.index else current_config.get('index', "default")
    config_project_fields = current_config.get('projectField', [])
    cli_project_fields = args.projectField if args.projectField else []
    project_fields = list(set(config_project_fields + cli_project_fields))

    pipeline = [
        {
            "$search": {
                "index": index,
                "text": {
                    "query": args.query,
                    "path": path
                }
            }
        },
        {
            "$limit": args.limit
        }
    ]

    if project_fields:
        project_stage = {"$project": {}}
        for field in project_fields:
            project_stage["$project"][field] = 1
        pipeline.append(project_stage)

    execute_pipeline(connection_string, db_name, coll_name, pipeline, args.verbose)

def handle_vector_search(args):
    current_config = get_config(args.config) if args.config else {}

    connection_string = args.connectionString if args.connectionString else current_config.get('connectionString')
    db_name = args.db if args.db else current_config.get('db')
    coll_name = args.coll if args.coll else current_config.get('coll')

    if not connection_string or not db_name or not coll_name:
        print("Error: Connection details not configured. Please run 'atlas-search config set <name>' first.", file=sys.stderr)
        sys.exit(1)

    index = args.index if args.index else current_config.get('index', "vector_index")
    field = args.field if args.field else current_config.get('field')
    config_project_fields = current_config.get('projectField', [])
    cli_project_fields = args.projectField if args.projectField else []
    project_fields = list(set(config_project_fields + cli_project_fields))

    if not field:
        print("Error: --field is required for vector search.", file=sys.stderr)
        sys.exit(1)
    elif isinstance(field, list):
        if len(field) > 1:
            print("Warning: Multiple fields specified for vector search. Only the first field will be used.", file=sys.stderr)
        field = field[0]

    if args.embedWithVoyage:
        api_key = args.voyageAPIKey if args.voyageAPIKey else current_config.get('voyageAPIKey', os.environ.get("VOYAGE_API_KEY"))
        if not api_key:
            print("Error: Voyage AI API key is required. Set the VOYAGE_API_KEY environment variable or use the --voyageAPIKey flag.", file=sys.stderr)
            sys.exit(1)
        vo = voyageai.Client(api_key=api_key)
        embedding = vo.embed([args.query], model=args.voyageModel if args.voyageModel else current_config.get('voyageModel', 'voyage-3.5')).embeddings[0]
        query_vector = embedding
        query_key = "queryVector"
    else:
        query_vector = args.query
        query_key = "query"

    pipeline = [
        {
            "$vectorSearch": {
                "index": index,
                query_key: query_vector,
                "path": field,
                "numCandidates": args.numCandidates if args.numCandidates else 10 * args.limit,
                "limit": args.limit
            }
        }
    ]

    if project_fields:
        project_stage = {"$project": {}}
        for p_field in project_fields:
            project_stage["$project"][p_field] = 1
        pipeline.append(project_stage)

    execute_pipeline(connection_string, db_name, coll_name, pipeline, args.verbose)

def execute_pipeline(connection_string, db_name, coll_name, pipeline, verbose):
    try:
        client = MongoClient(connection_string)
        db = client[db_name]
        collection = db[coll_name]

        if verbose:
            print("Executing aggregation pipeline:", file=sys.stderr)
            print(json.dumps(pipeline, indent=2), file=sys.stderr)

        results = list(collection.aggregate(pipeline))
        print(json.dumps(results, indent=2, default=str))

    except ConnectionFailure as e:
        print(f"Error: Could not connect to MongoDB: {e}", file=sys.stderr)
        sys.exit(1)
    except OperationFailure as e:
        print(f"Error: MongoDB operation failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='CLI for MongoDB Atlas Search')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Config command
    config_parser = subparsers.add_parser('config', help='Configure the CLI')
    config_subparsers = config_parser.add_subparsers(dest='subcommand', required=True)

    # Config set sub-subcommand
    config_set_parser = config_subparsers.add_parser('set', help='Set a named configuration')
    config_set_parser.add_argument('name', type=str, help='The name of the configuration')
    config_set_parser.add_argument('--connectionString', type=str, help='MongoDB connection string')
    config_set_parser.add_argument('--db', type=str, help='Database name')
    config_set_parser.add_argument('--coll', type=str, help='Collection name')
    config_set_parser.add_argument('--index', type=str, help='The name of the search index to use.')
    config_set_parser.add_argument('--field', type=str, action='append', help='The field to search. Can be specified multiple times.')
    config_set_parser.add_argument('--projectField', type=str, action='append', help='The field to project. Can be specified multiple times.')
    config_set_parser.add_argument('--voyageAPIKey', type=str, help='The Voyage AI API key.')
    config_set_parser.add_argument('--voyageModel', type=str, help='The Voyage AI model to use for embedding.')
    config_set_parser.set_defaults(func=handle_config_set)

    # Config list sub-subcommand
    config_list_parser = config_subparsers.add_parser('list', help='List saved configurations')
    config_list_parser.set_defaults(func=handle_config_list)

    # Lexical search command
    lexical_parser = subparsers.add_parser('lexical', help='Perform a lexical search')
    lexical_parser.add_argument('query', type=str, help='The search query string')
    lexical_parser.add_argument('--config', type=str, help='The name of the configuration to use.')
    lexical_parser.add_argument('--field', type=str, action='append', help='The field to search. Can be specified multiple times.')
    lexical_parser.add_argument('--projectField', type=str, action='append', help='The field to project. Can be specified multiple times.')
    lexical_parser.add_argument('--index', type=str, help='The name of the search index to use.')
    lexical_parser.add_argument('--limit', type=int, default=10, help='Number of results to return.')
    lexical_parser.add_argument('--connectionString', type=str, help='MongoDB connection string')
    lexical_parser.add_argument('--db', type=str, help='Database name')
    lexical_parser.add_argument('--coll', type=str, help='Collection name')
    lexical_parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    lexical_parser.set_defaults(func=handle_lexical_search)

    # Vector search command
    vector_parser = subparsers.add_parser('vector', help='Perform a vector search')
    vector_parser.add_argument('query', type=str, help='The search query string')
    vector_parser.add_argument('--config', type=str, help='The name of the configuration to use.')
    vector_parser.add_argument('--field', type=str, help='The field to search for vectors.')
    vector_parser.add_argument('--projectField', type=str, action='append', help='The field to project. Can be specified multiple times.')
    vector_parser.add_argument('--index', type=str, help='The name of the search index to use.')
    vector_parser.add_argument('--numCandidates', type=int, default=100, help='Number of candidates to consider for approximate vector search.')
    vector_parser.add_argument('--limit', type=int, default=10, help='Number of results to return.')
    vector_parser.add_argument('--embedWithVoyage', action='store_true', help='Embed the query with Voyage AI.')
    vector_parser.add_argument('--voyageModel', type=str, default='voyage-3.5', help='The Voyage AI model to use for embedding.')
    vector_parser.add_argument('--voyageAPIKey', type=str, help='The Voyage AI API key. Defaults to the VOYAGE_API_KEY environment variable.')
    vector_parser.add_argument('--connectionString', type=str, help='MongoDB connection string')
    vector_parser.add_argument('--db', type=str, help='Database name')
    vector_parser.add_argument('--coll', type=str, help='Collection name')
    vector_parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    vector_parser.set_defaults(func=handle_vector_search)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()