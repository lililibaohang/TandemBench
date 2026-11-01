"""OpenAI-compatible Chat Completions transport, standard library only."""
import json
import http.client
import time
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def endpoint(base_url):
    url = urllib.parse.urlsplit(base_url)
    if url.scheme not in ('http', 'https') or not url.netloc:
        raise ValueError('base_url must be an HTTP(S) URL')
    if url.username or url.password or url.query or url.fragment:
        raise ValueError('base_url must not contain credentials, query or fragment')
    return base_url.rstrip('/') + ('' if url.path.rstrip('/').endswith('/chat/completions') else '/chat/completions')


def redact(value, key):
    if isinstance(value,str):
        return value.replace(key,'[REDACTED]') if key else value
    if isinstance(value,list):
        return [redact(v,key) for v in value]
    if isinstance(value,dict):
        return {redact(k,key):redact(v,key) for k,v in value.items()}
    return value


def request_once(config, prompt, key):
    body = {'model':config['model'], 'messages':[{'role':'user','content':prompt}],
            'max_tokens':config['max_tokens'], 'temperature':config['temperature'],
            'stream':False, 'n':1}
    body.update(config['request_options'])
    if 'max_completion_tokens' in body:
        body.pop('max_tokens',None)
    req = urllib.request.Request(config['endpoint'], data=json.dumps(body).encode(),
          headers={'Content-Type':'application/json','Authorization':'Bearer '+key}, method='POST')
    start=time.monotonic()
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=config['timeout']) as response:
            raw=response.read(16*1024*1024+1)
        if len(raw)>16*1024*1024:
            return {'kind':'error','error':'response_too_large','retryable':False}
        # Never persist a provider-echoed credential, even in raw responses.
        data=redact(json.loads(raw.decode('utf-8')),key)
        if not isinstance(data,dict) or not isinstance(data.get('choices'),list) or len(data['choices'])!=1:
            return {'kind':'error','error':'invalid_response_schema','retryable':False}
        choice=data['choices'][0]
        if not isinstance(choice,dict) or not isinstance(choice.get('message'),dict):
            return {'kind':'error','error':'invalid_response_schema','retryable':False}
        return {'kind':'response','response':data,'latency_seconds':round(time.monotonic()-start,4)}
    except urllib.error.HTTPError as exc:
        # Error bodies may contain secrets or gateway diagnostics: retain status only.
        return {'kind':'error','error':'http_error','http_status':exc.code,
                'retryable':exc.code in (408,429,500,502,503,504)}
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.HTTPException):
        return {'kind':'error','error':'transport_error','retryable':True}
    except (ValueError,UnicodeError):
        return {'kind':'error','error':'invalid_json_response','retryable':False}
