.PHONY: install test lint pipeline resume docker-build clean

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt
	python -m pip install -e .

test:
	pytest

lint:
	ruff check src tests

pipeline:
	nextflow run main.nf \
		-with-report results/execution_report.html \
		-with-timeline results/execution_timeline.html \
		-with-trace results/execution_trace.txt \
		-with-dag results/execution_dag.html

resume:
	nextflow run main.nf -resume

docker-build:
	docker build -t scientific-data-platform:0.1.0 .

clean:
	rm -rf results work .nextflow .nextflow.log*
