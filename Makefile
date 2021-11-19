
all: docker-image docker-run

docker-image:
	docker build -t queued-printing .


docker-run:
	docker run -ti -dp 5000:5000 -v config:/app/config -v jobs:/app/jobs queued-printing

