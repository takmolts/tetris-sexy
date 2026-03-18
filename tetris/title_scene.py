import pygame
import asyncio
from engine.scene import Scene
from engine.input_manager import input_manager
from engine.net_score import fetch_scores

class TitleScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.blink_timer = 0
        self.show_text = True
        
        # ランキングデータ管理
        self.ranking = []
        self.loading_ranking = True
        
        self.title_logo = None
        # アセットの読み込みを非同期タスクとして開始（起動のブロッキングを防ぐ）
        asyncio.create_task(self.load_assets())
        
        # 背景タスクとしてランキング取得を開始（※ブラウザ環境ではasyncioメインループの一部として動作）
        asyncio.create_task(self.load_ranking())
        
    async def load_assets(self):
        # 巨大画像（軽量化した .jpg）を非同期にロード
        await asyncio.sleep(0.1)
        try:
            img = pygame.image.load("assets/title_logo.jpg").convert_alpha()
            # 画面の高さ（600前提）に合わせて最大化し、上下の見切れを防ぐ
            ratio = 600.0 / img.get_height()
            self.title_logo = pygame.transform.scale(img, (int(img.get_width()*ratio), int(img.get_height()*ratio)))
        except:
            pass

    async def load_ranking(self):
        self.ranking = await fetch_scores("tetris", limit=10)
        print(f"DEBUG: ranking loaded: {self.ranking}")
        self.loading_ranking = False
        
    def update(self, dt):
        self.blink_timer += dt
        if self.blink_timer > 0.5:
            self.blink_timer = 0
            self.show_text = not self.show_text
            
        # 決定ボタンが押されたらゲームに遷移
        # Circular importを避けるため、ここでimport
        if input_manager.triggers.get("action") or input_manager.triggers.get("start"):
            from tetris.game_scene import GameScene
            self.manager.add_scene("game", GameScene(self.manager))
            self.manager.set_scene("game")

    def draw(self, screen):
        width = screen.get_width()
        height = screen.get_height()
        
        # タイトルロゴ（中央に戻す）
        if self.title_logo:
            screen.blit(self.title_logo, (width // 2 - self.title_logo.get_width() // 2, height // 2 - self.title_logo.get_height() // 2))
        else:
            title_font = pygame.font.Font(None, 80)
            title_text = title_font.render("SEXY!! OSURISU", True, (0, 255, 255))
            screen.blit(title_text, (width // 2 - title_text.get_width() // 2, 200))

        # UIが見やすいように半透明の黒背景を敷く（透過度をさらに上げる: 180 -> 100）
        ui_bg_w, ui_bg_h = 460, 360
        ui_bg_x, ui_bg_y = width // 2 - ui_bg_w // 2, 230
        ui_bg = pygame.Surface((ui_bg_w, ui_bg_h), pygame.SRCALPHA)
        ui_bg.fill((0, 0, 0, 100))
        screen.blit(ui_bg, (ui_bg_x, ui_bg_y))
        
        # "Press Start"
        if self.show_text:
            text_font = pygame.font.Font(None, 40)
            start_text_shadow = text_font.render("Press SPACE or A to Start", True, (0, 0, 0))
            start_text = text_font.render("Press SPACE or A to Start", True, (255, 255, 255))
            screen.blit(start_text_shadow, (width // 2 - start_text.get_width() // 2 + 2, ui_bg_y + 20 + 2))
            screen.blit(start_text, (width // 2 - start_text.get_width() // 2, ui_bg_y + 20))
            
        # ランキング表示
        rank_header_font = pygame.font.Font(None, 34)
        rank_item_font = pygame.font.Font(None, 28) # 10件入れるために少し小さく
        
        header_y = ui_bg_y + 75
        screen.blit(rank_header_font.render("--- TOP SCORES ---", True, (255, 215, 0)), (width // 2 - 120, header_y))
        
        if self.loading_ranking:
            loading_text = rank_item_font.render("Loading...", True, (150, 150, 150))
            screen.blit(loading_text, (width // 2 - loading_text.get_width() // 2, header_y + 40))
        else:
            if not self.ranking:
                no_data_text = rank_item_font.render("No Data", True, (150, 150, 150))
                screen.blit(no_data_text, (width // 2 - no_data_text.get_width() // 2, header_y + 40))
            else:
                for i, row in enumerate(self.ranking):
                    if not isinstance(row, dict): continue
                    # プレイヤー名とスコアを描画
                    name_text = f"{i+1:2d}. {row.get('name', '????')}"
                    score_text = str(row.get('score', 0))
                    
                    n_surf = rank_item_font.render(name_text, True, (220, 220, 220))
                    s_surf = rank_item_font.render(score_text, True, (220, 220, 220))
                    
                    ry = header_y + 40 + i * 22 # 行間も詰める
                    screen.blit(n_surf, (ui_bg_x + 60, ry))
                    screen.blit(s_surf, (ui_bg_x + ui_bg_w - 60 - s_surf.get_width(), ry))
