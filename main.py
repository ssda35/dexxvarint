import json
from aiohttp import web
from curl_cffi import requests
from redis.asyncio import Redis
import uuid
import asyncio
import traceback

redis = Redis.from_url('redis://default:PWxaKLYytEXblATYEUQOfLPAwegBGplb@autorack.proxy.rlwy.net:33532')

url_s = 'https://glarityapi.com/trail/v1/chat/completions?tracking_id='

headers = {
    'Authorization': 'Gk_841d7a18274e4f65881c65aa7c51e812__',
    'origin': 'https://glarityapi.com',
}


async def chat_complete(prompt='', chat_history=None, model='gpt-4o', system_prompt=''):

    cookie = await redis.get('feno')
    cookie = cookie.decode('utf-8')
    headers['Authorization'] = cookie
    if chat_history is None:
        chat_history = []
    new_chat_history = remake_chat_history(chat_history, system_prompt, prompt)
    url = url_s + str(uuid.uuid4())
    data = {
        "messages": new_chat_history,
        "stream": True,
        "model": model,
        "temperature": 0.68,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "top_p": 1,
        "max_tokens": 4000
    }

    async with requests.AsyncSession(impersonate='chrome120') as session:
        res = await session.post(url, json=data, headers=headers, stream=True)
        print(res.status_code)
        async for data in res.aiter_lines():
            print(data)
            if data:
                data = data.decode('utf-8')
                if data.startswith('data:'):
                    data = json.loads(data[5:])
                    content = data['choices'][0]['delta']['content']
                    print(content)
                    yield content


def remake_chat_history(chat_history: list, system_prompt: str, prompt: str):
    re_chat_history = [{
        'role': 'system',
        'content': system_prompt
    }]
    for chat in chat_history:
        if 'question' in chat:
            re_chat_history.append({
                'role': 'user',
                'content': chat['question']
            })
        if 'answer' in chat:
            re_chat_history.append({
                'role': "assistant",
                'content': chat['answer']
            })
        else:
            re_chat_history.append({
                'role': "assistant",
                'content': 'error'
            })
    re_chat_history.append({
        'role': 'user',
        'content': prompt
    })
    return re_chat_history


async def chat_complete_feno(request):
    try:
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-cache',ik0oh
                'Transfer-Encoding': 'chunked'
            }
        )
        await response.prepare(request)
        data = await request.json()
        model = data.get('model', '')
        chat_history = data.get('chat_history', [])
        system_prompt = data.get('system_prompt', '')
        prompt = data.get('prompt', '')
        try:
            async for text in chat_complete(prompt=prompt, chat_history=chat_history, model=model,
                                            system_prompt=system_prompt):
                await response.write(json.dumps({'data': text}).encode())
                await response.write(b"\n\n")
        except Exception as e:
            return web.Response(text=str(e), status=400)
        finally:
            await response.write_eof()
        await response.write_eof()
        return response
    except Exception as e:
        return web.Response(text=str(e), status=400)


if __name__ == '__main__':
    app = web.Application()
    app.router.add_post('/chat_complete_feno', chat_complete_feno)
    web.run_app(app, port=8080)

