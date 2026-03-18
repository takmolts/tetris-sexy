import pygame
from engine.input_manager import input_manager

class VirtualPad:
    """スマホやマウスで操作可能なオンスクリーンパッド"""
    def __init__(self, screen_width, screen_height):
        # パッドのレイアウト設定 (画面下部に配置する想定)
        self.buttons = {}
        
        # 十字キーの基本位置（左下）
        dpad_center_x = 120
        dpad_center_y = screen_height - 120
        dpad_size = 60
        
        # ミュートボタン (右上)
        self.buttons["mute"] = pygame.Rect(screen_width - 60, 10, 50, 50)
        
        # A/Bボタンの基本位置（右下）
        btn_center_x = screen_width - 100
        btn_center_y = screen_height - 100
        btn_size = 70
        btn_spacing = 80
        
        # ボタンの矩形を定義 (x, y, w, h)
        # 上下左右
        self.buttons["up"] = pygame.Rect(dpad_center_x - dpad_size//2, dpad_center_y - dpad_size - dpad_size//2, dpad_size, dpad_size)
        self.buttons["down"] = pygame.Rect(dpad_center_x - dpad_size//2, dpad_center_y + dpad_size//2, dpad_size, dpad_size)
        self.buttons["left"] = pygame.Rect(dpad_center_x - dpad_size - dpad_size//2, dpad_center_y - dpad_size//2, dpad_size, dpad_size)
        self.buttons["right"] = pygame.Rect(dpad_center_x + dpad_size//2, dpad_center_y - dpad_size//2, dpad_size, dpad_size)
        
        # アクションボタン
        self.buttons["action"] = pygame.Rect(btn_center_x - btn_size//2, btn_center_y - btn_size//2, btn_size, btn_size)
        self.buttons["cancel"] = pygame.Rect(btn_center_x - btn_size//2 - btn_spacing, btn_center_y - btn_size//2 + 30, btn_size, btn_size)
        
        # Startボタン (上部や中央付近)
        self.buttons["start"] = pygame.Rect(screen_width//2 - 50, screen_height - 60, 100, 40)
        
        self.active_touches = {} # touch_id -> action_name
        self.mouse_pressed = False
        self.mouse_action = None
        
        # 表示するかどうかフラグ (PC等では不要なら非表示にできる)
        self.visible = True
        self.is_muted = False # 外部から設定

    def update(self, events):
        # 状態リセット
        for k in input_manager.vpad_state:
            input_manager.vpad_state[k] = False
            
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = pygame.mouse.get_pressed()[0]
        
        # pybagではマウスイベントとしてタッチを受け取ることが多い
        # 簡単のためシングルタッチ（マウスクリック等価）で判定
        current_hover = None
        for action, rect in self.buttons.items():
            if rect.collidepoint(mouse_pos):
                current_hover = action
                break
                
        if mouse_clicked:
            self.mouse_pressed = True
            self.mouse_action = current_hover
        else:
            self.mouse_pressed = False
            self.mouse_action = None
            
        if self.mouse_pressed and self.mouse_action:
            input_manager.vpad_state[self.mouse_action] = True
            
        # TODO: pygame.FINGERDOWN などのマルチタッチ対応（必要であれば）

    def draw(self, surface):
        if not self.visible:
            return
            
        # 半透明の描画面を作成
        pad_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        
        for action, rect in self.buttons.items():
            # 押されているか
            is_pressed = (self.mouse_action == action and self.mouse_pressed)
            
            # ミュート状態による色の変更
            if action == "mute" and self.is_muted:
                color = (255, 100, 100, 180) if is_pressed else (255, 80, 80, 140)
            else:
                color = (255, 255, 255, 128) if is_pressed else (255, 255, 255, 64)
            
            # 円や角丸矩形で描画
            if action in ["action", "cancel"]:
                pygame.draw.ellipse(pad_surface, color, rect)
                pygame.draw.ellipse(pad_surface, (255, 255, 255, 180), rect, 2)
            else:
                pygame.draw.rect(pad_surface, color, rect, border_radius=10)
                pygame.draw.rect(pad_surface, (255, 255, 255, 180), rect, 2, border_radius=10)
                
            # テキストラベル (アイコン代わりの簡易テキスト)
            font = pygame.font.Font(None, 24)
            labels = {
                "up": "U", "down": "D", "left": "L", "right": "R",
                "action": "A", "cancel": "B", "start": "PAUSE", "mute": "MUTE"
            }
            label = labels.get(action, "")
            if label:
                txt_surf = font.render(label, True, (255, 255, 255))
                pad_surface.blit(txt_surf, (rect.centerx - txt_surf.get_width()//2, rect.centery - txt_surf.get_height()//2))
            
        surface.blit(pad_surface, (0, 0))
