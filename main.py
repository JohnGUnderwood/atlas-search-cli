#!/usr/bin/env python3
import argparse
import json
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

import os
import voyageai

def main():
    parser = argparse.ArgumentParser(description='CLI for MongoDB Atlas Search')
    parser.add_argument('query', type=str, help='The search query string')
    parser.add_argument('--connectionString', type=str, help='MongoDB connection string')
    parser.add_argument('--db', type=str, help='Database name')
    parser.add_argument('--coll', type=str, help='Collection name')
    parser.add_argument('--searchAggFile', type=str, help='Path to a JSON file containing the search aggregation pipeline')
    parser.add_argument('--vector', action='store_true', help='Perform a vector search')
    parser.add_argument('--vectorField', type=str, help='The field to search for vectors. Required when --vector is used.')
    parser.add_argument('--searchField', type=str, action='append', help='The field to search for text. Can be specified multiple times.')
    parser.add_argument('--projectField', type=str, action='append', help='The field to project. Can be specified multiple times.')
    parser.add_argument('--index', type=str, help='The name of the search index to use.')
    parser.add_argument('--numCandidates', type=int, default=10, help='Number of candidates to consider for approximate vector search.')
    parser.add_argument('--limit', type=int, default=10, help='Number of results to return.')
    parser.add_argument('--embedWithVoyage', action='store_true', help='Embed the query with Voyage AI.')
    parser.add_argument('--voyageAIModel', type=str, default='voyage-2', help='The Voyage AI model to use for embedding.')
    parser.add_argument('--voyageAIAPIKey', type=str, help='The Voyage AI API key. Defaults to the VOYAGE_API_KEY environment variable.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.vector and not args.vectorField:
        print("Error: --vectorField is required when --vector is used.", file=sys.stderr)
        sys.exit(1)

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
        elif args.vector:
            # Vector search pipeline
            index = args.index if args.index else "vector_index"
            if args.embedWithVoyage:
                api_key = args.voyageAIAPIKey if args.voyageAIAPIKey else os.environ.get("VOYAGE_API_KEY")
                if not api_key:
                    print("Error: Voyage AI API key is required. Set the VOYAGE_API_KEY environment variable or use the --voyageAIAPIKey flag.", file=sys.stderr)
                    sys.exit(1)
                vo = voyageai.Client(api_key=api_key)
                embedding = vo.embed([args.query], model=args.voyageAIModel).embeddings[0]
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
                        "path": args.vectorField,
                        "numCandidates": args.numCandidates,
                        "limit": args.limit
                    }
                }
            ]
        else:
            # Default search pipeline
            path = {"wildcard": "*"} if not args.searchField else args.searchField
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