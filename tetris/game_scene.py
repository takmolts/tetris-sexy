import pygame
import asyncio
from engine.scene import Scene
from engine.input_manager import input_manager
from engine.net_score import fetch_scores
from engine.config import VERSION
from tetris.tetromino import Tetromino

class GameScene(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        # キャラ画像読み込み用の属性を初期化（AttributeError防止）
        self.special_image_main = None
        self.special_image_effects = {}
        
        # 非同期で演出アセットをロード
        asyncio.create_task(self.load_special_assets())
            
        self.banana_image = None
        try:
            img = pygame.image.load("assets/banana.png").convert_alpha()
            self.banana_image = pygame.transform.scale(img, (25, 25))
        except:
            pass
        
        # BGMのロード
        self.bgm_loaded = False
        try:
            pygame.mixer.music.load("assets/bgm.ogg")
            self.bgm_loaded = True
        except:
            pass
            
        self.reset()
        
        # 描画パラメータ
        self.cell_size = 25
        # 画面中央付近に配置
        self.board_x = 400 - (self.grid_width * self.cell_size) // 2
        self.board_y = 50

    async def load_special_assets(self):
        def load_scaled_img(path, target_width=400):
            try:
                # 拡張子を .jpg に変更
                img = pygame.image.load(path).convert_alpha()
                ratio = target_width / img.get_width()
                return pygame.transform.scale(img, (int(img.get_width() * ratio), int(img.get_height() * ratio)))
            except:
                return None

        # 巨大画像（軽量化した .jpg）を非同期に逐次ロード
        await asyncio.sleep(0.1)
        self.special_image_main = load_scaled_img("assets/event_main.jpg", 600)
        for i in range(1, 5):
            await asyncio.sleep(0.05)
            self.special_image_effects[i] = load_scaled_img(f"assets/effect{i}.jpg", 600)

    def reset(self):
        self.grid_width = 10
        self.grid_height = 20
        # self.grid[y][x] でアクセス。Noneは空きのセル。(R,G,B)はブロックの色。
        self.grid = [[None for _ in range(self.grid_width)] for _ in range(self.grid_height)]
        
        self.bananas = 0
        self.special_active = False
        self.special_timer = 0
        self.special_effect = 0
        self.special_msg = ""
        
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        
        self.score = 0
        self.lines_cleared = 0
        self.level = 1
        self.score_sent = False
        
        self.fall_time = 0
        self.fall_speed = self.get_fall_speed()
        self.game_over = False
        self.paused = False
        
        # BGM再生開始
        if getattr(self, 'bgm_loaded', False):
            try:
                pygame.mixer.music.play(-1)  # -1はループ再生
            except:
                pass
        
        # 連続入力制御用
        self.move_timer = 0
        self.move_delay = 0.1

    def new_piece(self):
        return Tetromino(3, 0)
        
    def get_fall_speed(self):
        # レベルが上がるごとに速くなる (秒/マス)
        # 1レベルごとに0.0756秒ずつ短縮、最速はLV10で0.12秒
        return max(0.12, 0.8 - (self.level - 1) * 0.0756)

    def check_collision(self, piece, offset_x=0, offset_y=0, shape=None):
        """指定したオフセットまたは形状での衝突判定"""
        check_shape = shape if shape is not None else piece.shape
        px = piece.x + offset_x
        py = piece.y + offset_y
        
        for y, row in enumerate(check_shape):
            for x, cell in enumerate(row):
                if cell:
                    c_x = px + x
                    c_y = py + y
                    # 範囲外
                    if c_x < 0 or c_x >= self.grid_width or c_y >= self.grid_height:
                        return True
                    # 上部は範囲外でもOKとするが、盤面内かつ既にブロックがある場合衝突
                    if c_y >= 0 and self.grid[c_y][c_x] is not None:
                        return True
        return False

    def lock_piece(self):
        """ブロックを固定し、行消去、次のブロック生成を行う"""
        for y, row in enumerate(self.current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    c_y = self.current_piece.y + y
                    c_x = self.current_piece.x + x
                    if c_y >= 0 and c_y < self.grid_height:
                        is_banana = (cell == 2)
                        self.grid[c_y][c_x] = (self.current_piece.color, is_banana)
        
        self.score += 10  # ブロック設置時の加算
        self.clear_lines()
        
        self.current_piece = self.next_piece
        self.next_piece = self.new_piece()
        
        # 出現直後に衝突していたらゲームオーバー
        if self.check_collision(self.current_piece):
            self.game_over = True
            # BGM停止
            try:
                pygame.mixer.music.stop()
            except:
                pass
            # 名前入力シーンへ遷移（2秒待機）
            asyncio.create_task(self._go_score_entry())

    async def _go_score_entry(self):
        """ゲームオーバー後に少し間を置いてScoreEntrySceneへ遷移する"""
        await asyncio.sleep(2.0)
        from tetris.score_entry_scene import ScoreEntryScene
        self.manager.add_scene("score_entry", ScoreEntryScene(self.manager, self.score))
        self.manager.set_scene("score_entry")

    def clear_lines(self):
        lines_to_clear = []
        bananas_in_cleared = 0
        for y, row in enumerate(self.grid):
            if all(cell is not None for cell in row):
                lines_to_clear.append(y)
                bananas_in_cleared += sum(1 for cell in row if cell[1])
                
        cleared = len(lines_to_clear)
        if cleared > 0:
            self.bananas += bananas_in_cleared
            if self.bananas >= 10:
                self.trigger_special()
                
            # 消えた行数分を上部に追加
            new_grid = [row for i, row in enumerate(self.grid) if i not in lines_to_clear]
            for _ in range(cleared):
                new_grid.insert(0, [None for _ in range(self.grid_width)])
            self.grid = new_grid
            
            self.lines_cleared += cleared
            # 基本的なスコア計算
            scores = {1: 100, 2: 300, 3: 500, 4: 800}
            self.score += scores.get(cleared, 800) * self.level
            
            # レベルアップ判定
            if self.lines_cleared >= self.level * 10:
                self.level += 1
                self.fall_speed = self.get_fall_speed()

    def hard_drop(self):
        while not self.check_collision(self.current_piece, offset_y=1):
            self.current_piece.y += 1
        self.lock_piece()

    def trigger_special(self):
        self.bananas -= 10
        self.special_active = True
        self.special_timer = 3.0
        
        import random
        self.special_effect = random.randint(1, 4)
        msgs = {
            1: "Vertical Sexy!!",
            2: "Horizontal Sexy!!",
            3: "Sorry...",
            4: "What's S E X Y!?"
        }
        self.special_msg = msgs[self.special_effect]

    def apply_special(self):
        import random
        if self.special_effect == 1:
            cols = random.sample(range(self.grid_width), min(3, self.grid_width))
            for y in range(self.grid_height):
                for x in cols:
                    self.grid[y][x] = None
        elif self.special_effect == 2:
            rows = random.sample(range(self.grid_height), min(3, self.grid_height))
            for y in rows:
                for x in range(self.grid_width):
                    self.grid[y][x] = None
        elif self.special_effect == 3:
            for _ in range(5):
                self.grid.pop(0)
                hole_x = random.randint(0, self.grid_width - 1)
                self.grid.append([((100, 100, 100), False) if x != hole_x else None for x in range(self.grid_width)])
        elif self.special_effect == 4:
            self.grid = [[None for _ in range(self.grid_width)] for _ in range(self.grid_height)]
            self.level += 2
            if self.level > 10:
                self.level = 5
            self.fall_speed = self.get_fall_speed()

    def update(self, dt):
        if self.game_over:
            # 遷移待機中は何もからスキップ
            return
            
        if input_manager.triggers.get("start"):
            self.paused = not self.paused
            # ポーズ中はBGMを一時停止/再開
            if getattr(self, 'bgm_loaded', False):
                try:
                    if self.paused:
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
                except:
                    pass
            
        if getattr(self, 'paused', False):
            return
            
        if self.special_active:
            self.special_timer -= dt
            if self.special_timer <= 0:
                self.special_active = False
                self.apply_special()
            return
            
        # 自動落下
        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            if not self.check_collision(self.current_piece, offset_y=1):
                self.current_piece.y += 1
            else:
                self.lock_piece()

        # 入力処理
        self.move_timer -= dt
        
        dx = 0
        if input_manager.keys.get("left"): dx = -1
        if input_manager.keys.get("right"): dx = 1
        
        # 左右移動
        if dx != 0:
            if input_manager.triggers.get("left") or input_manager.triggers.get("right") or self.move_timer <= 0:
                if not self.check_collision(self.current_piece, offset_x=dx):
                    self.current_piece.x += dx
                # 押しっぱなしの場合はディレイを短くする
                self.move_timer = self.move_delay if not (input_manager.triggers.get("left") or input_manager.triggers.get("right")) else self.move_delay * 2
                
        # 下移動（ソフトドロップ）
        if input_manager.keys.get("down"):
            if self.move_timer <= 0 or input_manager.triggers.get("down"):
                if not self.check_collision(self.current_piece, offset_y=1):
                    self.current_piece.y += 1
                self.move_timer = self.move_delay / 2

        # 回転
        if input_manager.triggers.get("action"):
            rotated = self.current_piece.get_rotated_shape()
            # 壁蹴り等は簡易的（単純に範囲内かチェックし、NGなら何もしない）
            if not self.check_collision(self.current_piece, shape=rotated):
                self.current_piece.rotate()

        # ハードドロップ
        if input_manager.triggers.get("up"):
            self.hard_drop()

    def draw_board(self, screen):
        # 枠
        pygame.draw.rect(screen, (100, 100, 100), 
                         (self.board_x - 2, self.board_y - 2, 
                          self.grid_width * self.cell_size + 4, 
                          self.grid_height * self.cell_size + 4), 2)
        
        # 背景（半透明にして全体の背景画像が透けるようにする）
        bg_surface = pygame.Surface((self.grid_width * self.cell_size, self.grid_height * self.cell_size), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 160))
        screen.blit(bg_surface, (self.board_x, self.board_y))

        # 固定済みブロック
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                cell_data = self.grid[y][x]
                if cell_data:
                    color, is_banana = cell_data
                    rect = (self.board_x + x * self.cell_size, 
                            self.board_y + y * self.cell_size, 
                            self.cell_size - 1, self.cell_size - 1)
                    pygame.draw.rect(screen, color, rect)
                    if is_banana:
                        if self.banana_image:
                            screen.blit(self.banana_image, (self.board_x + x * self.cell_size, self.board_y + y * self.cell_size))
                        else:
                            center = (self.board_x + x * self.cell_size + self.cell_size//2, 
                                      self.board_y + y * self.cell_size + self.cell_size//2)
                            pygame.draw.circle(screen, (255, 255, 0), center, self.cell_size//3)
                    
        # 操作中ブロック
        if self.current_piece and not self.game_over:
            for y, row in enumerate(self.current_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        c_x = self.current_piece.x + x
                        c_y = self.current_piece.y + y
                        if c_y >= 0:
                            rect = (self.board_x + c_x * self.cell_size, 
                                    self.board_y + c_y * self.cell_size, 
                                    self.cell_size - 1, self.cell_size - 1)
                            pygame.draw.rect(screen, self.current_piece.color, rect)
                            if cell == 2:
                                if self.banana_image:
                                    screen.blit(self.banana_image, (self.board_x + c_x * self.cell_size, self.board_y + c_y * self.cell_size))
                                else:
                                    center = (self.board_x + c_x * self.cell_size + self.cell_size//2, 
                                              self.board_y + c_y * self.cell_size + self.cell_size//2)
                                    pygame.draw.circle(screen, (255, 255, 0), center, self.cell_size//3)

    def draw_ui(self, screen):
        font = pygame.font.Font(None, 36)
        
        # スコア・レベル
        score_text = font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        level_text = font.render(f"LEVEL: {self.level}", True, (255, 255, 255))
        lines_text = font.render(f"LINES: {self.lines_cleared}", True, (255, 255, 255))
        banana_text = font.render(f"BANANAS: {self.bananas}/10", True, (255, 255, 0))
        
        ui_x = self.board_x + self.grid_width * self.cell_size + 30
        
        # 見やすくするためにUI背景に半透明の黒帯を描画する
        ui_bg = pygame.Surface((200, 320), pygame.SRCALPHA)
        ui_bg.fill((0, 0, 0, 180))
        screen.blit(ui_bg, (ui_x - 10, self.board_y - 10))
        
        screen.blit(score_text, (ui_x, self.board_y))
        screen.blit(level_text, (ui_x, self.board_y + 40))
        screen.blit(lines_text, (ui_x, self.board_y + 80))
        screen.blit(banana_text, (ui_x, self.board_y + 120))
        
        # ========== 左側パネル ==========
        left_x = 10
        left_y = self.board_y
        panel_w = self.board_x - 20
        panel_h = self.grid_height * self.cell_size
        
        if panel_w > 40:
            # 背景
            left_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            left_bg.fill((0, 0, 0, 180))
            screen.blit(left_bg, (left_x, left_y))
            
            sm_font = pygame.font.Font(None, 22)
            title_font2 = pygame.font.Font(None, 26)
            
            def draw_text_line(text, x, y, color=(200, 200, 200), f=sm_font):
                surf = f.render(text, True, color)
                screen.blit(surf, (x, y))
                return y + surf.get_height() + 3
            
            cy = left_y + 6
            
            # --- 操作説明 ---
            cy = draw_text_line("[ CONTROLS ]", left_x + 6, cy, (255, 220, 50), title_font2)
            cy = draw_text_line("Left/Right : Move", left_x + 6, cy)
            cy = draw_text_line("Space/Z    : Rotate", left_x + 6, cy)
            cy = draw_text_line("Down       : Soft Drop", left_x + 6, cy)
            cy = draw_text_line("Up         : Hard Drop", left_x + 6, cy)
            cy = draw_text_line("Enter      : Pause", left_x + 6, cy)
            cy += 10
            
            # --- バナナ説明 ---
            cy = draw_text_line("[ BANANA FEVER ]", left_x + 6, cy, (255, 220, 50), title_font2)
            cy = draw_text_line("Collect 10 bananas", left_x + 6, cy, (255, 255, 100))
            cy = draw_text_line("to trigger a SPECIAL!", left_x + 6, cy, (255, 255, 100))
            cy += 6
            cy = draw_text_line("Random effects:", left_x + 6, cy)
            cy = draw_text_line(" 1:Vertical Sexy", left_x + 6, cy)
            cy = draw_text_line(" 2:Horizontal Sexy", left_x + 6, cy)
            cy = draw_text_line(" 3:Sorry...", left_x + 6, cy, (255, 120, 120))
            cy = draw_text_line(" 4:What's S E X Y!?", left_x + 6, cy, (100, 255, 150))
            
            # --- バージョン ---
            ver_surf = sm_font.render(f"Ver. {VERSION}", True, (120, 120, 120))
            screen.blit(ver_surf, (left_x + 6, left_y + panel_h - ver_surf.get_height() - 6))
        
        # Nextブロック
        next_text = font.render("NEXT:", True, (255, 255, 255))
        screen.blit(next_text, (ui_x, self.board_y + 160))
        
        if self.next_piece:
            for y, row in enumerate(self.next_piece.shape):
                for x, cell in enumerate(row):
                    if cell:
                        rect = (ui_x + x * self.cell_size, 
                                self.board_y + 200 + y * self.cell_size, 
                                self.cell_size - 1, self.cell_size - 1)
                        pygame.draw.rect(screen, self.next_piece.color, rect)
                        if cell == 2:
                            if self.banana_image:
                                screen.blit(self.banana_image, (ui_x + x * self.cell_size, self.board_y + 200 + y * self.cell_size))
                            else:
                                center = (ui_x + x * self.cell_size + self.cell_size//2, 
                                          self.board_y + 200 + y * self.cell_size + self.cell_size//2)
                                pygame.draw.circle(screen, (255, 255, 0), center, self.cell_size//3)
                        
        if self.game_over:
            go_font = pygame.font.Font(None, 64)
            go_text = go_font.render("GAME OVER", True, (255, 0, 0))
            sub_text = font.render("Press SPACE to Restart", True, (200, 200, 200))
            screen.blit(go_text, (screen.get_width()//2 - go_text.get_width()//2, screen.get_height()//2 - 50))
            screen.blit(sub_text, (screen.get_width()//2 - sub_text.get_width()//2, screen.get_height()//2 + 20))
            
        if getattr(self, 'paused', False) and not self.game_over:
            p_font = pygame.font.Font(None, 64)
            p_text = p_font.render("PAUSED", True, (255, 255, 255))
            screen.blit(p_text, (screen.get_width()//2 - p_text.get_width()//2, screen.get_height()//2 - 30))

    def draw(self, screen):
        self.draw_board(screen)
        self.draw_ui(screen)
        
        if self.special_active:
            s = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            screen.blit(s, (0, 0))
            
            # 残り時間に応じて画像を切り替え
            # timerは初期値2.0。1.0より大きければメイン画像、それ以下ならエフェクト画像
            img_to_draw = None
            show_text = False
            
            if self.special_timer > 1.5:
                img_to_draw = self.special_image_main
            else:
                img_to_draw = self.special_image_effects.get(self.special_effect)
                show_text = True
            
            # 画像が読み込めなかった場合のフォールバック
            if not img_to_draw:
                img_to_draw = self.special_image_main
                
            if img_to_draw:
                screen.blit(img_to_draw, (screen.get_width()//2 - img_to_draw.get_width()//2, 10))
                
            if show_text:
                font = pygame.font.Font(None, 64)
                # 文字枠付きで描画
                text = font.render(self.special_msg, True, (255, 255, 0))
                shadow = font.render(self.special_msg, True, (0, 0, 0))
                
                screen.blit(shadow, (screen.get_width()//2 - text.get_width()//2 + 3, screen.get_height()//2 + 180 + 3))
                screen.blit(text, (screen.get_width()//2 - text.get_width()//2, screen.get_height()//2 + 180))
