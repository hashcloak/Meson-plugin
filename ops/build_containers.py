from os import path, curdir
from subprocess import run
from tempfile import gettempdir
import urllib.request
from json import loads

from config import CONFIG
from utils import log, checkoutRepo

dockerApiUrl="https://hub.docker.com/v2/repositories"

def doesContainerExistsInCloud(name: str, tag: str) -> bool:
    try:
        urllib.request.urlopen("{}/{}/tags/{}".format(dockerApiUrl, name, tag)).read()
        return True
    except urllib.error.HTTPError:
        return False

def getContainerInfo(name: str, tag: str) -> str:
    if doesContainerExistsInCloud(name, tag):
        url = "{}/{}/tags/{}".format(dockerApiUrl, name, tag)
        return loads(urllib.request.urlopen(url).read().decode())
        
    raise urllib.error.URLError('Container {}:{} not found in registry'.format(name, tag))

def compareRemoteContainers(containerOne: str, containerTwo: str) -> bool:
    try:
        info1 = getContainerInfo(containerOne.split(":")[0], containerOne.split(":")[1])
        info2 = getContainerInfo(containerTwo.split(":")[0], containerTwo.split(":")[1])
        return info1['images'][0]['digest'] == info2['images'][0]['digest']
    except urllib.error.URLError as e:
        log(e.reason)
        return False

def buildContainer(container: str, tag: str, dockerFile: str, path: str) -> None:
    log("Building {}:{}".format(container, tag))
    args = [
        "docker",
        "build",
        "-t",
        "{}:{}".format(container, tag),
        "-f",
        dockerFile,
        path,
    ]
    if CONFIG["WARPED"]:
        args.extend([
            "--build-arg",
            "warped=true",
            "--build-arg",
            "server={}".format(CONFIG["REPOS"]["SERVER"]["NAMEDTAG"])
        ])
    log(args)
    run(args, check=True)

def reTag(container: str, tag1: str, tag2: str) -> None:
    log("Tagging container {} with {} -> {}".format(container, tag1, tag2))
    run([
        "docker",
        "tag",
        "{}:{}".format(container, tag1),
        "{}:{}".format(container, tag2)
    ], check=True)

def main():
    # The sorted ensures that server gets built before meson
    for _, repo in sorted(CONFIG["REPOS"].items(), reverse=True):
        areEqual = compareRemoteContainers(
            "{}:{}".format(repo["CONTAINER"], repo["NAMEDTAG"]),
            "{}:{}".format(repo["CONTAINER"], repo["HASHTAG"])
        )
        log("Container {} tags digests are: {} {} {}".format(
            repo["CONTAINER"],
            repo["HASHTAG"],
            "==" if areEqual else "!=",
            repo["NAMEDTAG"],
        ))

        if areEqual and not CONFIG["BUILD"]:
            log("Pulling container: {}:{}".format(repo["CONTAINER"], repo["NAMEDTAG"]))
            run(["docker", "pull", "{}:{}".format(repo["CONTAINER"], repo["NAMEDTAG"])], check=True)
        else:
            if "meson" in repo["CONTAINER"]:
                repoPath = curdir
            else:
                repoPath = path.join(gettempdir(), repo["CONTAINER"].split("/")[-1])
                checkoutRepo(repoPath, repo["REPOSITORY"], repo["GITHASH"])

            dockerFile = path.join(repoPath, "Dockerfile")
            if "authority" in repo["CONTAINER"]:
                dockerFile = path.join(repoPath, "Dockerfile.nonvoting")

            buildContainer(repo["CONTAINER"], repo["HASHTAG"], dockerFile, repoPath)
            reTag(repo["CONTAINER"], repo["HASHTAG"], repo["NAMEDTAG"])

main()
