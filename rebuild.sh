!#/bin/sh
#since don't published a docker images yet, using this to build my docker image.
git pull
docker stop pe
docker container rm pe
docker image rm emby2podcasts
docker build . -t emby2podcasts
docker run -p 8880:8099 -v /root/config/:/config/ --name pe -d emby2podcasts