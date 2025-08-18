#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import voyageai

CONFIG_DIR = os.path.expanduser("~/.atlas-search-cli")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def get_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def handle_config(args):
    config = get_config()
    if args.connectionString:
        config['connectionString'] = args.connectionString
    if args.db:
        config['db'] = args.db
    if args.coll:
        config['coll'] = args.coll
    save_config(config)
    print("Configuration saved.")

def handle_lexical_search(args):
    config = get_config()
    connection_string = args.connectionString if args.connectionString else config.get('connectionString')
    db_name = args.db if args.db else config.get('db')
    coll_name = args.coll if args.coll else config.get('coll')

    if not connection_string or not db_name or not coll_name:
        print("Error: Connection details not configured. Please run 'atlas-search config' first.", file=sys.stderr)
        sys.exit(1)

    path = {"wildcard": "*"} if not args.field else args.field
    index = args.index if args.index else "default"
    pipeline = [
        {
            "$search": {
                "index": index,
                "text": {
                    "query": args.query,
                    "path": path
                }
            }
        }
    ]

    if args.projectField:
        project_stage = {"$project": {}}
        for field in args.projectField:
            project_stage["$project"][field] = 1
        pipeline.append(project_stage)

    execute_pipeline(connection_string, db_name, coll_name, pipeline, args.verbose)

def handle_vector_search(args):
    config = get_config()
    connection_string = args.connectionString if args.connectionString else config.get('connectionString')
    db_name = args.db if args.db else config.get('db')
    coll_name = args.coll if args.coll else config.get('coll')

    if not connection_string or not db_name or not coll_name:
        print("Error: Connection details not configured. Please run 'atlas-search config' first.", file=sys.stderr)
        sys.exit(1)

    index = args.index if args.index else "vector_index"

    if args.embedWithVoyage:
        api_key = args.voyageAPIKey if args.voyageAPIKey else os.environ.get("VOYAGE_API_KEY")
        if not api_key:
            print("Error: Voyage AI API key is required. Set the VOYAGE_API_KEY environment variable or use the --voyageAPIKey flag.", file=sys.stderr)
            sys.exit(1)
        vo = voyageai.Client(api_key=api_key)
        embedding = vo.embed([args.query], model=args.voyageModel).embeddings[0]
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
                "path": args.field,
                "numCandidates": args.numCandidates,
                "limit": args.limit
            }
        }
    ]

    if args.projectField:
        project_stage = {"$project": {}}
        for field in args.projectField:
            project_stage["$project"][field] = 1
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
    config_parser.add_argument('--connectionString', type=str, help='MongoDB connection string')
    config_parser.add_argument('--db', type=str, help='Database name')
    config_parser.add_argument('--coll', type=str, help='Collection name')
    config_parser.set_defaults(func=handle_config)

    # Lexical search command
    lexical_parser = subparsers.add_parser('lexical', help='Perform a lexical search')
    lexical_parser.add_argument('query', type=str, help='The search query string')
    lexical_parser.add_argument('--field', type=str, action='append', help='The field to search. Can be specified multiple times.')
    lexical_parser.add_argument('--projectField', type=str, action='append', help='The field to project. Can be specified multiple times.')
    lexical_parser.add_argument('--index', type=str, help='The name of the search index to use.')
    lexical_parser.add_argument('--connectionString', type=str, help='MongoDB connection string')
    lexical_parser.add_argument('--db', type=str, help='Database name')
    lexical_parser.add_argument('--coll', type=str, help='Collection name')
    lexical_parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    lexical_parser.set_defaults(func=handle_lexical_search)

    # Vector search command
    vector_parser = subparsers.add_parser('vector', help='Perform a vector search')
    vector_parser.add_argument('query', type=str, help='The search query string')
    vector_parser.add_argument('--field', type=str, required=True, help='The field to search for vectors.')
    vector_parser.add_argument('--projectField', type=str, action='append', help='The field to project. Can be specified multiple times.')
    vector_parser.add_argument('--index', type=str, help='The name of the search index to use.')
    vector_parser.add_argument('--numCandidates', type=int, default=10, help='Number of candidates to consider for approximate vector search.')
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
