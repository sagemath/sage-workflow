# Author: Christopher Swenson (chris@caswenson.com, @swenson)
#
# Requires libgit2 installed. In OS X, this is as easy as:
#  brew install libgit2
#
# Run with:
#  ./run pr_export.py

import json
import os
import re
import requests
import time

from pygit2 import Repository, GIT_SORT_TIME

# Settings
TRAC_UI = ''
TRAC_REALM = 'sage.math.washington.edu'
TRAC_HTTP = "http://trac.sagemath.org/sage_trac"
TRAC_USERNAME = 'swenson'
TRAC_PASSWORD = open(os.environ['HOME'] + '/.sagetracpw').read().strip()
GITHUB_USERNAME = 'sageb0t'
GITHUB_PASSWORD = open(os.environ['HOME'] + '/.sagegitpw').read().strip()
GITHUB_URL = "https://api.github.com/"
GITHUB_REPO = "testsage"
GIT_REPO = os.environ['HOME'] + '/sage-src/sage-git'

trac_to_github_user_mapping = {
#  'was': 'williamstein',
#  'swenson': 'swenson'
}

github_rate_limit_per_hour = 5000.0
github_sleep = 1.0 / (github_rate_limit_per_hour / 60.0 / 60.0)

# Poor programmer's rate limit
def rate_limit():
  time.sleep(github_sleep)

def github_create_pr(title, body, base, head):
  rate_limit()
  data = {
    'title': title,
    'body': body,
    'base': base,
    'head': head
  }
  resp = requests.post(GITHUB_URL + 'repos/%s/%s/pulls' % (GITHUB_USERNAME, GITHUB_REPO),
    data=json.dumps(data),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  print resp.json()
  return resp.json()['number']

repo = Repository(GIT_REPO)

for commit in repo.walk(repo.head.oid, GIT_SORT_TIME):
  if '#' in commit.message:
    if len(commit.parents) != 1:
      continue
    base = commit.parents[0].hex
    head = commit.hex
    title = commit.message
    body = "PR for issues %s" % (', '.join(re.findall('#[0-9]+', title)))
    github_create_pr(title, body, base, head)

