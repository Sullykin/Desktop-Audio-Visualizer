import math
import pygame
import pygame.gfxdraw
import numpy as np
import random

class BlackHole:
    def __init__(self, visualizer):
        self.jets = Jet(visualizer)
        self.accretion_disk = AccretionDisk(visualizer)
        self.accretion_disk.jets = self.jets
        self.visualizer = visualizer
        self.radius = 100
        self.distortion_factor = 0.005

    def update(self, pitch, volume, is_beat):
        if is_beat and self.accretion_disk.disk_speed >= 0.1:
            self.jets.active = True
        elif self.accretion_disk.disk_speed < 0.09:
            self.jets.active = False

        self.accretion_disk.update(pitch, volume, is_beat)
        disk_normal = self.jets.particle_system.rotate_points_around_axis(self.accretion_disk.rotation_speed, self.accretion_disk.rotation_axis, self.accretion_disk.center, self.accretion_disk.disk_normal)
        self.jets.update(disk_normal)

    def draw(self):
        #self.visualizer.screen.fill((10,10,10))
        pygame.draw.circle(self.visualizer.screen, (0,0,0), (1920//2,1080//2), self.radius)
        #self.draw_distorted_circle(self.visualizer.screen, (255, 255, 255), (1920/2,1080/2), self.radius*3, self.distortion_factor)
        self.accretion_disk.draw()
        self.jets.draw()

    # Define a function to draw a distorted circle
    def draw_distorted_circle(self, surface, color, center, radius, distortion_factor):
        # Create a meshgrid of points within the circle
        x, y = np.meshgrid(np.arange(center[0]-radius, center[0]+radius+1), np.arange(center[1]-radius, center[1]+radius+1))
        points = np.vstack((x.flatten(), y.flatten())).T
        
        # Calculate the displacement of each point due to the gravitational lensing effect
        displacement = (points - center) * (np.linalg.norm(points - center, axis=1) ** 2 * distortion_factor)
        displacement = np.expand_dims(displacement, axis=1)

        for i in range(360):
            start_angle = np.radians(i)
            end_angle = np.radians(i+1)
            start_point = (np.cos(start_angle) * radius, np.sin(start_angle) * radius)
            start_point = (start_point[0] + center[0] + displacement[i][0], start_point[1] + center[1] + displacement[i][1])
            start_point = tuple(map(int, start_point))  # Convert start_point to a tuple of integers
            pygame.draw.arc(surface, color, pygame.Rect(start_point[0]-radius, start_point[1]-radius, radius * 2, radius * 2), start_angle, end_angle, 1)


class AccretionDisk:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.center = (1920//2,1080//2,0)
        self.inner_radius = 150
        self.outer_radius = 500
        self.rotation_speed = 0.005  # radians per frame
        self.disk_speed = 0.05
        self.rotation_axis = [0.1,0.1,0.3]
        self.target_axis = [0,0,1]
        self.tolerance = 0.01
        self.disk_normal = np.array([0,0,1])
        self.target_disk_normal = np.array([0.1,0.9,0])
        self.color = self.visualizer.color
        num_particles = 6000
        disk_positions = generate_disk_points(num_particles, self.inner_radius, self.outer_radius, self.center)
        self.particle_system = ParticleSystem(visualizer, disk_positions)

        """ Rotate the disk and jet to a specified vector before starting """
        #self.particle_system.positions = transform_disk(self.disk_normal, self.particle_system.positions, self.target_disk_normal)
        #self.jets.particle_system.positions = transform_disk(self.disk_normal, self.jets.particle_system.positions, self.target_disk_normal)
        #self.disk_normal = self.target_disk_normal

    def update(self, pitch, volume, is_beat):
        self.color = self.visualizer.color
        if is_beat:
            self.color = tuple(min(255, max(0, c + 100)) for c in self.color)
        if volume > 12 and self.disk_speed <= 0.1:
            self.disk_speed += 0.001
        elif self.disk_speed > 0.005:
            self.disk_speed -= 0.0002
        self.disk_normal = self.particle_system.rotate_points_around_axis(self.rotation_speed, self.rotation_axis, self.center, self.disk_normal)
        disk_normal = self.particle_system.rotate_points_around_axis(self.disk_speed, self.disk_normal, self.center, self.disk_normal)

        if random.random() < 0.001:
            axis = random.randint(0,2)
            self.rotation_axis[axis] += random.uniform(-0.2, 0.2)

        #self.check_target_axis()

    def draw(self):
        self.particle_system.draw(self.color)

    def check_target_axis(self):
        t_np = self.disk_normal
        target_np = np.array(self.target_axis)
        within_tolerance = np.allclose(t_np, target_np, rtol=0, atol=self.tolerance)
        if within_tolerance and not self.jets.particle_system.positions.any():
            target_vec = [0,1,0]
            self.particle_system.positions = transform_disk(self.disk_normal, self.particle_system.positions, target_vec, 1920, 1080)
            self.disk_normal = target_vec


class Jet:
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.color = visualizer.color
        self.particle_rate = 30
        jet_positions = generate_jet_positions(num_particles=10, jet_radius=10, jet_height=100)
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
        self.center = (1920//2,1080//2,0)
        self.positions = positions

    def update(self, disk_normal):
        self.positions = translate_points_away_from_disk(self.positions, disk_normal, translation_speed=30)
        self.positions = self.remove_offscreen_particles(self.positions, 1920, 1080)

    def draw(self, color):
        for position in self.positions:
            point2d = (int(position[0]), int(position[1]))
            distance2d = math.sqrt((point2d[0] - 1920//2) ** 2 + (point2d[1] - 1080//2) ** 2)
            distance3d = math.sqrt(distance2d ** 2 + position[2] ** 2)
            if not ((int(position[2]) < 0) and distance2d <= 100) and (distance3d >= 100):
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

    def translate_points_to_center(self, points, indices, center=np.array([1920/2, 1080/2, 0])):
        # translate the chosen points towards the center
        for i in indices:
            points[i] = points[i] - 0.01 * (points[i] - center)
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
    # From https://stackoverflow.com/a/6802723
    axis = np.asarray(axis)
    axis = axis / np.sqrt(np.dot(axis, axis))
    a = np.cos(angle/2.0)
    b, c, d = -axis * np.sin(angle/2.0)
    aa, bb, cc, dd = a*a, b*b, c*c, d*d
    bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
    return np.array([[aa+bb-cc-dd, 2*(bc+ad), 2*(bd-ac)],
                     [2*(bc-ad), aa+cc-bb-dd, 2*(cd+ab)],
                     [2*(bd+ac), 2*(cd-ab), aa+dd-bb-cc]])
                    
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

def generate_jet_positions(num_particles, jet_radius, jet_height):
    # Generate particle positions along a circular arc around the black hole
    positions = []
    for i in range(num_particles):
        # Calculate x and y coordinates of particle position
        x, y = rand_point(jet_radius, 1920/2, 1080/2)
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