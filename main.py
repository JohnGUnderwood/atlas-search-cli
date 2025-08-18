import argparse
import json
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

def main():
    parser = argparse.ArgumentParser(description='CLI for MongoDB Atlas Search')
    parser.add_argument('query', type=str, help='The search query string')
    parser.add_argument('--connectionString', type=str, help='MongoDB connection string')
    parser.add_argument('--db', type=str, help='Database name')
    parser.add_argument('--coll', type=str, help='Collection name')
    parser.add_argument('--searchAggFile', type=str, help='Path to a JSON file containing the search aggregation pipeline')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if not args.connectionString:
        print("Error: Connection string is required.", file=sys.stderr)
        sys.exit(1)

    if not args.db:
        print("Error: Database name is required.", file=sys.stderr)
        sys.exit(1)

    if not args.coll:
        print("Error: Collection name is required.", file=sys.stderr)
        sys.exit(1)

    try:
        client = MongoClient(args.connectionString)
        db = client[args.db]
        collection = db[args.coll]

        if args.searchAggFile:
            try:
                with open(args.searchAggFile, 'r') as f:
                    pipeline_str = f.read()
                    # Replace placeholder with the actual query
                    if "%%SEARCH_QUERY%%" not in pipeline_str:
                        print(f"Error: The aggregation file '{args.searchAggFile}' must contain the '%%SEARCH_QUERY%%' placeholder.", file=sys.stderr)
                        sys.exit(1)
                    pipeline_str = pipeline_str.replace("%%SEARCH_QUERY%%", args.query)
                    pipeline = json.loads(pipeline_str)
                    if not isinstance(pipeline, list):
                        print(f"Error: The aggregation file '{args.searchAggFile}' must contain a valid JSON array (pipeline).", file=sys.stderr)
                        sys.exit(1)

            except FileNotFoundError:
                print(f"Error: Aggregation file not found at '{args.searchAggFile}'", file=sys.stderr)
                sys.exit(1)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON in aggregation file '{args.searchAggFile}'", file=sys.stderr)
                sys.exit(1)
        else:
            # Default search pipeline
            pipeline = [
                {
                    "$search": {
                        "index": "default",
                        "text": {
                            "query": args.query,
                            "path": {
                                "wildcard": "*"
                            }
                        }
                    }
                }
            ]

        if args.verbose:
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

if __name__ == "__main__":
    main()
