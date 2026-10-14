"""Publish reviewed source images to a browser-viewable GitHub branch."""
import base64,hashlib,io,json,os,urllib.request,zipfile

REPO='mxsam72/orlando-mx-build';API='https://api.github.com/repos/'+REPO
RUN=38581423680;ARTIFACT=11903922819;SOURCE='ccf1e5544d8ea5b8354bf1edc1f697aec0d2774b'
BRANCH='preview-v053';FOLDER='PREVIEWS/v053/'
HEADERS={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'OrlandoMX-source-previews'}
def api(path,data=None,method=None):
    body=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(API+path,data=body,method=method,headers=HEADERS|({'Content-Type':'application/json'} if body else {}))
    with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        out=super().redirect_request(req,fp,code,msg,headers,newurl)
        if out is not None:out.remove_header('Authorization');out.remove_header('Accept')
        return out
def main():
    repo=api('');assert repo['id']==1368050549 and not repo['private']
    artifact=api('/actions/artifacts/'+str(ARTIFACT))
    assert artifact['name']=='v053-source-review' and artifact['workflow_run']['id']==RUN and artifact['workflow_run']['head_sha']==SOURCE
    req=urllib.request.Request(API+'/actions/artifacts/'+str(ARTIFACT)+'/zip',headers=HEADERS)
    with urllib.request.build_opener(NoAuthRedirect).open(req,timeout=120) as response:payload=response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        assert z.testzip() is None
        def read(name):
            paths=[p for p in z.namelist() if p.rsplit('/',1)[-1]==name]
            assert len(paths)==1,(name,paths)
            return z.read(paths[0])
        manifest=json.loads(read('manifest.json'));assert manifest['source_only'] and not manifest['game_captures']
        files={}
        for label in ['straight','jump_face','corner','landing']:
            name='v053_'+label+'.jpg';data=read(name)
            row=next(r for r in manifest['renders'] if r['file']==name)
            assert hashlib.sha256(data).hexdigest()==row['sha256']
            files[name]=data;files['comparison_'+label+'.jpg']=read('comparison_'+label+'.jpg')
    text='''# v053 dirt comparison renders

**v052 is on the left; v053 is on the right.** Click an image to view it larger.

These are matched source previews of the terrain and dirt materials. Trees and other scenery are omitted in both views. They are not screenshots from MX Bikes. The track is compiling separately: [build status](https://github.com/mxsam72/orlando-mx-build/actions/runs/38581423680).

## Straight

![Straight comparison](comparison_straight.jpg)

[Open the v053 straight by itself](v053_straight.jpg)

## Jump face

![Jump face comparison](comparison_jump_face.jpg)

[Open the v053 jump face by itself](v053_jump_face.jpg)

## Corner

![Corner comparison](comparison_corner.jpg)

[Open the v053 corner by itself](v053_corner.jpg)

## Landing

![Landing comparison](comparison_landing.jpg)

[Open the v053 landing by itself](v053_landing.jpg)
'''
    files['README.md']=text.encode()
    ref=api('/git/ref/heads/'+BRANCH);head=ref['object']['sha'];assert head==os.environ['GITHUB_SHA']
    commit=api('/git/commits/'+head);entries=[]
    for name,data in files.items():
        blob=api('/git/blobs',{'content':base64.b64encode(data).decode(),'encoding':'base64'})
        entries.append({'path':FOLDER+name,'mode':'100644','type':'blob','sha':blob['sha']})
    tree=api('/git/trees',{'base_tree':commit['tree']['sha'],'tree':entries})
    new=api('/git/commits',{'message':'Publish reviewed v053 comparison renders for browser viewing','tree':tree['sha'],'parents':[head]})
    current=api('/git/ref/heads/'+BRANCH);assert current['object']['sha']==head
    api('/git/refs/heads/'+BRANCH,{'sha':new['sha'],'force':False},method='PATCH')
    url='https://github.com/'+REPO+'/tree/'+BRANCH+'/'+FOLDER.rstrip('/')
    print('V053_PREVIEW_PAGE',url,flush=True)
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('[View v053 comparison renders]('+url+')\n')
if __name__=='__main__':main()
