# Makefile for Nursingpod Deployment

.PHONY: help build push deploy-cloudrun deploy-k8s test-docker clean

PROJECT_ID ?= sanaths-projects
REGION ?= us-central1
IMAGE_NAME = gcr.io/$(PROJECT_ID)/nursingpod-app
SERVICE_NAME = nursingpod-app

help: ## Show this help message
	@echo 'Usage:'
	@echo '  make build              - Build Docker image'
	@echo '  make push               - Push image to GCR'
	@echo '  make deploy-cloudrun    - Deploy to Cloud Run'
	@echo '  make deploy-k8s         - Deploy to Kubernetes'
	@echo '  make test-docker        - Test Docker image locally'
	@echo '  make clean              - Clean up local resources'

build: ## Build Docker image
	docker build --network=host -t $(IMAGE_NAME):latest .
	docker tag $(IMAGE_NAME):latest $(IMAGE_NAME):$(shell date +%Y%m%d-%H%M%S)

push: ## Push image to Google Container Registry
	docker push $(IMAGE_NAME):latest

deploy-cloudrun: push ## Deploy to Cloud Run
	@cd cloudrun && ./deploy.sh

deploy-k8s: push ## Deploy to Kubernetes
	@echo "Updating deployment with latest image..."
	kubectl set image deployment/nursingpod-app app=$(IMAGE_NAME):latest
	kubectl rollout status deployment/nursingpod-app

test-docker: ## Test Docker image locally
	docker run --rm -p 8080:8080 \
		-e FLASK_ENV=development \
		-e PORT=8080 \
		$(IMAGE_NAME):latest

clean: ## Clean up local Docker resources
	docker rmi $(IMAGE_NAME):latest || true

login-gcr: ## Login to Google Container Registry
	gcloud auth configure-docker

setup-project: ## Set up GCP project for deployment
	@echo "Setting up GCP project: $(PROJECT_ID)"
	gcloud config set project $(PROJECT_ID)
	gcloud services enable run.googleapis.com
	gcloud services enable containerregistry.googleapis.com
	gcloud services enable secretmanager.googleapis.com
	gcloud services enable container.googleapis.com
	@echo "✅ Project setup complete!"

