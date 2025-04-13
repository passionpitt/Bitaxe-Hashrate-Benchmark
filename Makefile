SHELL := /bin/bash

.PHONY: all run build

project-name := bitaxe-hashrate-benchmark
image-name := $(project-name):latest

all: greet

run:
	@if [ -z "$(ip)" ]; then \
		echo "Error: You must provide an 'ip' (e.g. make run ip=192.168.1.10 -v=1200 -f=550)"; \
		exit 1; \
	fi && \
	echo "Start $(project-name) Service with IP=$(ip), Voltage=$(v), Frequency=$(f):" && \
	docker run --rm $(image-name) $(ip) -v $(v) -f $(f)

build:
	@echo "Build $(project-name) image:" && \
	docker image build -t $(image-name) .

greet:
	@echo "Welcome to the $(project-name) project!"
