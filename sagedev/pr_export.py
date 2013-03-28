# Author: Christopher Swenson (chris@caswenson.com, @swenson)
#
# Requires libgit2 installed. In OS X, this is as easy as:
#  brew install libgit2
#
# On ubuntu: https://gist.github.com/Problematic/1794222
#
# Run with:
#  ./run pr_export.py

import json
import os
import re
import requests
import time
from pygit2 import Repository, GIT_SORT_TIME
from sagedev import TracInterface

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

trac = TracInterface(UI=TRAC_UI, realm=TRAC_REALM, trac=TRAC_HTTP, username=TRAC_USERNAME, password=TRAC_PASSWORD)

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
  return resp

def github_create_pr_issue(issue, base, head):
  rate_limit()
  data = {
    'issue': issue,
    'base': base,
    'head': head
  }
  resp = requests.post(GITHUB_URL + 'repos/%s/%s/pulls' % (GITHUB_USERNAME, GITHUB_REPO),
    data=json.dumps(data),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  print resp.json()
  return resp

def github_create_branch(branch, sha):
  data = {
    'ref': 'refs/heads/' + branch,
    'sha': sha
  }
  resp = requests.post(GITHUB_URL + 'repos/%s/%s/git/refs' % (GITHUB_USERNAME, GITHUB_REPO),
    data=json.dumps(data),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  return resp


def get_attachement(num, attachment):
  url = TRAC_HTTP + "/raw-attachment/ticket/%d/%s" % (num, attachment)
  print url
  resp = requests.get(url)
  print resp.status_code
  if resp.status_code == 200:
    return resp.text
  return None


repo = Repository(GIT_REPO)

for commit in repo.walk(repo.head.oid, GIT_SORT_TIME):
  tickets = re.findall('#[0-9]+', commit.message)
  if tickets:
    if len(commit.parents) != 1:
      continue
    base = commit.parents[0].hex
    head = commit.hex
    title = commit.message
    ticket = tickets[0][1:]
    body = "PR for issue #%s" % (ticket)
    trac_ticket = trac._tracserver.ticket.get(ticket)
    num, updated, created, props = trac_ticket
    if props['status'] != 'closed':
      continue
    print commit.message
    branch = 'issue_branch_' + ticket
    resp = github_create_branch(branch, base)
    print 'branch', resp.status_code
    resp = github_create_pr_issue(ticket, GITHUB_USERNAME + ':' + branch, head)
    print 'pr_issue', resp.status_code

