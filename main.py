import asyncio
import pygame
import sys

from engine.scene import SceneManager, Scene
from engine.input_manager import input_manager
from engine.virtual_pad import VirtualPad
from engine.config import VERSION

# ダミーの初期シーン（後でテトリスのタイトル等に置き換える）
class DummyScene(Scene):
    def update(self, dt):
        pass
    def draw(self, screen):
        font = pygame.font.Font(None, 36)
        text = font.render("Browser Game Engine Booted", True, (255, 255, 255))
        screen.blit(text, (200, 200))

async def main():
    pygame.init()
    pygame.mixer.music.set_volume(0.3) # 初期音量を控えめ（30%）に設定
    
    # iPhone対策: 初期化直後に少し待機してブラウザに制御を返す
    await asyncio.sleep(0.1)
    
    # モバイル等の画面比率も考慮し、レトロゲーム風の固定解像度(例:800x600)とする
    WIDTH, HEIGHT = 800, 600
    # pygame.SCALED を付加してブラウザ側でのアスペクト比維持を強制する
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
    pygame.display.set_caption(f"SEXY!! OSU-RIS Ver. {VERSION}")
    
    clock = pygame.time.Clock()
    
    # 背景画像の読み込み
    try:
        bg_img = pygame.image.load("assets/bg.jpg").convert()
        bg_img = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))
    except:
        bg_img = None
    
    # 共通入力・シーン構築
    scene_manager = SceneManager()
    vpad = VirtualPad(WIDTH, HEIGHT)
    
    # テトリスのシーンを追加する
    from tetris.title_scene import TitleScene
    scene_manager.add_scene("title", TitleScene(scene_manager))
    scene_manager.set_scene("title")
    
    running = True
    is_muted = False
    while running:
        dt = clock.tick(60) / 1000.0
        
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
                
        # 入力状態の更新
        vpad.update(events)
        input_manager.update(events)
        
        # ミュートのトグル
        if input_manager.triggers.get("mute"):
            is_muted = not is_muted
            print(f"DEBUG: MUTE TOGGLED. is_muted={is_muted}")
            if is_muted:
                pygame.mixer.music.set_volume(0)
            else:
                pygame.mixer.music.set_volume(0.3)
        
        # 仮想パッドにミュート状態を伝える
        vpad.is_muted = is_muted
        
        # シーンの更新
        scene_manager.handle_events(events)
        scene_manager.update(dt)
        
        # 描画
        if bg_img and scene_manager.active_scene_name != "title":
            screen.blit(bg_img, (0, 0))
        else:
            screen.fill((0, 0, 0))
        scene_manager.draw(screen)
        
        # 仮想パッドは一番上に重ねて描画する
        vpad.draw(screen)
        
        pygame.display.flip()
        
        # WASMコンテキストでブラウザに制御を返すための非同期スリープ (pygbagの必須要件)
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
