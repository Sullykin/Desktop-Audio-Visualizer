class ColorFade:
    def __init__(self, cycle_type='rainbow', speed=1):
        self.steps = 300
        self.current_step = 0
        self.speed = speed
        self.color_cycle = self.get_cycle(cycle_type)
        self.color = self.color_cycle[self.current_step]

    def get_cycle(self, cycle_type):
        if cycle_type == 'rainbow':
            return self.precompute_colors([(255, 0, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)])
        elif cycle_type == 'rgb':
            return self.precompute_colors([(255, 0, 0), (0, 255, 0), (0, 0, 255)])
        elif cycle_type == 'warm':
            return self.precompute_colors([(255, 0, 0), (255, 165, 0), (255, 255, 0), (165, 255, 0)])
        elif cycle_type == 'cool':
            return self.precompute_colors([(0, 255, 0), (0, 255, 255), (0, 0, 255), (0, 255, 255)])
        else:
            raise ValueError("Unknown cycle_type")

    def precompute_colors(self, targets):
        colors = []
        for i in range(len(targets)):
            from_color = targets[i]
            to_color = targets[(i + 1) % len(targets)]
            for step in range(self.steps):
                t = step / self.steps
                r = int((1 - t) * from_color[0] + t * to_color[0])
                g = int((1 - t) * from_color[1] + t * to_color[1])
                b = int((1 - t) * from_color[2] + t * to_color[2])
                colors.append((r, g, b))
        return colors

    def next(self):
        self.current_step = (self.current_step + self.speed) % len(self.color_cycle)
        self.color = self.color_cycle[self.current_step]
        return self.color