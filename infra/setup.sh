#!/usr/bin/env bash
set -euo pipefail

RG="rg-forecast-benchmark"
LOCATION="swedencentral"
WORKSPACE="mlw-forecast-benchmark"
COMPUTE_INSTANCE="ci-forecast-dev"
COMPUTE_CLUSTER="cc-forecast-batch"
VM_SIZE="STANDARD_E4DS_V4"

echo "=== 1. Register ML provider ==="
az provider register --namespace Microsoft.MachineLearningServices --wait

echo "=== 2. Create resource group ==="
az group create --name "$RG" --location "$LOCATION"

echo "=== 3. Create Azure ML workspace ==="
az ml workspace create --name "$WORKSPACE" --resource-group "$RG" --location "$LOCATION"

echo "=== 4. Set CLI defaults ==="
az configure --defaults group="$RG" workspace="$WORKSPACE"

echo "=== 5. Create Compute Instance ==="
az ml compute create \
  --name "$COMPUTE_INSTANCE" \
  --type ComputeInstance \
  --size "$VM_SIZE"

echo "=== 6. Create Compute Cluster ==="
az ml compute create \
  --name "$COMPUTE_CLUSTER" \
  --type AmlCompute \
  --size "$VM_SIZE" \
  --min-instances 0 \
  --max-instances 4 \
  --tier dedicated

echo "=== 7. Create environment ==="
az ml environment create \
  --name forecast-benchmark-env \
  --conda-file benchmark/code/environment.yaml \
  --image mcr.microsoft.com/azureml/curated/minimal-ubuntu22.04-py311:latest

echo ""
echo "=== Done ==="
echo "MLflow tracking URI:"
az ml workspace show --query mlflow_tracking_uri -o tsv
