import pygame

class Scene:
    """ゲームの1画面を表すベースクラス"""
    def __init__(self, manager):
        self.manager = manager
        
    def handle_events(self, events):
        """イベント処理（入力など）"""
        pass
        
    def update(self, dt):
        """状態更新"""
        pass
        
    def draw(self, surface):
        """描画"""
        pass

class SceneManager:
    """シーンの切り替えとメインループ管理を行うクラス"""
    def __init__(self):
        self.scenes = {}
        self.active_scene_name = None
        self.active_scene = None
    
    def add_scene(self, name, scene_obj):
        self.scenes[name] = scene_obj
        
    def set_scene(self, name):
        if name in self.scenes:
            self.active_scene_name = name
            self.active_scene = self.scenes[name]
    
    def update(self, dt):
        if self.active_scene:
            self.active_scene.update(dt)
            
    def draw(self, surface):
        if self.active_scene:
            self.active_scene.draw(surface)
            
    def handle_events(self, events):
        if self.active_scene:
            self.active_scene.handle_events(events)
