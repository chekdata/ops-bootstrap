# -*- coding: utf-8 -*-
import os, sys, base64, requests
OWNER='chekdata'
REPOS=['vehicle-model-service','osm-gateway']
GH_PAT=os.environ.get('GH_PAT')
if not GH_PAT:
  print('Missing GH_PAT', file=sys.stderr); sys.exit(2)
S=requests.Session(); S.headers.update({'Authorization': f'Bearer {GH_PAT}', 'Accept':'application/vnd.github+json'})
API='https://api.github.com'
BRANCH='chore/yapi-sync-url'
PATH='.github/workflows/yapi-sync.yml'

NEW_CONTENT='''name: yapi-sync

on:
  push:
    branches: [ main, dev, staging ]
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'

jobs:
  build-and-export-swagger:
    runs-on: ubuntu-latest
    outputs:
      swagger_path: ${{ steps.out.outputs.path }}
    steps:
      - uses: actions/checkout@v4
      - name: Generate Swagger (project-specific)
        run: |
          set -e
          mkdir -p build/swagger
          # TODO: replace with real generator to produce build/swagger/swagger.json
          test -f build/swagger/swagger.json || echo '{"openapi":"3.0.0","info":{"title":"placeholder","version":"0.0.0"}}' > build/swagger/swagger.json
      - id: out
        run: echo "path=build/swagger/swagger.json" >> "$GITHUB_OUTPUT"

  import-to-yapi:
    needs: build-and-export-swagger
    runs-on: ubuntu-latest
    steps:
      - name: Select YApi token by branch
        id: sel
        run: |
          if [[ "${{ github.ref_name }}" == "main" ]]; then
            echo "token=${{ secrets.YAPI_TOKEN }}" >> "$GITHUB_OUTPUT"
          elif [[ "${{ github.ref_name }}" == "staging" ]]; then
            echo "token=${{ secrets.YAPI_TOKEN_STG }}" >> "$GITHUB_OUTPUT"
          else
            echo "token=${{ secrets.YAPI_TOKEN_DEV }}" >> "$GITHUB_OUTPUT"
          fi

      - name: Import via URL when provided
        if: ${{ secrets.SWAGGER_URL != '' }}
        uses: chekdata/.github/.github/workflows/yapi-sync-reusable.yml@main
        with:
          swagger-url: ${{ secrets.SWAGGER_URL }}
        secrets:
          YAPI_BASE: ${{ secrets.YAPI_BASE }}
          YAPI_TOKEN: ${{ steps.sel.outputs.token }}

      - name: Import via file fallback
        if: ${{ secrets.SWAGGER_URL == '' }}
        uses: chekdata/.github/.github/workflows/yapi-sync-reusable.yml@main
        with:
          swagger-path: ${{ needs.build-and-export-swagger.outputs.swagger_path }}
        secrets:
          YAPI_BASE: ${{ secrets.YAPI_BASE }}
          YAPI_TOKEN: ${{ steps.sel.outputs.token }}
'''

def ensure_branch(owner, repo, from_branch, new_branch):
  r=S.get(f'{API}/repos/{owner}/{repo}')
  r.raise_for_status()
  default_branch=r.json()['default_branch']
  base=from_branch or default_branch
  head=S.get(f'{API}/repos/{owner}/{repo}/git/ref/heads/{base}')
  head.raise_for_status(); sha=head.json()['object']['sha']
  r2=S.post(f'{API}/repos/{owner}/{repo}/git/refs', json={'ref':f'refs/heads/{new_branch}','sha':sha})
  if r2.status_code==422 and 'Reference already exists' in r2.text:
    return new_branch
  r2.raise_for_status(); return new_branch

def put_file(owner, repo, path, branch, content, message):
  b64=base64.b64encode(content.encode('utf-8')).decode('ascii')
  # get existing sha if any
  sha=None
  r=S.get(f'{API}/repos/{owner}/{repo}/contents/{path}', params={'ref': branch})
  if r.status_code==200:
    sha=r.json().get('sha')
  r2=S.put(f'{API}/repos/{owner}/{repo}/contents/{path}', json={'message':message,'content':b64,'branch':branch, **({'sha':sha} if sha else {})})
  if r2.status_code not in (200,201):
    raise Exception(f'put_file failed {r2.status_code} {r2.text}')

def open_pr(owner, repo, head, base, title, body):
  r=S.post(f'{API}/repos/{owner}/{repo}/pulls', json={'title':title,'head':head,'base':base,'body':body})
  if r.status_code not in (200,201):
    print('open_pr failed', repo, r.status_code, r.text)
    return None
  return r.json()

def merge_pr(owner, repo, num):
  r=S.put(f'{API}/repos/{owner}/{repo}/pulls/{num}/merge', json={'merge_method':'squash'})
  return r.status_code in (200,201)

for repo in REPOS:
  print('== update', repo)
  branch=ensure_branch(OWNER, repo, None, BRANCH)
  put_file(OWNER, repo, PATH, branch, NEW_CONTENT, 'chore(ci): support SWAGGER_URL for YApi sync')
  pr=open_pr(OWNER, repo, BRANCH, 'main', 'chore(ci): YApi sync via URL or file', 'Prefer SWAGGER_URL secret, fallback to built file')
  if pr:
    merged=merge_pr(OWNER, repo, pr['number'])
    print('merged', repo, merged)
