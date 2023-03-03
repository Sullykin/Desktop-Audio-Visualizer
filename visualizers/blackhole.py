import math
import pygame
import pygame.gfxdraw
import numpy as np
import random

# emite soundwaves through the disk, brightening the color via pitch or amp; requires using distance from center formula

class BlackHole:
    def __init__(self, visualizer):
        self.jets = Jet(visualizer)
        self.accretion_disk = AccretionDisk(visualizer)
        self.accretion_disk.jets = self.jets
        self.visualizer = visualizer
        self.radius = 100
        self.center = (visualizer.SCREEN_WIDTH//2,visualizer.SCREEN_HEIGHT//2)

    def update(self, audio_features):
        volume = audio_features["volume"]
        if self.accretion_disk.disk_speed >= 0.1:
            self.jets.active = True
        elif self.accretion_disk.disk_speed < 0.09:
            self.jets.active = False

        self.accretion_disk.update(volume)
        disk_normal = self.jets.particle_system.rotate_points_around_axis(self.accretion_disk.rotation_speed, self.accretion_disk.rotation_axis, self.accretion_disk.center, self.accretion_disk.disk_normal)
        self.jets.update(disk_normal)

    def draw(self):
        pygame.draw.circle(self.visualizer.screen, (0,0,0), self.center, self.radius)
        self.accretion_disk.draw()
        self.jets.draw()


class AccretionDisk:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.screen_w = visualizer.SCREEN_WIDTH
        self.screen_h = visualizer.SCREEN_HEIGHT
        self.center = (self.screen_w//2,self.screen_h//2,0)
        self.inner_radius = 150
        self.outer_radius = 500
        self.color = self.visualizer.color
        self.setup_transformation_vars()
        disk_positions = generate_disk_points(4000, self.inner_radius, self.outer_radius, self.center)
        self.particle_system = ParticleSystem(visualizer, disk_positions)
        # self.rotate_from_start_pos(self, target_vector=np.array([0.1,0.9,0]))

    """
    def rotate_from_start_pos(self, target_vector):
        # Rotate the disk and jet to a specified vector before starting
        # has minor issue with disk spin axis
        self.particle_system.positions = transform_disk(self.disk_normal, self.particle_system.positions, target_vector)
        self.jets.particle_system.positions = transform_disk(self.disk_normal, self.jets.particle_system.positions, target_vector)
        self.disk_normal = target_vector
    """

    def setup_transformation_vars(self):
        self.rotation_speed = 0.005  # radians per frame
        self.disk_speed = 0.05
        self.rotation_axis = [0.4,0.7,0.1]
        self.target_axis = [0,0,1]
        self.tolerance = 0.01
        self.disk_normal = np.array([0,0,1])

    def update(self, volume):
        self.color = self.visualizer.color
        if volume > 12 and self.disk_speed <= 0.1:
            self.disk_speed += 0.001
        elif self.disk_speed > 0.005:
            self.disk_speed -= 0.0002
        self.disk_normal = self.particle_system.rotate_points_around_axis(self.rotation_speed, self.rotation_axis, self.center, self.disk_normal)
        disk_normal = self.particle_system.rotate_points_around_axis(self.disk_speed, self.disk_normal, self.center, self.disk_normal)
        self.randomize_rotation_axis()
        #self.check_target_axis()

    def randomize_rotation_axis(self):
        # slightly change the rotation axis at random intervals
        if random.random() < 0.001:
            axis = random.randint(0,2)
            self.rotation_axis[axis] += random.uniform(-0.2, 0.2)

    def draw(self):
        self.particle_system.draw(self.color)

    """
    def check_target_axis(self):
        t_np = self.disk_normal
        target_np = np.array(self.target_axis)
        within_tolerance = np.allclose(t_np, target_np, rtol=0, atol=self.tolerance)
        if within_tolerance and not self.jets.particle_system.positions.any():
            target_vec = [0,1,0]
            self.particle_system.positions = transform_disk(self.disk_normal, self.particle_system.positions, target_vec, self.screen_w, self.screen_h)
            self.disk_normal = target_vec
    """


class Jet:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.color = visualizer.color
        self.particle_rate = 30
        jet_positions = generate_jet_positions(num_particles=1, jet_radius=10, jet_height=100, center=(visualizer.SCREEN_WIDTH/2, visualizer.SCREEN_HEIGHT/2))
        self.particle_system = ParticleSystem(visualizer, jet_positions)
        self.active = False

    def update(self, disk_normal):
        self.particle_system.update(disk_normal)
        if self.active:
            new_points = [generate_new_jet_point(disk_normal) for i in range(self.particle_rate)]
            new_points_array = np.vstack(new_points)
            self.particle_system.positions = np.vstack([self.particle_system.positions, new_points_array])

    def draw(self):
        self.particle_system.draw(self.visualizer.color)


class ParticleSystem:
    def __init__(self, visualizer, positions=np.array([])):
        self.visualizer = visualizer
        self.screen_w = visualizer.SCREEN_WIDTH
        self.screen_h = visualizer.SCREEN_HEIGHT
        self.center = (self.screen_w//2,self.screen_h//2,0)
        self.positions = positions

    def update(self, disk_normal):
        self.positions = translate_points_away_from_disk(self.positions, disk_normal, translation_speed=30)
        self.positions = self.remove_offscreen_particles(self.positions, self.screen_w, self.screen_h)

    def draw(self, color): # 900, 500, 200
        radius_squared = 100 ** 2   
        for position in self.positions:
            int_position = [int(x) for x in position]
            point2d = (int_position[0], position[1])
            distance2d_squared = (point2d[0] - self.screen_w//2) ** 2 + (point2d[1] - self.screen_h//2) ** 2
            distance3d_squared = distance2d_squared + position[2] ** 2
            # if not inside sphere or behind it
            if not (distance3d_squared <= radius_squared) and not (distance2d_squared <= radius_squared and position[2] < 100):
                pygame.draw.circle(self.visualizer.screen, color, point2d, 1)

    def rotate_points_around_axis(self, angle, axis, center, disk_normal):
        points = self.positions
        center = np.array(center)
        axis = np.array(axis)
        u = axis / np.linalg.norm(axis)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        rotation_matrix = np.array([
            [cos_a + u[0]**2*(1-cos_a), u[0]*u[1]*(1-cos_a) - u[2]*sin_a, u[0]*u[2]*(1-cos_a) + u[1]*sin_a],
            [u[1]*u[0]*(1-cos_a) + u[2]*sin_a, cos_a + u[1]**2*(1-cos_a), u[1]*u[2]*(1-cos_a) - u[0]*sin_a],
            [u[2]*u[0]*(1-cos_a) - u[1]*sin_a, u[2]*u[1]*(1-cos_a) + u[0]*sin_a, cos_a + u[2]**2*(1-cos_a)]
        ])
        points_centered = points - center
        rotated_points = np.dot(rotation_matrix, points_centered.T).T
        disk_normal = np.dot(rotation_matrix, disk_normal)
        rotated_points += center
        self.positions = rotated_points
        return disk_normal

    def translate_points_to_center(self, points, indices):
        # translate the chosen points towards the center
        for i in indices:
            points[i] = points[i] - 0.01 * (points[i] - self.center)
        return points

    def remove_offscreen_particles(self, positions, screen_width, screen_height):
        """
        This function is applied when particles are assumed
        to never return to the screen such as a jet shooting
        out into space.
        """
        # Create boolean mask for particles that are on screen
        on_screen_mask = np.logical_and.reduce((
            positions[:, 0] >= 0,
            positions[:, 0] <= screen_width,
            positions[:, 1] >= 0,
            positions[:, 1] <= screen_height,
        ))
        
        # Remove particles that are off screen
        positions = positions[on_screen_mask]
        return positions


def generate_disk_points(num_points, min_radius, max_radius, center):
    center = np.array(center)
    rand_radii = np.random.uniform(min_radius, max_radius, num_points)
    rand_angles = np.random.uniform(0, 2*np.pi, num_points)
    x = rand_radii * np.cos(rand_angles) + center[0]
    y = rand_radii * np.sin(rand_angles) + center[1]
    z = np.zeros(num_points) + center[2]
    return np.array([x, y, z]).T

"""
def transform_disk(normal_vec, points, target_normal_vec):
    # Define a scaling matrix to convert from Pygame's coordinate system to standard Cartesian coordinates
    S = np.array([[1, 0, 0], [0, -1, 0], [0, 0, 1]])

    # Normalize the input and target normal vectors
    u = normal_vec / np.linalg.norm(normal_vec)
    v = target_normal_vec / np.linalg.norm(target_normal_vec)

    # Calculate the cross product of the input and target normal vectors
    w = np.cross(u, v)

    # Calculate the rotation matrix using the Rodrigues formula
    if np.allclose(w, 0):
        # Input and target normal vectors are parallel
        R = np.eye(3)
    else:
        theta = np.arccos(np.dot(u, v))
        K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
        R = np.eye(3) + np.sin(theta) * K + (1 - np.cos(theta)) * np.dot(K, K)

    # Step 1: Apply the translation to center the disk at the origin
    center = np.array((1920/2,1080/2,0))
    centered_points = points - center
    # Step 2: Apply scaling to convert to standard Cartesian coordinates
    scaled_points = np.dot(np.linalg.inv(S), centered_points.T).T
    # Step 3: Calculate the rotated points
    rotated_points = np.dot(R, scaled_points.T).T
    # Step 4: Apply scaling to convert back to pygame coordinates
    unscaled_points = np.dot(S, rotated_points.T).T
    # Step 5: Apply the translation to move the disk back to the center of the screen
    new_points = unscaled_points + center

    return new_points
"""

def translate_points_away_from_disk(points, disk_normal, translation_speed=10, disk_center=np.array([960, 540, 0])):
    """Translates points away from a 3D disk of particles."""
    # Normalize the normal vector
    normal_vector = disk_normal / np.linalg.norm(disk_normal)
    # Calculate the distance of each point from the disk plane
    distances = np.sum((points - disk_center) * normal_vector, axis=1)
    # Check which points are above or below the disk
    above_disk = distances > 0
    below_disk = distances < 0
    # Translate the above points away from the disk plane
    points[above_disk] += normal_vector * translation_speed
    # Translate the below points away from the disk plane
    points[below_disk] -= normal_vector * translation_speed
    return points

def generate_jet_positions(num_particles, jet_radius, jet_height, center):
    # Generate particle positions along a circular arc around the black hole
    positions = []
    for i in range(num_particles):
        # Calculate x and y coordinates of particle position
        x, y = rand_point(jet_radius, center[0], center[1])
        # Choose random height along the jet
        z_up = random.uniform(100, jet_height)
        z_down = random.uniform(-100, -jet_height)
        z = random.choice([z_up, z_down])
        positions.append([x, y, z])
    
    return np.array(positions)

def generate_new_jet_point(disk_normal, disk_center=(960, 540, 0), radius=20, distance=50):
    """Creates a point randomly on the disk plane within a given radius from the disk center, and translates it up or down from the disk plane by a given distance."""
    # Generate a random point on the disk plane within the radius from the disk center
    theta = np.random.uniform(0, 2*np.pi)
    r = np.random.uniform(0, radius)
    point_on_disk = np.array([disk_center[0] + r*np.cos(theta), disk_center[1] + r*np.sin(theta), disk_center[2]])
    # Choose randomly whether to translate the point up or down from the disk plane
    direction = np.random.choice([-1, 1])
    # Calculate the translation vector based on the disk normal and the chosen direction
    translation = direction * distance * np.array(disk_normal)
    # Translate the point along the translation vector
    translated_point = point_on_disk + translation
    return translated_point

def rand_point(radius, x_center, y_center):
    x_center = x_center
    y_center = y_center
    x_min = x_center - radius
    x_max = x_center + radius
    y_min = y_center - radius
    y_max = y_center + radius
    radius = radius
    output = [0, 0]
    while True:
        output[0], output[1] = random.uniform(x_min, x_max), random.uniform(y_min, y_max)
        if math.sqrt(pow(output[0]-x_center,2) + pow(output[1]-y_center,2)) <= radius:
            return output