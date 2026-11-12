from ollama import Client
import os
c=Client(host=os.getenv('OLLAMA_HOST','http://localhost:11434'),timeout=180,trust_env=False)
r=c.chat(model=os.getenv('OLLAMA_MODEL','qwen3.5:2b-q4_K_M'),messages=[{'role':'user','content':'한국어로 한 문장 인사해 주세요.'}],think=False)
print(r.message.content)
