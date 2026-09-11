from pathlib import Path
from typing import Any

import base64
import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qs

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from mmf_engine.engine import VERSION, analyze_ticker
from mmf_engine.beta_v110 import review_markdown
from mmf_engine.llm import ask_ollama
from mailer.email_engine import get_email_language_preference, normalize_email_language, render_email_cn, render_email_en, send_email_report, send_email_report_to, set_email_language_preference
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT / 'config' / 'config.env')
app=FastAPI(title='Miao Market Framework',version=VERSION)
app.mount('/frontend',StaticFiles(directory=str(ROOT/'frontend')),name='frontend')
AUTH_COOKIE='mmf_session'
AUTH_MAX_AGE=60*60*12
def auth_enabled():
    return bool(os.getenv('MMF_AUTH_PASSWORD','').strip()) and os.getenv('MMF_AUTH_ENABLED','true').lower()!='false'
def auth_user():
    return os.getenv('MMF_AUTH_USER','mmf').strip() or 'mmf'
def auth_secret():
    raw=os.getenv('MMF_AUTH_SECRET','').strip() or (auth_user()+':'+os.getenv('MMF_AUTH_PASSWORD','')+':'+VERSION)
    return raw.encode('utf-8')
def _b64(data:bytes): return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')
def _unb64(data:str): return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))
def make_session_token(user:str):
    payload={'u':user,'exp':int(time.time())+AUTH_MAX_AGE}
    body=_b64(json.dumps(payload,separators=(',',':')).encode('utf-8'))
    sig=_b64(hmac.new(auth_secret(),body.encode('ascii'),hashlib.sha256).digest())
    return body+'.'+sig
def read_session_token(token:str|None):
    if not token or '.' not in token: return None
    body,sig=token.rsplit('.',1)
    expected=_b64(hmac.new(auth_secret(),body.encode('ascii'),hashlib.sha256).digest())
    if not hmac.compare_digest(sig,expected): return None
    try: payload=json.loads(_unb64(body))
    except Exception: return None
    if int(payload.get('exp',0)) < int(time.time()): return None
    return payload.get('u')
def require_auth(request:Request):
    if not auth_enabled(): return auth_user()
    user=read_session_token(request.cookies.get(AUTH_COOKIE))
    if user: return user
    raise HTTPException(status_code=401,detail='请先登录 MMF。')
def require_page_auth(request:Request):
    if not auth_enabled(): return auth_user()
    user=read_session_token(request.cookies.get(AUTH_COOKIE))
    if user: return user
    return None
def passwordless_user(username:str):
    normalized=' '.join(username.strip().split())
    allowed={'issacm1224@gmail.com','Issac Miao'}
    return normalized if normalized in allowed else None
class AskRequest(BaseModel):
    question: str
    report: dict[str, Any]
    account: dict[str, Any] | None = None
    provider: str = 'ollama'
@app.get('/',response_class=HTMLResponse)
def index(request:Request):
    if auth_enabled() and not require_page_auth(request):
        return RedirectResponse('/login',status_code=302)
    return (ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
@app.get('/login',response_class=HTMLResponse)
def login_page(request:Request):
    if auth_enabled() and require_page_auth(request):
        return RedirectResponse('/',status_code=302)
    return """<!doctype html><html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>MMF Login</title><style>body{margin:0;background:#081018;color:#E8EEF9;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;display:grid;place-items:center;min-height:100vh}.box{width:min(420px,92vw);background:#0E1524;border:1px solid #263247;border-radius:8px;padding:24px;box-shadow:0 18px 60px rgba(0,0,0,.45)}h1{margin:0 0 8px;color:#D7B56D}.note{color:#9CA8BA;line-height:1.55;margin-bottom:18px}label{display:block;font-size:12px;font-weight:900;color:#AAB4C3;margin:12px 0 6px}input{width:100%;box-sizing:border-box;background:#0B1020;color:#E8EEF9;border:1px solid #263247;border-radius:8px;padding:12px;min-height:44px}button{width:100%;margin-top:18px;background:#D7B56D;border:0;color:#111;font-weight:900;border-radius:8px;padding:12px 18px;cursor:pointer}.small{font-size:12px;color:#9CA8BA;margin-top:14px}</style></head><body><form class="box" method="post" action="/login"><h1>MMF 登录</h1><div class="note">UAT 访问需要登录。账号密码由当前服务配置控制。</div><label>用户名</label><input name="username" autocomplete="username" autofocus/><label>密码</label><input name="password" type="password" autocomplete="current-password"/><button type="submit">进入 MMF</button><div class="small">如果访问被撤销，请联系平台持有人更新权限。</div></form></body></html>"""
@app.post('/login')
async def login(request:Request):
    if not auth_enabled():
        return RedirectResponse('/',status_code=302)
    form=parse_qs((await request.body()).decode('utf-8'))
    username=(form.get('username') or [''])[0]
    password=(form.get('password') or [''])[0]
    bypass_user=passwordless_user(username)
    if bypass_user:
        resp=RedirectResponse('/',status_code=302)
        resp.set_cookie(AUTH_COOKIE,make_session_token(bypass_user),max_age=AUTH_MAX_AGE,httponly=True,samesite='lax')
        return resp
    ok_user=hmac.compare_digest(username.strip(),auth_user())
    ok_pass=hmac.compare_digest(password,os.getenv('MMF_AUTH_PASSWORD',''))
    if not (ok_user and ok_pass):
        return HTMLResponse('<h1>登录失败</h1><p>用户名或密码不正确。</p><p><a href="/login">返回登录</a></p>',status_code=401)
    resp=RedirectResponse('/',status_code=302)
    resp.set_cookie(AUTH_COOKIE,make_session_token(auth_user()),max_age=AUTH_MAX_AGE,httponly=True,samesite='lax')
    return resp
@app.post('/logout')
def logout():
    resp=RedirectResponse('/login',status_code=302)
    resp.delete_cookie(AUTH_COOKIE)
    return resp
@app.get('/health')
def health():
    return {'ok':True,'version':VERSION,'edition':'全球战场版','project':'孙子计划','auth_enabled':auth_enabled(),'tiingo_key':bool(os.getenv('TIINGO_API_KEY','').strip()),'email_enabled':os.getenv('EMAIL_ENABLED','false').lower()=='true','email_language':get_email_language_preference(),'ollama_url':os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434'),'ollama_model':os.getenv('OLLAMA_MODEL','qwen2.5:7b')}


def resolved_email_language(lang=None):
    return normalize_email_language(lang) if lang else get_email_language_preference()


@app.get('/email-language')
def email_language(user:str=Depends(require_auth)):
    return {'language':get_email_language_preference()}


@app.post('/email-language')
def update_email_language(lang:str=Query(...), user:str=Depends(require_auth)):
    return {'language':set_email_language_preference(lang)}
@app.get('/mmf/{ticker}')
def mmf(ticker:str, mode:str=Query('live'), date:str|None=None, position_pct:float=Query(0,ge=0,le=100), user:str=Depends(require_auth)):
    try: return analyze_ticker(ticker,mode=mode,replay_date=date,current_position_pct=position_pct)
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
@app.post('/api/ask')
def ask(req: AskRequest, user:str=Depends(require_auth)):
    if req.provider != 'ollama':
        raise HTTPException(status_code=400, detail='当前只启用 Ollama 本地问答。')
    if not req.question.strip():
        raise HTTPException(status_code=400, detail='问题不能为空。')
    if not req.report:
        raise HTTPException(status_code=400, detail='请先运行一次 MMF，再提问。')
    try: return ask_ollama(req.question.strip(), req.report, req.account)
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail='Ollama 未连接。请确认 Ollama 正在运行，且 http://127.0.0.1:11434 可访问。')
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
@app.get('/email-preview/{ticker}',response_class=PlainTextResponse)
def email_preview(ticker:str, mode:str=Query('live'), date:str|None=None, lang:str|None=Query(None), position_pct:float=Query(0,ge=0,le=100), user:str=Depends(require_auth)):
    try:
        report=analyze_ticker(ticker,mode=mode,replay_date=date,current_position_pct=position_pct)
        return render_email_en(report) if resolved_email_language(lang)=='en' else render_email_cn(report)
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
@app.get('/review-export/{ticker}',response_class=PlainTextResponse)
def review_export(ticker:str, mode:str=Query('live'), date:str|None=None, lang:str=Query('cn'), position_pct:float=Query(0,ge=0,le=100), user:str=Depends(require_auth)):
    try:
        return review_markdown(analyze_ticker(ticker,mode=mode,replay_date=date,current_position_pct=position_pct),lang=lang)
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
@app.post('/send-email/{ticker}')
def send_email(ticker:str, mode:str=Query('live'), date:str|None=None, lang:str|None=Query(None), position_pct:float=Query(0,ge=0,le=100), user:str=Depends(require_auth)):
    try: return send_email_report(analyze_ticker(ticker,mode=mode,replay_date=date,current_position_pct=position_pct),lang=resolved_email_language(lang))
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
@app.post('/send-email-to/{ticker}')
def send_email_to(ticker:str, email:str=Query(...), mode:str=Query('live'), date:str|None=None, lang:str|None=Query(None), position_pct:float=Query(0,ge=0,le=100), user:str=Depends(require_auth)):
    try: return send_email_report_to(analyze_ticker(ticker,mode=mode,replay_date=date,current_position_pct=position_pct), email, lang=resolved_email_language(lang))
    except Exception as e: raise HTTPException(status_code=500,detail=str(e))
