import json,sys
P=json.load(open('_audit/content.json',encoding='utf-8'))
def show(path):
    p=[x for x in P if x['path']==path][0]
    print('#####',path,p['meta']['title'])
    def pr(bl,ind=0):
        for b in bl:
            s={k:(v if not isinstance(v,str) else v[:110]) for k,v in b.items() if k not in('slides','items','fields')}
            print(' '*ind+str(s))
            if 'items' in b:
                for it in b['items'][:3]: print(' '*(ind+4)+(it[:80] if isinstance(it,str) else str({k:(v[:70] if isinstance(v,str) else v) for k,v in it.items()})))
                if len(b['items'])>3: print(' '*(ind+4)+f'... {len(b["items"])} items')
            if 'slides' in b:
                print(' '*(ind+2)+f'{len(b["slides"])} slides')
                for sl in b['slides'][:2]: print(' '*(ind+2)+'--slide'); pr(sl,ind+4)
    for s in p['sections']:
        print('== SECTION',s['cls'][:60],s.get('crumbs','') and 'crumbs',s.get('bg',''),s.get('popup',''))
        pr(s['blocks'],2)
for a in sys.argv[1:]: show(a)
