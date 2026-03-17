import sys
import json
import asyncio
import urllib.parse
import urllib.request

# ★ デプロイしたGASウェブアプリのURLに差し替えてください
SCORE_API_URL = "https://script.google.com/macros/s/AKfycbz8V2XEr8FgcqAzt0D9GE49K6Gz_t38ZzHeptZJ9xUDdp21CrTQIJrt3jNYrFtNgywo/exec"

def _is_wasm():
    return sys.platform == "emscripten"

def _is_stub():
    return "YOUR_GAS_ID_HERE" in SCORE_API_URL

async def fetch_scores(game_id: str, limit: int = 10):
    """GASからスコア一覧を取得する（非同期）"""
    if _is_stub():
        await asyncio.sleep(0.3)
        return [{"name": "AAA", "score": 10000}, {"name": "BBB", "score": 8000}]
    
    params = urllib.parse.urlencode({
        "action": "get",
        "game_id": game_id,
        "limit": limit
    })
    url = f"{SCORE_API_URL}?{params}"
    
    try:
        if _is_wasm():
            import js
            js.console.log(f"[GAS] START fetch: {url}")
            # ブラウザのfetch APIを使用
            resp = await js.window.fetch(url)
            text = await resp.text()
            js.console.log(f"[GAS] END fetch: ok (len={len(text)})")
            data = json.loads(text)
            return data.get("scores", [])
        else:
            # ネイティブ環境 (PC等)
            print(f"DEBUG: [NATIVE] Fetching URL: {url}")
            loop = asyncio.get_event_loop()
            def _get():
                with urllib.request.urlopen(url, timeout=8) as r:
                    data = json.loads(r.read().decode())
                    return data.get("scores", [])
            return await loop.run_in_executor(None, _get)
    except Exception as e:
        msg = f"Score fetch error: {e}"
        print(msg)
        if _is_wasm():
            import js
            js.console.error(f"[GAS] {msg}")
        return []

async def send_score(game_id: str, player_name: str, score: int):
    """GASにスコアを送信する（非同期）"""
    if _is_stub():
        await asyncio.sleep(0.3)
        return True
        
    params = urllib.parse.urlencode({
        "action": "post",
        "game_id": game_id,
        "player_name": player_name,
        "score": score
    })
    url = f"{SCORE_API_URL}?{params}"
    
    try:
        if _is_wasm():
            import js
            js.console.log(f"[GAS] START send: {player_name} = {score}")
            await js.window.fetch(url)
            js.console.log("[GAS] END send: success")
            return True
        else:
            # ネイティブ環境
            loop = asyncio.get_event_loop()
            def _post():
                with urllib.request.urlopen(url, timeout=8) as r:
                    return r.read()
            await loop.run_in_executor(None, _post)
            return True
    except Exception as e:
        msg = f"Score send error: {e}"
        print(msg)
        if _is_wasm():
            import js
            js.console.error(f"[GAS] {msg}")
        return False
