# -*- coding: utf-8 -*-
import os, sys, base64, json, requests

OWNER = 'chekdata'
REPOS = [
  {'name': 'vehicle-model-service', 'yapi_token': 'd07b12268229a9bf20430bd2d905ed49cbc7ac2929254b37699510be70546e15'},
  {'name': 'osm-gateway', 'yapi_token': 'edb2e372f4339c4a54d9650ad7d79003d0836a9cc3f056f274702cc2d02e433d'},
]
YAPI_BASE = 'https://yapi.chekkk.com'
BRANCH = 'chore/yapi-sync-ci'
WF_PATH = '.github/workflows/yapi-sync.yml'
GH_PAT = os.environ.get('GH_PAT')
if not GH_PAT:
    print('Missing GH_PAT env', file=sys.stderr); sys.exit(2)
S = requests.Session()
S.headers.update({'Authorization': f'Bearer {GH_PAT}', 'Accept': 'application/vnd.github+json'})
API = 'https://api.github.com'

WF_CONTENT = '''name: yapi-sync

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
      - id: sel
        run: |
          if [[ "${{ github.ref_name }}" == "main" ]]; then
            echo "token=${{ secrets.YAPI_TOKEN }}" >> "$GITHUB_OUTPUT"
          elif [[ "${{ github.ref_name }}" == "staging" ]]; then
            echo "token=${{ secrets.YAPI_TOKEN_STG }}" >> "$GITHUB_OUTPUT"
          else
            echo "token=${{ secrets.YAPI_TOKEN_DEV }}" >> "$GITHUB_OUTPUT"
          fi
      - uses: chekdata/.github/.github/workflows/yapi-sync-reusable.yml@main
        with:
          swagger-path: ${{ needs.build-and-export-swagger.outputs.swagger_path }}
        secrets:
          YAPI_BASE: ${{ secrets.YAPI_BASE }}
          YAPI_TOKEN: ${{ steps.sel.outputs.token }}
'''

def ensure_branch(owner, repo, from_branch, new_branch):
    r = S.get(f'{API}/repos/{owner}/{repo}')
    r.raise_for_status()
    default_branch = r.json()['default_branch']
    base = from_branch or default_branch
    head = S.get(f'{API}/repos/{owner}/{repo}/git/ref/heads/{base}')
    head.raise_for_status()
    sha = head.json()['object']['sha']
    # create ref
    r2 = S.post(f'{API}/repos/{owner}/{repo}/git/refs', json={
        'ref': f'refs/heads/{new_branch}',
        'sha': sha,
    })
    if r2.status_code == 422 and 'Reference already exists' in r2.text:
        return new_branch
    r2.raise_for_status()
    return new_branch

def put_file(owner, repo, path, branch, content, message):
    b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')
    r = S.put(f'{API}/repos/{owner}/{repo}/contents/{path}', json={
        'message': message,
        'content': b64,
        'branch': branch
    })
    if r.status_code not in (200,201):
        raise Exception(f'put_file failed {r.status_code} {r.text}')

def ensure_secret(owner, repo, name, value):
    # Get public key
    r = S.get(f'{API}/repos/{owner}/{repo}/actions/secrets/public-key')
    r.raise_for_status()
    data = r.json()
    key_id = data['key_id']
    key = data['key']
    # encrypt using libsodium sealed box (base64)
    import nacl.encoding, nacl.public
    pubkey = nacl.public.PublicKey(key, nacl.encoding.Base64Encoder())
    sealed = nacl.public.SealedBox(pubkey).encrypt(value.encode('utf-8'))
    enc = base64.b64encode(sealed).decode('ascii')
    r2 = S.put(f'{API}/repos/{owner}/{repo}/actions/secrets/{name}', json={
        'encrypted_value': enc,
        'key_id': key_id,
    })
    r2.raise_for_status()

for item in REPOS:
    repo = item['name']
    print('== Repo', repo)
    branch = ensure_branch(OWNER, repo, None, BRANCH)
    put_file(OWNER, repo, WF_PATH, branch, WF_CONTENT, 'chore(ci): add YApi auto-import workflow')
    # secrets
    try:
        ensure_secret(OWNER, repo, 'YAPI_BASE', YAPI_BASE)
        ensure_secret(OWNER, repo, 'YAPI_TOKEN', item['yapi_token'])
    except Exception as e:
        print('secret failed', repo, str(e))
    # open PR
    r = S.post(f'{API}/repos/{OWNER}/{repo}/pulls', json={
        'title': 'chore(ci): YApi auto-sync on push',
        'head': BRANCH,
        'base': 'main',
        'body': 'Add reusable workflow to export Swagger and import to YApi on push/merge.'
    })
    if r.status_code not in (200,201):
        print('PR failed', repo, r.status_code, r.text)
    else:
        print('PR opened', repo, r.json().get('html_url'))
