import math
import pygame
import numpy as np
import colorsys

# add frequency bar at bottom or sides to generate waves completely based on music

class Camera:
    def __init__(self, particle_field, x=0, y=0, zoom=1, angle=0):
        self.particle_field = particle_field
        self.screen_w = particle_field.screen_w
        self.screen_h = particle_field.screen_h
        self.x = x
        self.y = y
        self.zoom = zoom
        self.angle = angle  # in degrees
        self.update()
        self.zoom_out(1 + particle_field.zoom_factor/10)

    def transform_points(self, points):
        # Add a homogeneous coordinate of 1
        homogeneous_coord = np.ones((points.shape[0], points.shape[1], 1))
        particles_with_homogeneous = np.concatenate((points[:, :, :2], homogeneous_coord), axis=2)
        
        # Reshape the particles to a 2D array and then transpose it to a 3xN array
        particles_reshaped = particles_with_homogeneous.reshape(-1, 3).T

        # Apply the transformation
        transformed_particles = np.dot(self.transformation_matrix, particles_reshaped)

        # Reshape back to the original shape and return
        return transformed_particles.T.reshape(self.particle_field.grid_w, self.particle_field.grid_h, 3)

    def update(self):
        cos_a = math.cos(math.radians(self.angle))
        sin_a = math.sin(math.radians(self.angle))

        # Translate to origin (center of screen)
        translate_to_origin = np.array([
            [1, 0, -self.screen_w // 2],
            [0, 1, -self.screen_h // 2],
            [0, 0, 1]
        ])

        # Rotation matrix
        rotation_matrix = np.array([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0],
            [0, 0, 1]
        ])

        # Translate back
        translate_back = np.array([
            [1, 0, self.screen_w // 2],
            [0, 1, self.screen_h // 2],
            [0, 0, 1]
        ])

        # Transformation matrix for panning and zooming
        transformation_matrix = np.array([
            [self.zoom, 0, self.x],
            [0, self.zoom, self.y],
            [0, 0, 1]
        ])

        # The final transformation matrix
        self.transformation_matrix = np.dot(translate_back, np.dot(rotation_matrix, translate_to_origin))
        self.transformation_matrix = np.dot(transformation_matrix, self.transformation_matrix)

    def rotate(self, delta_angle):
        self.angle += delta_angle
        self.angle %= 360  # Keep it between 0 and 359
        self.update()
        
    def pan_left(self, delta):
        self.x -= delta
        self.update()

    def pan_right(self, delta):
        self.x += delta
        self.update()

    def pan_up(self, delta):
        self.y -= delta
        self.update()

    def pan_down(self, delta):
        self.y += delta
        self.update()

    def zoom_in(self, factor):
        self.zoom *= factor
        self.x = self.x * factor + (1 - factor) * self.screen_w / 2
        self.y = self.y * factor + (1 - factor) * self.screen_h / 2
        self.update()

    def zoom_out(self, factor):
        self.zoom /= factor
        self.x = (self.x - self.screen_w / 2) / factor + self.screen_w / 2
        self.y = (self.y - self.screen_h / 2) / factor + self.screen_h / 2
        self.update()


class ParticleField:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.screen_w = visualizer.SCREEN_WIDTH
        self.screen_h = visualizer.SCREEN_HEIGHT
        self.debug = False
        self.update_settings()
        self.camera = Camera(self)
        self.init_field(48*self.grid_size, 27*self.grid_size)
        self.precompute_velocity_colors()
        self.setup_external_forces()

    def init_field(self, grid_w=48, grid_h=27):  # 64, 36
        self.grid_w = grid_w
        self.grid_h = grid_h
        
        # Initialize particles with positions and velocities
        # Each particle is represented as [x, y, z, vx, vy, vz]
        self.particles = np.zeros((self.grid_w, self.grid_h, 6))
        self.transformed_points = np.zeros((self.grid_w, self.grid_h, 3))

        dx = self.screen_w // self.grid_w
        dy = self.screen_h // self.grid_h
        for i in range(self.grid_w):
            for j in range(self.grid_h):
                x = i * dx + dx // 2
                y = j * dy + dy // 2
                z = 0
                vx, vy, vz = 0, 0, 0  # Initial velocities
                self.particles[i, j] = np.array([x, y, z, vx, vy, vz])
        self.original_positions = np.copy(self.particles)

    def precompute_velocity_colors(self):
        max_velocity = 100  # This is the maximum expected velocity
        self.color_angle = 0
        self.color_map = {}
        for v in range(max_velocity + 1):
            normalized_magnitude = np.log(v + 1) / np.log(max_velocity + 1)
            if normalized_magnitude < 0.01:
                saturation = 0
            else:
                saturation = 1.0
            hue = normalized_magnitude * 360
            self.color_map[v] = [int(x * 255) for x in colorsys.hsv_to_rgb(hue / 360.0, saturation, 1.0)]
        self.velocity_magnitudes = np.linalg.norm(self.particles[:,:,3:6], axis=2).astype(int)
        self.particle_colors = np.array([self.color_map.get(mag, self.color_map[50]) for mag in self.velocity_magnitudes.flatten()]).reshape(self.grid_w, self.grid_h, 3)

    def setup_external_forces(self):
        # Edge waves
        self.edge_force = np.zeros((self.grid_w, self.grid_h, 3))
        self.wave_damping_factor = 0.6  # How much the wave dampens after each bounce
        self.wave_threshold = 18
        self.wave_speed = 1
        self.wavefronts = []
        self.reverse_directions = {
            'up': 'down',
            'down': 'up',
            'left': 'right',
            'right': 'left'
        }

        # Radial waves
        self.force_center = (self.screen_w // 2, self.screen_h // 2)
        self.persistent_radial_wavefronts = []

        # distortion
        self.distortion_factor = 0
        self.distortion_threshold = 10

    def update_settings(self):
        self.grid_size = self.visualizer.settings["particle_field"]["grid_size"]
        self.zoom_factor = self.visualizer.settings["particle_field"]["zoom_factor"]
        self.edge_waves = self.visualizer.settings["particle_field"]["edge_waves"]
        self.radial_waves = self.visualizer.settings["particle_field"]["radial_waves"]

    def check_user_input(self):
        pan_speed = 20
        zoom_factor = 1.1
        pressed_keys = pygame.key.get_pressed()

        # Pan
        if pressed_keys[pygame.K_LEFT]:
            self.camera.pan_left(pan_speed)
        elif pressed_keys[pygame.K_UP]:
            self.camera.pan_up(pan_speed)
        if pressed_keys[pygame.K_RIGHT]:
            self.camera.pan_right(pan_speed)
        elif pressed_keys[pygame.K_DOWN]:
            self.camera.pan_down(pan_speed)

        # Zoom
        if pressed_keys[pygame.K_z]:
            self.camera.zoom_in(zoom_factor)
        elif pressed_keys[pygame.K_x]:
            self.camera.zoom_out(zoom_factor)

        # Rotate
        if pressed_keys[pygame.K_a]:
            self.camera.rotate(-5)
        elif pressed_keys[pygame.K_d]:
            self.camera.rotate(5)

    def update(self, audio_features):
        self.check_user_input()
        fft_data = audio_features["fft"]
        amplitude_data = audio_features["amps"]
        magnitude = np.max(amplitude_data)

        # Update velocities based on forces
        internal_forces = self.process_internal_forces()
        external_forces = self.process_external_forces(magnitude, fft_data, amplitude_data)
        total_forces = internal_forces + external_forces
        self.particles[:,:,3:6] += total_forces

        # Update positions based on velocities
        self.particles[:,:,0:3] += self.particles[:,:,3:6]
        self.velocity_magnitudes = np.linalg.norm(self.particles[:,:,3:6], axis=2).astype(int)
        self.particle_colors = np.array([self.color_map.get(mag, self.color_map[50]) for mag in self.velocity_magnitudes.flatten()]).reshape(self.grid_w, self.grid_h, 3)
        self.transformed_points = self.camera.transform_points(self.particles)

        # Generate random distortion values
        if self.distortion_factor >= 1:
            df = self.distortion_factor
            x_distort = np.random.randint(-df, df, self.transformed_points[:,:,0:1].shape)
            y_distort = np.random.randint(-df, df, self.transformed_points[:,:,1:2].shape)
            self.transformed_points[:,:,0:1] += x_distort
            self.transformed_points[:,:,1:2] += y_distort

    def process_internal_forces(self):
        damping_factor = 0.95
        self.particles[:,:,3:6] *= damping_factor

        internal_forces = -0.01 * (self.particles[:,:,0:3] - self.original_positions[:,:,0:3])

        neighbor_forces = (
            np.roll(self.particles[:,:,0:3], shift=-1, axis=0) +
            np.roll(self.particles[:,:,0:3], shift=1, axis=0) +
            np.roll(self.particles[:,:,0:3], shift=-1, axis=1) +
            np.roll(self.particles[:,:,0:3], shift=1, axis=1)
        ) / 4.0

        internal_forces[1:-1, 1:-1, 0:3] += 0.05 * (neighbor_forces[1:-1, 1:-1, 0:3] - self.particles[1:-1, 1:-1, 0:3])

        # Dampen the internal forces a bit
        internal_forces *= 0.3

        # Add restoring forces to pull particles back to their original positions
        restoring_force = -0.1 * (self.particles[:,:,0:2] - self.original_positions[:,:,0:2])
        internal_forces[:,:,0:2] += restoring_force

        return internal_forces

    def process_external_forces(self, magnitude, fft_data, amplitude_data):
        if magnitude >= self.wave_threshold  and np.random.random() < 0.3:
            if self.edge_waves:
                wave_direction = np.random.choice(['up', 'down', 'left', 'right'])
                self.generate_edge_wavefront(magnitude, wave_direction)
  
        # check distortion
        if magnitude > self.distortion_threshold:
            if self.distortion_factor < 5:  # hard cap
                self.distortion_factor += magnitude / 5
        elif self.distortion_factor > 1:
            self.distortion_factor -= 0.5

        self.update_edge_wavefronts()
        radial_forces = self.update_radial_wavefronts(fft_data, amplitude_data)

        #return np.zeros((self.grid_w, self.grid_h, 3))
        return radial_forces + self.edge_force

    def generate_edge_wavefront(self, magnitude, wave_direction='up'):
        self.wavefronts.append({
            'direction': wave_direction,
            'position': 0,
            'damping': 1.0,
            'max_distance': self.grid_h if wave_direction in ['up', 'down'] else self.grid_w,
            'amplitude': magnitude // 3
        })

    def update_edge_wavefronts(self):
        new_wavefronts = []
        for wavefront in self.wavefronts:
            wave_amplitude = wavefront['amplitude'] * wavefront['damping']

            force_magnitude = wave_amplitude
            direction = wavefront['direction']
            position = wavefront['position']

            if direction == 'right':
                self.edge_force[position, :, 0:3] = [0, force_magnitude, 0]
            elif direction == 'left':
                self.edge_force[self.grid_w - position - 1, :, 0:3] = [0, force_magnitude, 0]
            elif direction == 'up':
                self.edge_force[:, self.grid_h - position - 1, 0:3] = [0, force_magnitude, 0]
            elif direction == 'down':
                self.edge_force[:, position, 0:3] = [0, force_magnitude, 0]

            # Update position
            wavefront['position'] += self.wave_speed
            if wavefront['position'] >= wavefront['max_distance']:
                wavefront['direction'] = self.reverse_directions[direction]
                wavefront['damping'] *= self.wave_damping_factor
                wavefront['position'] = 0

            if wave_amplitude > 0.01:
                new_wavefronts.append(wavefront)

        self.wavefronts = new_wavefronts

    def generate_radial_wavefront(self, center_x, center_y, magnitude):
        mg = np.real(magnitude)
        new_wavefront = {'center_x': center_x, 'center_y': center_y,
                        'radius': 0, 'magnitude': mg,
                        'speed': 20+mg*2, 'max_radius': 1200}
        self.persistent_radial_wavefronts.append(new_wavefront) 

    def update_radial_wavefronts(self, fft_data, amplitude_data):
        force_vectors = np.zeros((self.grid_w, self.grid_h, 3), dtype=float)
        
        # Generate new wavefronts based on current force centers
        if self.radial_waves:
            force_centers = self.identify_force_centers(fft_data, amplitude_data)
            for center_x, center_y, magnitude in force_centers:
                self.generate_radial_wavefront(center_x, center_y, magnitude) 

        new_persistent_wavefronts = []
        for wavefront in self.persistent_radial_wavefronts:
            center_x = wavefront['center_x']
            center_y = wavefront['center_y']
            radius = wavefront['radius']

            # Draw radial wavefronts
            if self.debug:
                pygame.draw.circle(self.visualizer.screen, (255,0,0), (center_x, center_y), radius, 2)

            dx = self.particles[:,:,0] - center_x
            dy = self.particles[:,:,1] - center_y
            distance = np.sqrt(dx ** 2 + dy ** 2)

            # Gaussian profile for the force
            gaussian_width = 30.0  # This width can be adjusted
            gaussian_profile = np.exp(-((distance - radius)**2) / (2*gaussian_width**2))

            # Apply radial force only to particles close to the current wavefront radius
            radial_force = wavefront['magnitude']

            force_vectors[:,:,0] += gaussian_profile * radial_force * np.cos(np.arctan2(dy, dx))
            force_vectors[:,:,1] += gaussian_profile * radial_force * np.sin(np.arctan2(dy, dx))
            
            # Update radius for next frame
            wavefront['radius'] += wavefront['speed']
            
            # Remove old wavefronts
            if wavefront['radius'] < wavefront['max_radius']:
                new_persistent_wavefronts.append(wavefront)

        self.persistent_radial_wavefronts = new_persistent_wavefronts

        # Dampen the radial forces a bit
        force_vectors *= 0.3

        return force_vectors

    def identify_force_centers(self, fft_data, amplitude_data, random=False):
        if random:
            x = np.random.randint(0, self.screen_w)
            y = np.random.randint(0, self.screen_h)
            self.force_center = (x, y)

        # Use the amplitude to set the magnitude of the radial force
        magnitude = np.max(amplitude_data)

        return [(self.force_center[0], self.force_center[1], magnitude)]

    def draw(self):
        for i in range(self.grid_w):
            for j in range(self.grid_h):
                x, y, w = self.transformed_points[i, j]
                r, g, b = self.particle_colors[i, j]
                pygame.draw.circle(self.visualizer.screen, (r, g, b), (x, y), 2)

    def debug_draw(self, i, j, x, y):
        # Draw velocity vectors (scaled down for visibility)
        velocity = self.particles[i, j, 3:5] * 10
        end_point = (int(x + velocity[0]), int(y + velocity[1]))
        pygame.draw.line(self.visualizer.screen, (255, 0, 0), (x, y), end_point)
