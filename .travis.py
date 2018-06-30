#!/usr/bin/env python3
import os, urllib.parse, sys, subprocess

if 'TRAVIS_REPO_SLUG' not in os.environ:
    sys.exit("sorry, this script works on travis-ci.org only")

repo = os.environ['TRAVIS_REPO_SLUG']
ref = os.environ['TRAVIS_COMMIT']
if 'TRAVIS_PULL_REQUEST' in os.environ:
    print("pull request found")
    ref = "pr/%s/merge" % os.environ['TRAVIS_PULL_REQUEST']

print("running test for repo %s and ref %s" % (repo, ref))
url = "http://badge.marekventur.com/check?%s" % urllib.parse.urlencode({'repo':repo, 'ref':ref})
print(url)
result = subprocess.run(["curl", url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
data = result.stdout.decode('utf-8')
print(data)
if "\"errors\"" in data:
    sys.exit("Error found, failing build")

