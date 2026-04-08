import sys
import os
sys.path.append('backend')
from dotenv import load_dotenv
load_dotenv('.env')

import gemini
import json

with open('data/transcripts/call_1eb432ae.json') as f:
    t = json.load(f)

try:
    print(gemini.analyze_call(t))
except Exception as e:
    print("EXCEPTION:", repr(e))
