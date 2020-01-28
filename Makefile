TRAVIS_BRANCH ?= $(shell git branch| grep \* | cut -d' ' -f2)
BRANCH=$(TRAVIS_BRANCH)

flags=.makeFlags
VPATH=$(flags)
$(shell mkdir -p $(flags))

dockerRepo=hashcloak
katzenServerRepo=https://github.com/katzenpost/server
katzenServerTag=$(shell git ls-remote --heads $(katzenServerRepo) | grep master | cut -c1-7)
katzenServer=$(dockerRepo)/katzenpost-server:$(katzenServerTag)
mesonServer=$(dockerRepo)/Meson

messagePush=echo "LOG: Image already exists in docker.io/$(dockerRepo). Not pushing: "
messagePull=echo "LOG: Success in pulling image: "
imageNotFound=echo "LOG: Image not found... building: "

clean:
	rm -rf /tmp/server
	rm -rf $(flags)

pull-katzen-server:
	docker pull $(katzenServer) && $(messagePull)$(katzenServer) \
		|| ($(imageNotFound)$(katzenServer) && $(MAKE) build-katzen-server)
	@touch $(flags)/$@

push: push-katzen-server push-meson

push-katzen-server:
	docker push $(katzenServer) && $(messagePush)$(katzenServer) \
		|| ($(imageNotFound)$(katzenServer) && \
				$(MAKE) build-katzen-server; docker push $(katzenServer))

push-meson: build-meson
	docker push '$(mesonServer):$(BRANCH)'

build: build-katzen-server build-meson

build-katzen-server:
	git clone $(katzenServerRepo) /tmp/server || git --git-dir=/tmp/server/.git --work-tree=/tmp/server pull origin master
	docker build -f /tmp/server/Dockerfile -t $(katzenServer) /tmp/server
	@touch $(flags)/$@

build-meson: pull-katzen-server
	sed 's|%%KATZEN_SERVER%%|$(katzenServer)|g' ./Dockerfile > /tmp/meson.Dockerfile
	docker build -f /tmp/meson.Dockerfile -t $(mesonServer):$(BRANCH) .
	@touch $(flags)/$@

test:
	go test ./pkg/*