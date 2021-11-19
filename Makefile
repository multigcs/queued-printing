
all: docker-image docker-run

docker-image:
	docker build -t queued-printing .

docker-run: docker-stop
	docker run -ti -dp 5000:5000 -v config:/app/config -v jobs:/app/jobs --name queued-printing queued-printing

docker-stop:
	docker stop  queued-printing || true
	docker rm -f queued-printing || true


