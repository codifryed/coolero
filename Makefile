.DEFAULT_GOAL := build-appimage
docker_image_tag := v1
pr := poetry run

.PHONY: run help version debug lint test build build-one-file build-appimage build-clean install \
	docker-clean docker-build docker-login docker-push docker-images docker-run \
	bump release

# STANDARD commands:
####################
run:
	@$(pr) coolero

help:
	@echo Possible make targets:
	@LC_ALL=C $(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

version:
	@$(pr) coolero -v
	@echo "Poetry project version: " $(shell poetry version -s)

debug:
	@$(pr) coolero --debug

lint:
	@$(pr) lint

test:
	@$(pr) test

build:
	@$(pr) build

build-one-file:
	@$(pr) build-one-file

build-appimage:
	@$(pr) build
	@rm -f coolero.bin
	@rm -f Coolero*.AppImage*
	@mkdir -p coolero.dist/usr/share/applications
	@cp .appimage/coolero.desktop coolero.dist/usr/share/applications
	@cp .appimage/coolero.desktop coolero.dist
	@mkdir -p coolero.dist/usr/share/icons/hicolor/scalable/apps
	@cp .appimage/coolero.svg coolero.dist/usr/share/icons/hicolor/scalable/apps
	@mkdir -p coolero.dist/usr/share/icons/hicolor/256x256/apps
	@cp .appimage/coolero.png coolero.dist/usr/share/icons/hicolor/256x256/apps
	@cp .appimage/coolero.png coolero.dist
	@mkdir -p coolero.dist/usr/share/metainfo
	@cp .appimage/coolero.appdata.xml coolero.dist/usr/share/metainfo
	@cp .appimage/AppImageUpdate-x86_64.AppImage coolero.dist/AppImageUpdate
	@mv coolero.dist/coolero coolero.dist/Coolero
	@ln -s coolero.png coolero.dist/.DirIcon
	@cp .appimage/AppRun coolero.dist/AppRun
	@.appimage/appimagetool-x86_64.AppImage -n -u "zsync|https://coolero.org/releases/latest/Coolero-x86_64.AppImage.zsync" --comp=xz --sign coolero.dist Coolero-x86_64.AppImage

build-clean:
	@rm -r build
	@rm -r dist

#install:
#	@#.appimage/linuxdeploy-x86_64.AppImage --appdir=coolero.dist --desktop-file=.appimage/coolero.desktop --icon-file=.appimage/coolero.png


# VERSION bumping:
##################
# Valid version arguments are:
# a valid semver string or a valid bump rule: patch, minor, major, prepatch, preminor, premajor, prerelease
# examples:
#  make bump v=minor
#  make bump v=1.2.3
v = "patch"
bump:
	@./scripts/version_bump.sh $(v)

# version from bump above applies to release as well:
release: bump
	@./scripts/release.sh


# CI DOCKER Image commands:
#####################
docker-build:
	@docker build -t registry.gitlab.com/codifryed/coolero/pipeline:$(docker_image_tag) .gitlab/

docker-login:
	@docker login registry.gitlab.com

docker-push:
	@docker push registry.gitlab.com/codifryed/coolero/pipeline:$(docker_image_tag)

docker-run:
	@docker run --name coolero-ci -v `pwd`:/app/coolero -i -t registry.gitlab.com/codifryed/coolero/pipeline:$(docker_image_tag) bash

docker-clean:
	@docker rm coolero-ci
	@docker rmi registry.gitlab.com/codifryed/coolero/pipeline:$(docker_image_tag)

docker-images:
	@docker images
