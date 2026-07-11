.PHONY: local test deploy deploy-cli package clean

local:
	python3 local_server.py

local-bedrock:
	USE_BEDROCK=1 AWS_REGION=ap-southeast-2 python3 local_server.py

test:
	python3 -m unittest discover -s tests -v

package:
	cd src && zip -q /tmp/threetoday-lambda.zip lambda_function.py
	@echo "Package: /tmp/threetoday-lambda.zip"

deploy:
	cd infra && ./deploy.sh

deploy-cli:
	cd infra && ./deploy-cli.sh

clean:
	rm -f /tmp/threetoday-lambda.zip
	rm -rf .aws-sam __pycache__ src/__pycache__ tests/__pycache__
