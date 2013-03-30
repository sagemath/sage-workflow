# Author: Christopher Swenson (chris@caswenson.com, @swenson)
#
# Run with:
#  ./run issue_export.py

import json
import os
import re
import requests
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

trac_to_github_user_mapping = {
  'was': 'williamstein',
  'swenson': 'swenson'
}


trac = TracInterface(UI=TRAC_UI, realm=TRAC_REALM, trac=TRAC_HTTP, username=TRAC_USERNAME, password=TRAC_PASSWORD)
#print trac._tracserver.system.listMethods()

# This grabs all tickets
#tickets = sorted(trac._tracserver.ticket.query('max=0'))
tickets = range(13000, 13010)


# Milestones

def github_get_milestones():
  resp = requests.get(GITHUB_URL + 'repos/%s/%s/milestones?state=open' % (GITHUB_USERNAME, GITHUB_REPO),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD)).json() + \
    requests.get(GITHUB_URL + 'repos/%s/%s/milestones?state=closed' % (GITHUB_USERNAME, GITHUB_REPO),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD)).json()
  milestones = {}
  for m in resp:
    milestones[m['title']] = m['number']
  return milestones

def github_create_milestone(title):
  data = { 'title': title }
  resp = requests.post(GITHUB_URL + 'repos/%s/%s/milestones' % (GITHUB_USERNAME, GITHUB_REPO),
    data=json.dumps(data),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  resp = resp.json()
  return resp['number']


# Labels

def github_get_labels():
  resp = requests.get(GITHUB_URL + 'repos/%s/%s/labels' % (GITHUB_USERNAME, GITHUB_REPO),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  resp = resp.json()
  return set([r['name'] for r in resp])

def github_create_label(name):
  data = { 'name': name }
  resp = requests.post(GITHUB_URL + 'repos/%s/%s/labels' % (GITHUB_USERNAME, GITHUB_REPO),
    data=json.dumps(data),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  return


# Issues

def github_create_issue(title, body, assignee=None, milestone=None, labels=None):
  data = {
    'title': title,
    'body': body
  }
  if assignee:
    data['assignee'] = assignee
  if milestone:
    data['milestone'] = milestone
  if labels:
    data['labels'] = labels
  resp = requests.post(GITHUB_URL + 'repos/%s/%s/issues' % (GITHUB_USERNAME, GITHUB_REPO),
    data=json.dumps(data),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  return resp

def github_close_issue(num):
  data = {
    'state': 'closed',
  }
  resp = requests.patch(GITHUB_URL + 'repos/%s/%s/issues/%d' % (GITHUB_USERNAME, GITHUB_REPO, num),
    data=json.dumps(data),
    auth=(GITHUB_USERNAME, GITHUB_PASSWORD))
  return


# Convert wiki syntax

def fix_wiki_syntax(body, trac_num):
  body = body.replace('{{{', '```').replace('}}}', '```')
  body = body.replace("'''''", '***')
  body = body.replace("'''", "**")
  body = body.replace("''", "*")

  # Find ticket numbers in the body.
  body = re.sub(r'#([0-9]+)', r'<a href="http://trac.sagemath.org/sage_trac/ticket/\1">trac #\1</a>', body)

  # Find attachment references in the body.
  body = re.sub(r'\[attachment:(.*)\]', '[<a href="http://trac.sagemath.org/sage_trac/attachment/ticket/%d/\\1">attachement: \\1</a>]' % trac_num, body)

  return body


# Convert a Trac ticket object and attachments to a GitHub issue.

def convert(trac_ticket, attachments, milestones, all_labels):
  num, updated, created, props = trac_ticket

  # Extract fields
  status = props['status']
  changetime = props['changetime']
  description = props['description']
  reporter = props['reporter']
  cc = props['cc']
  typ = props['type'] # e.g., enhancement
  milestone = props['milestone']
  author = props['author']
  component = props['component']
  summary = props['summary']
  priority = props['priority']
  owner = props['owner']
  dependencies = props['dependencies']
  time = props['time']
  keywords = props['keywords']
  reviewer = props['reviewer']
  upstream = props['upstream']
  resolution = props['resolution']
  merged = props['merged']
  work_issues = props['work_issues']

  # Fix labels
  labels = set()
  labels.add("priority_%s" % priority)
  for kw in keywords.split():
    labels.add(kw)
  labels.add(typ)
  labels.add(resolution)

  # Remove empty labels
  labels = set([x for x in labels if x])

  for label in labels:
    if label not in all_labels:
      github_create_label(label)
      all_labels.add(label)

  labels = list(labels)

  # Fix milestone
  if milestone not in milestones:
    milestones[milestone] = github_create_milestone(milestone)

  milestone_num = milestones[milestone]

  # Fix description
  description = fix_wiki_syntax(description, num)

  # Fix usernames
  assignee = None
  if owner in trac_to_github_user_mapping:
    assignee = trac_to_github_user_mapping[owner]

  if reporter in trac_to_github_user_mapping:
    reporter = '@' + trac_to_github_user_mapping[reporter]

  # Fix CC list
  github_cc = []
  for x in cc.split():
    if x in trac_to_github_user_mapping:
      x = '@' + trac_to_github_user_mapping[x]
    github_cc.append(x)
  cc = ', '.join(github_cc)

  # Construct attachments blob
  attachments_html = "<ol>"
  for attachment in attachments:
    fname, description, _, date, author = attachment
    if author in trac_to_github_user_mapping:
      author = '@' + trac_to_github_user_mapping[author]

    attachments_html += "<li>"
    attachments_html += '<a href="http://trac.sagemath.org/sage_trac/attachment/ticket/%d/%s">' % (num, fname)
    attachments_html += '%s: %s' % (fname, description)
    attachments_html += '</a> by %s at %s' % (author, date)
    attachments_html += '</li>'
  attachments_html += '</ol>'

  # Fix dependencies
  dependencies = [x.strip()[1:] for x in dependencies.split(',')]
  dependencies = [x for x in dependencies if x]
  dependencies = ', '.join(['<a href="http://trac.sagemath.org/sage_trac/ticket/%s">trac #%s</a>' % (x, x) for x in dependencies])

  body = """Imported from <a href="http://trac.sagemath.org/sage_trac/ticket/%d">trac #%d</a>.

%s

Reported by: %s

Component: %s

CC: %s

Report Upstream: %s

Authors: %s

Dependencies: %s

Work issues: %s

Reviewers: %s

Merged in: %s

Attachments: %s""" % (num, num, description, reporter, component, cc, upstream, author, dependencies, work_issues, reviewer, merged, attachments_html)

  resp = github_create_issue(title=summary, body=body, assignee=assignee, milestone=milestone_num, labels=labels)
  if resp.status_code == 201:
    if status == 'closed':
      github_close_issue(resp.json()['number'])
  return resp.json()['number']


all_labels = github_get_labels()
milestones = github_get_milestones()
milestones = github_get_milestones()

for ticket in tickets:
  print "Converting trac %d ->" % ticket,
  trac_ticket = trac._tracserver.ticket.get(ticket)
  attachments = trac._tracserver.ticket.listAttachments(ticket)
  issue = convert(trac_ticket, attachments, milestones, all_labels)
  print issue


