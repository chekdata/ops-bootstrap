# -*- coding: utf-8 -*-
import os, sys, base64, requests
ORG='chekdata'
REPO_DOTGITHUB='.github'
SRC_FILES=[
  ('/Users/jasonhong/Desktop/CICD/.github/workflows/yapi-sync-reusable.yml', '.github/workflows/yapi-sync-reusable.yml'),
  ('/Users/jasonhong/Desktop/CICD/.github/workflows/yapi-sync-autodetect.yml', '.github/workflows/yapi-sync-autodetect.yml'),
]
SERVICE_REPOS=['vehicle-model-service','osm-gateway']
GH_PAT=os.environ.get('GH_PAT')
if not GH_PAT:
  print('Missing GH_PAT', file=sys.stderr); sys.exit(2)
S=requests.Session(); S.headers.update({'Authorization': f'Bearer {GH_PAT}', 'Accept':'application/vnd.github+json'})
API='https://api.github.com'

def ensure_repo(owner, name):
  r=S.get(f'{API}/repos/{owner}/{name}')
  if r.status_code==200:
    return r.json()['default_branch']
  if r.status_code==404:
    r2=S.post(f'{API}/orgs/{owner}/repos', json={'name': name, 'private': False, 'auto_init': True, 'description':'Org-wide reusable workflows'})
    if r2.status_code in (201,):
      return r2.json()['default_branch']
    raise Exception(f'create repo failed {r2.status_code} {r2.text}')
  r.raise_for_status()

def get_file(owner, repo, path, ref):
  r=S.get(f'{API}/repos/{owner}/{repo}/contents/{path}', params={'ref':ref})
  if r.status_code==200:
    js=r.json(); content=base64.b64decode(js['content']).decode('utf-8'); return content, js['sha']
  return None, None

def put_file(owner, repo, path, content, message, branch):
  b64=base64.b64encode(content.encode()).decode('ascii')
  exist, sha = get_file(owner, repo, path, branch)
  payload={'message':message,'content':b64,'branch':branch}
  if sha: payload['sha']=sha
  r=S.put(f'{API}/repos/{owner}/{repo}/contents/{path}', json=payload)
  if r.status_code not in (200,201):
    raise Exception(f'put failed {r.status_code} {r.text}')

# 1) ensure .github repo
branch=ensure_repo(ORG, REPO_DOTGITHUB)
# 2) upload workflows
for src, dst in SRC_FILES:
  with open(src,'r') as f:
    put_file(ORG, REPO_DOTGITHUB, dst, f.read(), f'chore(workflows): sync {os.path.basename(dst)}', branch)
print('uploaded to chekdata/.github')

# 3) update service repos to reference new path
for repo in SERVICE_REPOS:
  # read current yapi-sync.yml
  path='.github/workflows/yapi-sync.yml'
  r=S.get(f'{API}/repos/{ORG}/{repo}/contents/{path}')
  if r.status_code!=200:
    print('skip no workflow', repo); continue
  js=r.json(); content=base64.b64decode(js['content']).decode('utf-8'); sha=js['sha']
new=content.replace('uses: chekdata/CICD/.github/workflows/yapi-sync-autodetect.yml@main',
                      'uses: chekdata/.github/.github/workflows/yapi-sync-autodetect.yml@main')
new=new.replace('uses: chekdata/CICD/.github/workflows/yapi-sync-reusable.yml@main',
                  'uses: chekdata/.github/.github/workflows/yapi-sync-reusable.yml@main')
  if new!=content:
    # create branch and PR
    base=S.get(f'{API}/repos/{ORG}/{repo}').json()['default_branch']
    head_ref=S.get(f'{API}/repos/{ORG}/{repo}/git/ref/heads/{base}').json()['object']['sha']
    br='chore/use-org-workflows'
    S.post(f'{API}/repos/{ORG}/{repo}/git/refs', json={'ref':f'refs/heads/{br}','sha':head_ref})
    # put edited file to branch
    b64=base64.b64encode(new.encode()).decode('ascii')
    S.put(f'{API}/repos/{ORG}/{repo}/contents/{path}', json={'message':'chore(ci): use org .github reusable workflows','content':b64,'branch':br,'sha':sha})
    pr=S.post(f'{API}/repos/{ORG}/{repo}/pulls', json={'title':'chore(ci): use org reusable workflows','head':br,'base':base})
    if pr.status_code in (200,201):
      num=pr.json()['number']
      S.put(f'{API}/repos/{ORG}/{repo}/pulls/{num}/merge', json={'merge_method':'squash'})
      print('updated', repo)

# 4) delete old CICD repo
r=S.delete(f'{API}/repos/{ORG}/CICD')
print('deleted CICD', r.status_code)
