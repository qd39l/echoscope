#!/usr/bin/env python3
"""Compare the browser model with the independent scalar Python reference."""
import json
import random
import subprocess
from pathlib import Path
from model import step, kick, clone

root = Path(__file__).resolve().parents[1]
rng = random.Random(260922)
vectors = []
for _ in range(256):
    s = tuple(rng.getrandbits(32) for _ in range(4))
    cell = rng.randrange(32)
    vectors.append(dict(s=s,cell=cell,forward=step(s),reverse=step(s,True),kick=kick(s,cell),clone=clone(s)))
code = '''
const fs=require('fs'),m=require('./demo/model.js');
const vectors=JSON.parse(fs.readFileSync(0,'utf8'));
for(const v of vectors)for(const [k,a] of Object.entries({forward:m.step(v.s),reverse:m.step(v.s,true),kick:m.kick(v.s,v.cell),clone:m.clone(v.s)}))
if(JSON.stringify(a)!==JSON.stringify(v[k]))throw new Error('Mismatch: '+k);
console.log('PASS: 256 random states, four operations each, browser = scalar reference');
'''
subprocess.run(['node','-e',code],cwd=root,input=json.dumps(vectors),text=True,check=True)
