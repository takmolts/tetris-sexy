"""
score_entry_scene.py
ゲームオーバー後に名前を入力してスコアを送信するシーン。
"""
import pygame
import asyncio
from engine.scene import Scene
from engine.input_manager import input_manager
from engine.net_score import send_score


class ScoreEntryScene(Scene):
    """
    プレイヤー名を入力してスコアを送信するシーン。
    final_score: 送信するスコア
    """
    MAX_NAME_LEN = 12

    def __init__(self, manager, final_score: int):
        super().__init__(manager)
        self.final_score = final_score
        self.player_name = ""
        self.state = "input"       # "input" | "sending" | "done"
        self.status_msg = ""
        self.blink_timer = 0
        self.show_cursor = True
        # テキスト入力モードを有効化
        pygame.key.start_text_input()

    # ------------------------------------------------------------------
    def handle_events(self, events):
        """mainループから渡されたイベントリストを処理する"""
        if self.state != "input":
            return
        for e in events:
            if e.type == pygame.TEXTINPUT:
                if len(self.player_name) < self.MAX_NAME_LEN:
                    self.player_name += e.text
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_BACKSPACE:
                    self.player_name = self.player_name[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._submit()
                elif e.key == pygame.K_ESCAPE:
                    self._cancel()

    # ------------------------------------------------------------------
    def update(self, dt):
        self.blink_timer += dt
        if self.blink_timer > 0.5:
            self.blink_timer = 0
            self.show_cursor = not self.show_cursor

        # バーチャルパッド / コントローラのボタン対応
        if self.state == "input":
            if input_manager.triggers.get("action"):   # Aボタン → 送信
                self._submit()
            if input_manager.triggers.get("back"):     # Bボタン → キャンセル
                self._cancel()

        if self.state == "done":
            self._go_title()

    # ------------------------------------------------------------------
    def _submit(self):
        name = self.player_name.strip() or "????"
        self.state = "sending"
        self.status_msg = "Sending..."
        pygame.key.stop_text_input()
        asyncio.create_task(self._send_and_finish(name))

    def _cancel(self):
        pygame.key.stop_text_input()
        self._go_title()

    async def _send_and_finish(self, name: str):
        success = await send_score("tetris", name, self.final_score)
        if success:
            self.status_msg = "Score submitted!"
        else:
            self.status_msg = "Failed to send score."
            
        await asyncio.sleep(1.5)  # 完了メッセージを見せるためのウェイト
        self.state = "done"

    def _go_title(self):
        from tetris.title_scene import TitleScene
        self.manager.add_scene("title", TitleScene(self.manager))
        self.manager.set_scene("title")

    # ------------------------------------------------------------------
    def draw(self, screen):
        w, h = screen.get_width(), screen.get_height()

        # 半透明オーバーレイ
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        screen.blit(overlay, (0, 0))

        title_font = pygame.font.Font(None, 60)
        sub_font   = pygame.font.Font(None, 38)
        hint_font  = pygame.font.Font(None, 28)

        cy = h // 2 - 160

        def center_text(surf, y):
            screen.blit(surf, (w // 2 - surf.get_width() // 2, y))

        # ゲームオーバー見出し
        center_text(title_font.render("GAME OVER", True, (255, 80, 80)), cy)
        cy += 70

        # スコア
        center_text(sub_font.render(f"SCORE: {self.final_score}", True, (255, 255, 100)), cy)
        cy += 50

        if self.state == "input":
            center_text(hint_font.render("Enter your name:", True, (200, 200, 200)), cy)
            cy += 36

            # 名前入力ボックス
            box_w, box_h = 340, 48
            box_x = w // 2 - box_w // 2
            pygame.draw.rect(screen, (60, 60, 80), (box_x, cy, box_w, box_h), border_radius=6)
            pygame.draw.rect(screen, (180, 180, 255), (box_x, cy, box_w, box_h), 2, border_radius=6)

            cursor = "|" if self.show_cursor else " "
            name_surf = sub_font.render(self.player_name + cursor, True, (255, 255, 255))
            screen.blit(name_surf, (box_x + 12, cy + (box_h - name_surf.get_height()) // 2))
            cy += box_h + 20

            # ボタンヒント
            center_text(hint_font.render("[Enter / A] Submit    [Esc / B] Cancel", True, (150, 150, 150)), cy)

        elif self.state == "sending":
            center_text(sub_font.render(self.status_msg, True, (200, 200, 255)), cy)

        elif self.state == "done":
            center_text(sub_font.render(self.status_msg, True, (100, 255, 150)), cy)
            cy += 44
            center_text(hint_font.render("Returning to title...", True, (180, 180, 180)), cy)
