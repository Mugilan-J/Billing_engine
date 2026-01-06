package pricing

import (
	"database/sql"
	"fmt"
)

func GetCostForModel(db *sql.DB, provider string, model string, inputtokens int, outputtokens int) (float64, error) {

	var costin1k, costoutt1k float64
	err := db.QueryRow(
		`select cost_input_per_1k_tokens, cost_output_per_1k_tokens from pricing_models where provider=$1 and model=$2 and active=true
		`, provider, model).Scan(&costin1k, &costoutt1k)
	if err != nil {
		return 0, fmt.Errorf("No cost found for model %s and provider %s", model, provider)
	}
	costin := (float64(inputtokens) / 1000.0) * costin1k
	costuot := (float64(outputtokens) / 1000.0) * costoutt1k
	return costin + costuot, nil
}
