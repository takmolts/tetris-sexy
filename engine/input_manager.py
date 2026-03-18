import pygame

class InputManager:
    """キーボード・ゲームパッド・仮想パッドの入力を統合管理する"""
    def __init__(self):
        # 抽象化された入力状態 (押されているかどうか)
        self.keys = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "action": False,  # Aボタン/Space
            "cancel": False,  # Bボタン/Esc
            "start": False,   # Startボタン/Enter
            "mute": False,    # ミュートトグル
        }
        
        # 1フレームで押された瞬間かどうかのトリガー
        self.triggers = {k: False for k in self.keys}
        
        # 前フレームのキー状態
        self._prev_keys = {k: False for k in self.keys}
        
        # キーボードのマッピング
        self.key_map = {
            pygame.K_UP: "up",
            pygame.K_DOWN: "down",
            pygame.K_LEFT: "left",
            pygame.K_RIGHT: "right",
            pygame.K_SPACE: "action",
            pygame.K_z: "action",
            pygame.K_x: "cancel",
            pygame.K_ESCAPE: "cancel",
            pygame.K_RETURN: "start",
            pygame.K_m: "mute",
        }
        
        # 仮想パッドの状態を受け取るための外部インターフェース用辞書
        self.vpad_state = {k: False for k in self.keys}

    def update(self, events):
        # 状態リセット
        for k in self.keys:
            self._prev_keys[k] = self.keys[k]
            self.keys[k] = False
            self.triggers[k] = False
            
        # キーボードの現在状態を取得
        pressed = pygame.key.get_pressed()
        
        for pg_key, action_name in self.key_map.items():
            if pressed[pg_key]:
                self.keys[action_name] = True
        
        # 仮想パッドの状態を合成
        for action_name in self.keys:
            if self.vpad_state.get(action_name, False):
                self.keys[action_name] = True
                
        # トリガーの判定（前フレームでFalse、今フレームでTrueならTrigger）
        for k in self.keys:
            if self.keys[k] and not self._prev_keys[k]:
                self.triggers[k] = True

# グローバルな入力マネージャインスタンス
input_manager = InputManager()
