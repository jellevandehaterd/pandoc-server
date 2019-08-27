VERSION = 2.7.3
REGISTRY = andromeda.docker.ing.net
DFILE := Dockerfile.alpine
IMAGE_NAME = pandoc-server

build:
	@echo ""
	docker build -t ${REGISTRY}/${IMAGE_NAME}:${VERSION} -t ${IMAGE_NAME}:${VERSION} \
		-f ${DFILE} .
	@if docker images ${REGISTRY}/${IMAGE_NAME}:${VERSION}; then touch build; fi

run:
	@echo ""
	docker run -it --rm -v $(shell pwd)/config:/config --init -p 8080:8080 -e PANDOC_SERVER_CONFIG=/config/api.dev.yml pandoc-server run -vvv

run.background:
	@echo ""
	docker run -it -d --name ${IMAGE_NAME} -v $(shell pwd)/config:/config --init -p 8080:8080 -e PANDOC_SERVER_CONFIG=/config/api.dev.yml pandoc-server run -vvv
