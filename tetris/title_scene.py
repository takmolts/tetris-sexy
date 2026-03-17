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
        try:
            img = pygame.image.load("assets/title_logo.png").convert_alpha()
            # 画面幅（800前提）に合わせて最大化
            ratio = 800.0 / img.get_width()
            self.title_logo = pygame.transform.scale(img, (int(img.get_width()*ratio), int(img.get_height()*ratio)))
        except:
            pass
            
        # 背景タスクとしてランキング取得を開始（※ブラウザ環境ではasyncioメインループの一部として動作）
        asyncio.create_task(self.load_ranking())
        
    async def load_ranking(self):
        self.ranking = await fetch_scores("tetris", limit=5)
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
        
        # タイトルロゴ
        if self.title_logo:
            screen.blit(self.title_logo, (width // 2 - self.title_logo.get_width() // 2, screen.get_height() // 2 - self.title_logo.get_height() // 2))
        else:
            title_font = pygame.font.Font(None, 80)
            title_text = title_font.render("SEXY!! OSURISU", True, (0, 255, 255))
            screen.blit(title_text, (width // 2 - title_text.get_width() // 2, 200))
        # UIが見やすいように半透明の黒背景を敷く
        ui_bg = pygame.Surface((450, 270), pygame.SRCALPHA)
        ui_bg.fill((0, 0, 0, 180))
        screen.blit(ui_bg, (width // 2 - 225, 330))
        
        # "Press Start"
        if self.show_text:
            text_font = pygame.font.Font(None, 40)
            # 文字枠を付けて見やすくする
            start_text_shadow = text_font.render("Press SPACE or A to Start", True, (0, 0, 0))
            start_text = text_font.render("Press SPACE or A to Start", True, (255, 255, 255))
            screen.blit(start_text_shadow, (width // 2 - start_text.get_width() // 2 + 2, 350 + 2))
            screen.blit(start_text, (width // 2 - start_text.get_width() // 2, 350))
            
        # ランキング表示
        rank_font = pygame.font.Font(None, 36)
        screen.blit(rank_font.render("--- TOP SCORES ---", True, (255, 215, 0)), (280, 420))
        
        if self.loading_ranking:
            loading_text = rank_font.render("Loading...", True, (150, 150, 150))
            screen.blit(loading_text, (330, 460))
        else:
            if not self.ranking:
                no_data_text = rank_font.render("No Data", True, (150, 150, 150))
                screen.blit(no_data_text, (350, 460))
            else:
                for i, row in enumerate(self.ranking):
                    if not isinstance(row, dict): continue
                    # プレイヤー名とスコアを描画
                    name_text = f"{i+1}. {row.get('name', '???')}"
                    score_text = str(row.get('score', 0))
                    
                    n_surf = rank_font.render(name_text, True, (200, 200, 200))
                    s_surf = rank_font.render(score_text, True, (200, 200, 200))
                    
                    screen.blit(n_surf, (250, 460 + i * 30))
                    screen.blit(s_surf, (550 - s_surf.get_width(), 460 + i * 30))
