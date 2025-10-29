# -*- coding: utf-8 -*-
import os, sys, base64, requests, time
OWNER='chekdata'
REPO_CICD='CICD'
PATH_AUTODETECT='.github/workflows/yapi-sync-autodetect.yml'
# Load local reusable content
with open('/Users/jasonhong/Desktop/CICD/.github/workflows/yapi-sync-autodetect.yml','r') as f:
  AUTODETECT=f.read()
# Service repos to update
REPOS=['vehicle-model-service','osm-gateway']
GH_PAT=os.environ.get('GH_PAT')
if not GH_PAT:
  print('Missing GH_PAT', file=sys.stderr); sys.exit(2)
S=requests.Session(); S.headers.update({'Authorization': f'Bearer {GH_PAT}', 'Accept':'application/vnd.github+json'})
API='https://api.github.com'

def ensure_org_repo(owner, name):
  r=S.get(f'{API}/repos/{owner}/{name}')
  if r.status_code==200: return True
  if r.status_code==404:
    r2=S.post(f'{API}/orgs/{owner}/repos', json={'name': name, 'private': False, 'auto_init': True, 'description':'Shared CI workflows'})
    if r2.status_code in (201,): return True
    raise Exception(f'create repo failed {r2.status_code} {r2.text}')
  r.raise_for_status()

def put_file(owner, repo, path, content, message, branch='main'):
  b64=base64.b64encode(content.encode('utf-8')).decode('ascii')
  # get to see if exists
  r=S.get(f'{API}/repos/{owner}/{repo}/contents/{path}', params={'ref': branch})
  if r.status_code==200:
    sha=r.json().get('sha')
    r2=S.put(f'{API}/repos/{owner}/{repo}/contents/{path}', json={'message': message, 'content': b64, 'branch': branch, 'sha': sha})
    if r2.status_code not in (200,201): raise Exception(r2.text)
  else:
    r2=S.put(f'{API}/repos/{owner}/{repo}/contents/{path}', json={'message': message, 'content': b64, 'branch': branch})
    if r2.status_code not in (200,201): raise Exception(r2.text)

# 1) publish autodetect reusable to CICD repo (main)
ensure_org_repo(OWNER, REPO_CICD)
put_file(OWNER, REPO_CICD, PATH_AUTODETECT, AUTODETECT, 'chore(ci): add yapi-sync-autodetect reusable')
print('Published reusable to chekdata/CICD')

# 2) Update service repos yapi-sync.yml to use autodetect
NEW_WF='''name: yapi-sync

on:
  push:
    branches: [ main, dev, staging ]
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'

jobs:
  select-token:
    runs-on: ubuntu-latest
    outputs:
      token: ${{ steps.sel.outputs.token }}
    steps:
      - id: sel
        run: |
          if [[ "${{ github.ref_name }}" == "main" ]]; then
            echo "token=${{ secrets.YAPI_TOKEN }}" >> "$GITHUB_OUTPUT"
          elif [[ "${{ github.ref_name }}" == "staging" ]]; then
            echo "token=${{ secrets.YAPI_TOKEN_STG }}" >> "$GITHUB_OUTPUT"
          else
            echo "token=${{ secrets.YAPI_TOKEN_DEV }}" >> "$GITHUB_OUTPUT"
          fi

  autodetect-and-import:
    needs: select-token
    runs-on: ubuntu-latest
    steps:
      - name: Call autodetect reusable
        uses: chekdata/.github/.github/workflows/yapi-sync-autodetect.yml@main
        with:
          dockerfile: Dockerfile
          context: .
          ports: '80,3000,8080,4010,8090'
          paths: '/openapi.json,/v3/api-docs,/v2/api-docs,/swagger.json,/swagger/doc.json'
        secrets:
          YAPI_BASE: ${{ secrets.YAPI_BASE }}
          YAPI_TOKEN: ${{ needs.select-token.outputs.token }}
'''

BRANCH='chore/yapi-sync-autodetect'
for repo in REPOS:
  # create branch from default
  r=S.get(f'{API}/repos/{OWNER}/{repo}')
  r.raise_for_status()
  default_branch=r.json()['default_branch']
  head=S.get(f'{API}/repos/{OWNER}/{repo}/git/ref/heads/{default_branch}')
  head.raise_for_status(); sha=head.json()['object']['sha']
  S.post(f'{API}/repos/{OWNER}/{repo}/git/refs', json={'ref':f'refs/heads/{BRANCH}','sha':sha})
  # put workflow file
  put_file(OWNER, repo, '.github/workflows/yapi-sync.yml', NEW_WF, 'chore(ci): switch to autodetect yapi sync', branch=BRANCH)
  # open PR and merge
  pr=S.post(f'{API}/repos/{OWNER}/{repo}/pulls', json={'title':'chore(ci): YApi sync autodetect','head':BRANCH,'base':default_branch,'body':'Use autodetect reusable to fetch swagger and import to YApi'})
  if pr.status_code in (200,201):
    num=pr.json()['number']
    m=S.put(f'{API}/repos/{OWNER}/{repo}/pulls/{num}/merge', json={'merge_method':'squash'})
    print('Updated workflow', repo, m.status_code)
  else:
    print('PR failed', repo, pr.status_code, pr.text)

# 3) Trigger on main
for repo in REPOS:
  # find workflow id
  r=S.get(f'{API}/repos/{OWNER}/{repo}/actions/workflows')
  wid=None
  if r.status_code==200:
    for wf in r.json().get('workflows', []):
      if wf.get('path')=='.github/workflows/yapi-sync.yml': wid=wf.get('id'); break
  if wid:
    d=S.post(f'{API}/repos/{OWNER}/{repo}/actions/workflows/{wid}/dispatches', json={'ref':'main'})
    print('dispatched', repo, d.status_code)
