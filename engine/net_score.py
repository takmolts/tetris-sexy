import sys
import json
import asyncio
import urllib.parse
import urllib.request
import time

# ★ デプロイしたGASウェブアプリのURLに差し替えてください
SCORE_API_URL = "https://script.google.com/macros/s/AKfycbxmRDvBBA_g11NQy4ZwP85h_v84Gs9sxsz5UTKgYskvOSTOQinwrhNaEUzxR-q-O6-H/exec"

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
            js.console.log(f"[GAS] START fetch (poll): {url}")
            
            # fetch_id は JS 変数名として安全な形式にする
            fetch_id = f"f{int(time.time() * 1000)}"
            js.window.eval(f"window['{fetch_id}'] = {{ status: 'PENDING', data: null }};")
            
            # setTimeout 内で window['ID'] が存在するかチェックすることで、
            # Python 側で削除された後の「Cannot read properties of undefined」エラーを防ぐ
            js_script = f"""
            fetch("{url}", {{ mode: 'cors', cache: 'no-cache', redirect: 'follow' }})
                .then(r => {{
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    return r.json();
                }})
                .then(json => {{
                    if (window['{fetch_id}']) {{
                        window['{fetch_id}'].data = JSON.stringify(json.scores || []);
                        window['{fetch_id}'].status = 'OK';
                    }}
                }})
                .catch(err => {{
                    console.error("[GAS JS] fetch error:", err);
                    if (window['{fetch_id}']) {{
                        window['{fetch_id}'].status = 'ERROR';
                    }}
                }});
            // 4.5秒で強制的にタイムアウト解決させる（削除済みチェック付き）
            setTimeout(() => {{
                if (window['{fetch_id}'] && window['{fetch_id}'].status === 'PENDING') {{
                    console.warn("[GAS JS] internal timeout reached");
                    window['{fetch_id}'].status = 'TIMEOUT';
                }}
            }}, 4500);
            """
            js.window.eval(js_script)
            
            # Python 側で定期的に完了をチェック
            for _ in range(60): # 最大6秒
                # eval 自体がエラーにならないよう安全にアクセス
                status = js.window.eval(f"window['{fetch_id}'] ? window['{fetch_id}'].status : 'DELETED'")
                if status == "OK":
                    raw_json = js.window.eval(f"window['{fetch_id}'].data")
                    js.console.log("[GAS] fetch success")
                    js.window.eval(f"delete window['{fetch_id}'];")
                    return json.loads(raw_json)
                if status in ("ERROR", "TIMEOUT"):
                    js.console.warn(f"[GAS] fetch aborted: {{status}}")
                    js.window.eval(f"delete window['{fetch_id}'];")
                    return []
                if status == "DELETED": # 万が一削除されていた場合
                    return []
                await asyncio.sleep(0.1)
                
            js.console.error("[GAS] fetch polling timeout")
            js.window.eval(f"if(window['{fetch_id}']) delete window['{fetch_id}'];")
            return []
        else:
            # ネイティブ環境 (PC等)
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
            js.console.log(f"[GAS] START send (Image ping): {player_name} = {score}")
            js.window.eval(f"(new Image()).src = '{url}';")
            await asyncio.sleep(0.5)
            js.console.log("[GAS] Send complete signal")
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
