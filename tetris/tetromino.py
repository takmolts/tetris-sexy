import random

SHAPES = {
    'I': [[1, 1, 1, 1]],
    'J': [[1, 0, 0], [1, 1, 1]],
    'L': [[0, 0, 1], [1, 1, 1]],
    'O': [[1, 1], [1, 1]],
    'S': [[0, 1, 1], [1, 1, 0]],
    'T': [[0, 1, 0], [1, 1, 1]],
    'Z': [[1, 1, 0], [0, 1, 1]]
}

COLORS = {
    'I': (0, 255, 255),
    'J': (0, 0, 255),
    'L': (255, 165, 0),
    'O': (255, 255, 0),
    'S': (0, 255, 0),
    'T': (128, 0, 128),
    'Z': (255, 0, 0)
}

class Tetromino:
    def __init__(self, x, y, shape_name=None):
        if shape_name is None:
            shape_name = random.choice(list(SHAPES.keys()))
        self.shape_name = shape_name
        self.shape = [list(row) for row in SHAPES[shape_name]]
        self.color = COLORS[shape_name]
        self.x = x
        self.y = y
        
        # 20%の確率でバナナマークを付与（1を2に置換）
        if random.random() < 0.2:
            ones = [(r, c) for r, row in enumerate(self.shape) for c, val in enumerate(row) if val == 1]
            if ones:
                br, bc = random.choice(ones)
                self.shape[br][bc] = 2

    def get_rotated_shape(self):
        """回転後の形状をプレビュー用として返す"""
        return [list(row) for row in zip(*self.shape[::-1])]
        
    def rotate(self):
        """実際に回転する (時計回り)"""
        self.shape = self.get_rotated_shape()
