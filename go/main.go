package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type Config struct {
	ConnectionString string   `json:"connectionString,omitempty"`
	DB               string   `json:"db,omitempty"`
	Coll             string   `json:"coll,omitempty"`
	Index            string   `json:"index,omitempty"`
	Field            []string `json:"field,omitempty"`
	ProjectField     []string `json:"projectField,omitempty"`
	VoyageAPIKey     string   `json:"voyageAPIKey,omitempty"`
	VoyageModel      string   `json:"voyageModel,omitempty"`
}

func getConfigDirPath() (string, error) {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("failed to get user home directory: %w", err)
	}
	configDirPath := filepath.Join(homeDir, ".atlas-search-cli", "configs")
	return configDirPath, nil
}

// loadConfig loads a named configuration from the file system.
func loadConfig(configName string) (*Config, error) {
	configDirPath, err := getConfigDirPath()
	if err != nil {
		return nil, err
	}
	configFilePath := filepath.Join(configDirPath, configName+".json")

	data, err := os.ReadFile(configFilePath)
	
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("configuration '%s' not found", configName)
		}
		return nil, fmt.Errorf("failed to read config file '%s': %w", configFilePath, err)
	}

	var cfg Config
	err = json.Unmarshal(data, &cfg)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal config file '%s': %w", configFilePath, err)
	}

	return &cfg, nil
}

// mergeConfigs merges a base configuration with command-line flags.
// Command-line flags take precedence.
func mergeConfigs(baseConfig *Config, cmd *cobra.Command) (*Config, error) {
	mergedConfig := *baseConfig // Start with a copy of the base config

	// Override with command-line flags if provided
	if cmd.Flags().Changed("connectionString") {
		mergedConfig.ConnectionString, _ = cmd.Flags().GetString("connectionString")
	}
	if cmd.Flags().Changed("db") {
		mergedConfig.DB, _ = cmd.Flags().GetString("db")
	}
	if cmd.Flags().Changed("coll") {
		mergedConfig.Coll, _ = cmd.Flags().GetString("coll")
	}
	if cmd.Flags().Changed("index") {
		mergedConfig.Index, _ = cmd.Flags().GetString("index")
	}
	if cmd.Flags().Changed("field") {
		mergedConfig.Field, _ = cmd.Flags().GetStringArray("field")
	}
	if cmd.Flags().Changed("projectField") {
		cmdProjectFields, _ := cmd.Flags().GetStringArray("projectField")
		mergedConfig.ProjectField = append(mergedConfig.ProjectField, cmdProjectFields...)
	}
	if cmd.Flags().Changed("voyageAPIKey") {
		mergedConfig.VoyageAPIKey, _ = cmd.Flags().GetString("voyageAPIKey")
	}
	if cmd.Flags().Changed("voyageModel") {
		mergedConfig.VoyageModel, _ = cmd.Flags().GetString("voyageModel")
	}

	return &mergedConfig, nil
}

// getMongoClient establishes a MongoDB client connection.
func getMongoClient(connectionString string) (*mongo.Client, error) {
	if connectionString == "" {
		return nil, fmt.Errorf("MongoDB connection string is empty")
	}

	clientOptions := options.Client().ApplyURI(connectionString)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, clientOptions)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to MongoDB: %w", err)
	}

	// Ping the primary to verify connection
	err = client.Ping(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to ping MongoDB: %w", err)
	}

	return client, nil
}

// getEmbeddings fetches embeddings from Voyage AI.
func getEmbeddings(query, apiKey, model string) ([]float64, error) {
	if apiKey == "" {
		return nil, fmt.Errorf("Voyage AI API key is not provided")
	}

	if model == "" {
		model = "voyage-3.5" // Default model as per README
	}

	url := "https://api.voyageai.com/v1/embeddings"
	payload := map[string]interface{}{
		"input": []string{query},
		"model": model,
	}
	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal embedding payload: %w", err)
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonPayload))
	if err != nil {
		return nil, fmt.Errorf("failed to create HTTP request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)

	client := &http.Client{Timeout: 10 * time.Second}
	res, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send HTTP request to Voyage AI: %w", err)
	}
	defer res.Body.Close()

	if res.StatusCode != http.StatusOK {
		bodyBytes, _ := io.ReadAll(res.Body)
		return nil, fmt.Errorf("Voyage AI API returned non-200 status: %d, body: %s", res.StatusCode, string(bodyBytes))
	}

	var result struct {
		Data []struct {
			Embedding []float64 `json:"embedding"`
		} `json:"data"`
	}

	bodyBytes, err := io.ReadAll(res.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read Voyage AI response body: %w", err)
	}

	err = json.Unmarshal(bodyBytes, &result)
	if err != nil {
		return nil, fmt.Errorf("failed to unmarshal Voyage AI response: %w", err)
	}

	if len(result.Data) == 0 || len(result.Data[0].Embedding) == 0 {
		return nil, fmt.Errorf("no embeddings found in Voyage AI response")
	}

	return result.Data[0].Embedding, nil
}

// parseVectorString parses a comma-separated string of floats into a []float64.
func parseVectorString(s string) ([]float64, error) {
	parts := strings.Split(s, ",")
	vector := make([]float64, len(parts))
	for i, part := range parts {
		val, err := strconv.ParseFloat(strings.TrimSpace(part), 64)
		if err != nil {
			return nil, fmt.Errorf("invalid vector component '%s': %w", part, err)
		}
		vector[i] = val
	}
	return vector, nil
}

var rootCmd = &cobra.Command{
	Use:   "atlas-search",
	Short: "A command-line interface for querying MongoDB Atlas Search.",
	Long:  `A command-line interface for querying MongoDB Atlas Search.`,
	Run: func(cmd *cobra.Command, args []string) {
		// Default behavior if no subcommand is given
		cmd.Help()
	},
}

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage Atlas Search CLI configurations",
	Long:  `Manage Atlas Search CLI configurations.`,
	Run: func(cmd *cobra.Command, args []string) {
		cmd.Help()
	},
}

var configSetCmd = &cobra.Command{
	Use:   "set <name>",
	Short: "Set a named configuration",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		configName := args[0]

		configDirPath, err := getConfigDirPath()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return
		}

		err = os.MkdirAll(configDirPath, 0755)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error creating config directory: %v\n", err)
			return
		}

		cfg := Config{}
		cfg.ConnectionString, _ = cmd.Flags().GetString("connectionString")
		cfg.DB, _ = cmd.Flags().GetString("db")
		cfg.Coll, _ = cmd.Flags().GetString("coll")
		cfg.Index, _ = cmd.Flags().GetString("index")
		cfg.Field, _ = cmd.Flags().GetStringArray("field")
		cfg.ProjectField, _ = cmd.Flags().GetStringArray("projectField")
		cfg.VoyageAPIKey, _ = cmd.Flags().GetString("voyageAPIKey")
		cfg.VoyageModel, _ = cmd.Flags().GetString("voyageModel")

		configFilePath := filepath.Join(configDirPath, configName+".json")
		data, err := json.MarshalIndent(cfg, "", "  ")
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error marshalling config: %v\n", err)
			return
		}

		err = os.WriteFile(configFilePath, data, 0644)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error writing config file: %v\n", err)
			return
		}

		fmt.Printf("Configuration '%s' saved successfully.\n", configName)
	},
}

var configListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all saved configurations",
	Run: func(cmd *cobra.Command, args []string) {
		configDirPath, err := getConfigDirPath()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			return
		}

		files, err := os.ReadDir(configDirPath)
		if err != nil {
			if os.IsNotExist(err) {
				fmt.Println("No configurations found.")
				return
			}
			fmt.Fprintf(os.Stderr, "Error reading config directory: %v\n", err)
			return
		}

		fmt.Println("Available Configurations:")
		found := false
		for _, file := range files {
			if !file.IsDir() && filepath.Ext(file.Name()) == ".json" {
				fmt.Printf("- %s\n", file.Name()[:len(file.Name())-len(filepath.Ext(file.Name()))])
				found = true
			}
		}

		if !found {
			fmt.Println("  No configurations found.")
		}
	},
}

var lexicalCmd = &cobra.Command{
	Use:   "lexical <query>",
	Short: "Perform a lexical search",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		query := args[0]
		configName, _ := cmd.Flags().GetString("config")
		verbose, _ := cmd.Flags().GetBool("verbose")

		var cfg *Config
		if configName != "" {
			var err error
			cfg, err = loadConfig(configName)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error loading configuration: %v\n", err)
				return
			}
		}

		// Create a default config if none loaded
		if cfg == nil {
			cfg = &Config{}
		}

		finalConfig, err := mergeConfigs(cfg, cmd)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error merging configurations: %v\n", err)
			return
		}

		if finalConfig.ConnectionString == "" || finalConfig.DB == "" || finalConfig.Coll == "" {
			fmt.Fprintf(os.Stderr, "Error: connectionString, db, and coll must be provided either via config or flags.\n")
			return
		}

		client, err := getMongoClient(finalConfig.ConnectionString)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error connecting to MongoDB: %v\n", err)
			return
		}
		defer func() {
			if err = client.Disconnect(context.TODO()); err != nil {
				fmt.Fprintf(os.Stderr, "Error disconnecting from MongoDB: %v\n", err)
			}
		}()

		collection := client.Database(finalConfig.DB).Collection(finalConfig.Coll)

		// Build the $search stage
		searchPath := finalConfig.Field
		if len(searchPath) == 0 {
			searchPath = []string{"*"} // Default to wildcard if no field is specified
		}
		searchStage := bson.D{{"$search", bson.D{
			{"index", finalConfig.Index},
			{"text", bson.D{{"query", query}, {"path", searchPath}}}},
		}}

		// Build the $project stage
		projectStage := bson.D{{"$project", bson.D{}}}
		if len(finalConfig.ProjectField) > 0 {
			projectFields := bson.D{}
			for _, field := range finalConfig.ProjectField {
				projectFields = append(projectFields, bson.E{Key: field, Value: 1})
			}
			projectFields = append(projectFields, bson.E{Key: "_id", Value: 0}) // Exclude _id by default
			projectStage = bson.D{{"$project", projectFields}}
		}

		pipeline := mongo.Pipeline{searchStage, projectStage}

		if verbose {
			fmt.Println("MongoDB Aggregation Pipeline:")
			pipelineJSON, _ := json.MarshalIndent(pipeline, "", "  ")
			fmt.Println(string(pipelineJSON))
		}

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		cursor, err := collection.Aggregate(ctx, pipeline)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error executing aggregation: %v\n", err)
			return
		}
		defer cursor.Close(ctx)

		var results []bson.M
		if err = cursor.All(ctx, &results); err != nil {
			fmt.Fprintf(os.Stderr, "Error reading results: %v\n", err)
			return
		}

		if len(results) == 0 {
			fmt.Println("No results found.")
			return
		}

		resultsJSON, err := json.MarshalIndent(results, "", "  ")
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error marshalling results: %v\n", err)
			return
		}
		fmt.Println(string(resultsJSON))
	},
}

var vectorCmd = &cobra.Command{
	Use:   "vector <query>",
	Short: "Perform a vector search",
	Args:  cobra.ExactArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		query := args[0]
		configName, _ := cmd.Flags().GetString("config")
		verbose, _ := cmd.Flags().GetBool("verbose")

		var cfg *Config
		if configName != "" {
			var err error
			cfg, err = loadConfig(configName)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error loading configuration: %v\n", err)
				return
			}
		}

		// Create a default config if none loaded
		if cfg == nil {
			cfg = &Config{}
		}

		finalConfig, err := mergeConfigs(cfg, cmd)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error merging configurations: %v\n", err)
			return
		}

		if finalConfig.ConnectionString == "" || finalConfig.DB == "" || finalConfig.Coll == "" || finalConfig.Field == nil || len(finalConfig.Field) == 0 {
			fmt.Fprintf(os.Stderr, "Error: connectionString, db, coll, and field must be provided either via config or flags.\n")
			return
		}

		var embedding []float64
		embedWithVoyage, _ := cmd.Flags().GetBool("embedWithVoyage")
		if embedWithVoyage {
			voyageAPIKey := finalConfig.VoyageAPIKey
			if voyageAPIKey == "" {
				voyageAPIKey = os.Getenv("VOYAGE_API_KEY") // Fallback to environment variable
			}
			if voyageAPIKey == "" {
				fmt.Fprintf(os.Stderr, "Error: Voyage AI API key not provided. Set --voyageAPIKey flag, in config, or VOYAGE_API_KEY environment variable.\n")
				return
			}

			voyageModel, _ := cmd.Flags().GetString("voyageModel")
			if voyageModel == "" {
				voyageModel = finalConfig.VoyageModel
			}

			fmt.Println("Fetching embeddings from Voyage AI...")
			embedding, err = getEmbeddings(query, voyageAPIKey, voyageModel)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error getting embeddings from Voyage AI: %v\n", err)
				return
			}
			if verbose {
				fmt.Printf("Embedding: %v\n", embedding)
			}
		} else {
			// If not embedding, assume the query itself is the vector (e.g., comma-separated floats)
			var err error
			embedding, err = parseVectorString(query)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error parsing query as vector: %v\n", err)
				return
			}
			if verbose {
				fmt.Printf("Parsed Embedding: %v\n", embedding)
			}
		}

		client, err := getMongoClient(finalConfig.ConnectionString)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error connecting to MongoDB: %v\n", err)
			return
		}
		defer func() {
			if err = client.Disconnect(context.TODO()); err != nil {
				fmt.Fprintf(os.Stderr, "Error disconnecting from MongoDB: %v\n", err)
			}
		}()

		collection := client.Database(finalConfig.DB).Collection(finalConfig.Coll)

		numCandidates, _ := cmd.Flags().GetInt("numCandidates")
		limit, _ := cmd.Flags().GetInt("limit")

		// Apply numCandidates logic: 10x limit if limit is set and numCandidates is default
		if cmd.Flags().Changed("limit") && !cmd.Flags().Changed("numCandidates") {
			numCandidates = limit * 10
		}

		// Build the $vectorSearch stage
		vectorSearchStage := bson.D{{"$vectorSearch", bson.D{
			{"index", finalConfig.Index},
			{"path", finalConfig.Field[0]}, // Assuming single field for vector search as per README example
			{"queryVector", embedding},
			{"numCandidates", numCandidates},
			{"limit", limit},
		}}}

		// Build the $project stage
		projectStage := bson.D{{"$project", bson.D{}}}
		if len(finalConfig.ProjectField) > 0 {
			projectFields := bson.D{}
			for _, field := range finalConfig.ProjectField {
				projectFields = append(projectFields, bson.E{Key: field, Value: 1})
			}
			projectFields = append(projectFields, bson.E{Key: "_id", Value: 0}) // Exclude _id by default
			projectStage = bson.D{{"$project", projectFields}}
		}

		pipeline := mongo.Pipeline{vectorSearchStage, projectStage}

		if verbose {
			fmt.Println("MongoDB Aggregation Pipeline:")
			pipelineJSON, _ := json.MarshalIndent(pipeline, "", "  ")
			fmt.Println(string(pipelineJSON))
		}

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		cursor, err := collection.Aggregate(ctx, pipeline)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error executing aggregation: %v\n", err)
			return
		}
		defer cursor.Close(ctx)

		var results []bson.M
		if err = cursor.All(ctx, &results); err != nil {
			fmt.Fprintf(os.Stderr, "Error reading results: %v\n", err)
			return
		}

		if len(results) == 0 {
			fmt.Println("No results found.")
			return
		}

		resultsJSON, err := json.MarshalIndent(results, "", "  ")
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error marshalling results: %v\n", err)
			return
		}
		fmt.Println(string(resultsJSON))
	},
}

func init() {
	rootCmd.AddCommand(configCmd)
	configCmd.AddCommand(configSetCmd)
	configCmd.AddCommand(configListCmd)
	rootCmd.AddCommand(lexicalCmd)
	rootCmd.AddCommand(vectorCmd)

	// Add flags for configSetCmd
	configSetCmd.Flags().String("connectionString", "", "MongoDB connection string.")
	configSetCmd.Flags().String("db", "", "Database name.")
	configSetCmd.Flags().String("coll", "", "Collection name.")
	configSetCmd.Flags().String("index", "", "The name of the search index to use.")
	configSetCmd.Flags().StringArray("field", []string{}, "The field to search. Can be specified multiple times.")
	configSetCmd.Flags().StringArray("projectField", []string{}, "The field to project. Can be specified multiple times.")
	configSetCmd.Flags().String("voyageAPIKey", "", "The Voyage AI API key.")
	configSetCmd.Flags().String("voyageModel", "", "The Voyage AI model to use for embedding.")

	// Add flags for lexicalCmd
	lexicalCmd.Flags().String("config", "", "The name of the configuration to use.")
	lexicalCmd.Flags().StringArray("field", []string{}, "The field to search. Can be specified multiple times. Defaults to wildcard (*).")
	lexicalCmd.Flags().StringArray("projectField", []string{}, "The field to project. Can be specified multiple times.")
	lexicalCmd.Flags().String("index", "default", "The name of the search index to use. Defaults to default.")
	lexicalCmd.Flags().String("connectionString", "", "MongoDB connection string. Overrides the configured value.")
	lexicalCmd.Flags().String("db", "", "Database name. Overrides the configured value.")
	lexicalCmd.Flags().String("coll", "", "Collection name. Overrides the configured value.")
	lexicalCmd.Flags().Bool("verbose", false, "Enable verbose logging.")

	// Add flags for vectorCmd
	vectorCmd.Flags().String("config", "", "The name of the configuration to use.")
	vectorCmd.Flags().String("field", "", "The field to search for vectors. This is a required argument.")
	vectorCmd.MarkFlagRequired("field") // Mark field as required for vectorCmd
	vectorCmd.Flags().StringArray("projectField", []string{}, "The field to project. Can be specified multiple times.")
	vectorCmd.Flags().String("index", "vector_index", "The name of the search index to use. Defaults to vector_index.")
	vectorCmd.Flags().Int("numCandidates", 100, "Number of candidates to consider for approximate vector search.")
	vectorCmd.Flags().Int("limit", 10, "Number of results to return.")
	vectorCmd.Flags().Bool("embedWithVoyage", false, "Embed the query with Voyage AI.")
	vectorCmd.Flags().String("voyageModel", "voyage-3.5", "The Voyage AI model to use for embedding.")
	vectorCmd.Flags().String("voyageAPIKey", "", "The Voyage AI API key.")
	vectorCmd.Flags().String("connectionString", "", "MongoDB connection string. Overrides the configured value.")
	vectorCmd.Flags().String("db", "", "Database name. Overrides the configured value.")
	vectorCmd.Flags().String("coll", "", "Collection name. Overrides the configured value.")
	vectorCmd.Flags().Bool("verbose", false, "Enable verbose logging.")
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func main() {
	Execute()
}
