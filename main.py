import imgui
import pygame
from imgui.integrations.pygame import PygameRenderer
from pygame.locals import DOUBLEBUF, OPENGL
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import sys



WIDTH, HEIGHT = 1200, 720 # Ancho y alto de la pantalla
TARGET_FPS = 60 # Limite de FPS
PHYSICS_DT = 1.0 / 60.0 # Resolución de leapfrog
MAX_SUBSTEPS = 12 # Maximo de pasos que realiza por frame
SIM_SPEED = 1.0 # Multiplicador de velocidad visual
G = 1.0 # Constante gravitacional
EPS = 0.2 # Suavizado para encuentros muy cercanos
MAX_DIST = 1000.0 # Distancia maxima de camara

bodies = [] # Todos los cuerpos que se dibujan
planets = [] # Cuerpos afectados por todas las fuerzas
hot_bodies = [] # Cuerpos ganadores en colisión reciente
hot_bodies_time = [] # Tiempo de colisión en cuerpos ganadores


def load_texture(path):
    surf = pygame.image.load(path).convert_alpha()
    img = pygame.image.tostring(surf, "RGBA", True)
    w, h = surf.get_size()
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img)
    glGenerateMipmap(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tex


def magnitude(x, y, z):
    return math.sqrt(x * x + y * y + z * z)


class CelestialObject:
    def __init__(self, mass, radius, color, x, y, z, dynamic, father=None, name=None, texture=None, black=False, spin_speed=0.0, tilt=0.0):
        self.mass = mass
        self.default_mass = mass
        self.radius = radius
        self.color = color
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.vel_x, self.vel_y, self.vel_z = 0.0, 0.0, 0.0
        self.accel_x, self.accel_y, self.accel_z = 0.0, 0.0, 0.0
        self.father = father
        self.dynamic = dynamic
        self.name = name
        self.black = black
        self.volume = 4 * math.pi * radius * radius * radius / 3
        self.texture = texture
        self.spin = 0.0
        self.spin_speed = spin_speed
        self.tilt = tilt

        if father is not None: # Inicialización de velocidad orbital cuando se tiene un cuerpo padre
            dx, dy, dz = self.x - father.x, self.y - father.y, self.z - father.z
            r = magnitude(dx, dy, dz)
            if r > 0: # Version suavizada de la velocidad orbital circular
                d = (r * r + EPS * EPS) ** 1.5
                v_tan = math.sqrt(G * father.mass * (r * r) / d)

                r_hat = (dx / r, dy / r, dz / r)
                up = (0.0, 0.0, 1.0)
                if abs(r_hat[0] * up[0] + r_hat[1] * up[1] + r_hat[2] * up[2]) > 0.99:
                    up = (0.0, 1.0, 0.0)

                tx = up[1] * r_hat[2] - up[2] * r_hat[1]
                ty = up[2] * r_hat[0] - up[0] * r_hat[2]
                tz = up[0] * r_hat[1] - up[1] * r_hat[0]
                t_norm = math.sqrt(tx * tx + ty * ty + tz * tz)
                tx, ty, tz = tx / t_norm, ty / t_norm, tz / t_norm

                self.vel_x = father.vel_x + v_tan * tx
                self.vel_y = father.vel_y + v_tan * ty
                self.vel_z = father.vel_z + v_tan * tz


    def calculate_acceleration(self): # Uso de gravedad newtoniana con suavizado tipo Plummer
        global planets
        if not self.dynamic:
            self.accel_x = 0.0
            self.accel_y = 0.0
            self.accel_z = 0.0
            return
        ax, ay, az = 0.0, 0.0, 0.0
        for body in planets:
            if body is self:
                continue
            dir_x = body.x - self.x
            dir_y = body.y - self.y
            dir_z = body.z - self.z
            dist = math.sqrt(dir_x * dir_x + dir_y * dir_y + dir_z * dir_z)
            min_d = body.radius + self.radius
            if dist <= min_d:
                collide(self, body)

            r2 = dir_x * dir_x + dir_y * dir_y + dir_z * dir_z + EPS * EPS
            inv_r = 1.0 / math.sqrt(r2)
            inv_r3 = inv_r * inv_r * inv_r
            ax += G * body.mass * dir_x * inv_r3
            ay += G * body.mass * dir_y * inv_r3
            az += G * body.mass * dir_z * inv_r3
        self.accel_x, self.accel_y, self.accel_z = ax, ay, az


    def integrate_pos(self, dt):
        if self.dynamic: # Si el cuerpo es dinámico, se cambia su posición
            self.vel_x += 0.5 * self.accel_x * dt
            self.vel_y += 0.5 * self.accel_y * dt
            self.vel_z += 0.5 * self.accel_z * dt
            self.x += self.vel_x * dt
            self.y += self.vel_y * dt
            self.z += self.vel_z * dt


    def integrate_vel(self, dt):
        if self.dynamic: # Si el cuerpo es dinámico se cambia su velocidad
            self.vel_x += 0.5 * self.accel_x * dt
            self.vel_y += 0.5 * self.accel_y * dt
            self.vel_z += 0.5 * self.accel_z * dt


    def calculate_radius(self, volume): # Se calcula el tamaño del radio a partir de su volumen
        self.volume += volume
        self.radius = math.pow((3 * self.volume) / (math.pi * 4), 1/3)


def create_asteroid_belt(sun, n, r_inner, r_outer, texture=None): # Generación de anillo de asteroides
    rocks = []
    for _ in range(n):
        r = random.uniform(r_inner, r_outer)
        theta = random.uniform(0, 2 * math.pi)
        x = sun.x + r * math.cos(theta)
        y = sun.y + r * math.sin(theta)
        mass = 1e-9
        radius = 1 if random.random() < 0.7 else 2
        rock = CelestialObject(mass, radius, (0.7, 0.7, 0.7), x, y, 0, True, sun, None, texture)
        rocks.append(rock)
    return rocks


class OrbitCamera:
    def __init__(self, target_getter, dist, yaw, pitch):
        self.dist = dist
        self.yaw = yaw
        self.pitch = pitch
        self.get_target = target_getter

    def apply(self): # Cambiar la posición de la camara
        tx, ty, tz = self.get_target()
        cx, cy, cz = self.get_camera_pos()
        gluLookAt(cx, cy, cz,  tx, ty, tz,  0, 0, 1)

    def get_camera_pos(self):
        tx, ty, tz = self.get_target()
        r = max(5.0, self.dist)
        rad_yaw = math.radians(self.yaw)
        rad_pitch = math.radians(self.pitch)
        cx = tx + r * math.cos(rad_pitch) * math.cos(rad_yaw)
        cy = ty + r * math.cos(rad_pitch) * math.sin(rad_yaw)
        cz = tz + r * math.sin(rad_pitch)
        return cx, cy, cz


def gl_init():
    glViewport(0, 0, WIDTH, HEIGHT)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    glClearColor(0.02, 0.02, 0.04, 1.0)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60.0, WIDTH / float(HEIGHT), 0.1, 10000.0)

    glMatrixMode(GL_MODELVIEW)

    # Estado base de iluminación/material
    glEnable(GL_LIGHTING)

    # Ambiente global por defecto en 0, se ajusta en update_lights según la condición
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.0, 0.0, 0.0, 1.0))

    # Se apagan las luces por defecto, se encienden/apagan en update_lights
    glDisable(GL_LIGHT0)
    glDisable(GL_LIGHT1)

    # Parámetros "estáticos" de las luces (colores, brillos). La posición/dirección se actualiza cada frame.
    glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.1, 0.1, 0.1, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  (1.0, 1.0, 1.0, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))

    glLightfv(GL_LIGHT1, GL_AMBIENT,  (0.0, 0.0, 0.0, 1.0))
    glLightfv(GL_LIGHT1, GL_DIFFUSE,  (1.0, 1.0, 0.8, 1.0))
    glLightfv(GL_LIGHT1, GL_SPECULAR, (1.0, 1.0, 0.8, 1.0))
    glLightf(GL_LIGHT1, GL_SPOT_CUTOFF,   35.0)
    glLightf(GL_LIGHT1, GL_SPOT_EXPONENT, 8.0)

    # Materiales
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)
    glEnable(GL_NORMALIZE)

    # Texturas
    glEnable(GL_TEXTURE_2D)
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)


quadric = None


def draw_sphere(x, y, z, radius, color_rgb, tex_id=None, tilt=0.0, spin=0.0): # Dibujado de esferas con función ya integrada
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(tilt, 0, 1, 0)
    glRotatef(spin, 0, 0, 1)
    global quadric
    if quadric is None:
        quadric = gluNewQuadric()

        gluQuadricTexture(quadric, GL_TRUE)

    if tex_id:
        glColor3f(1.0, 1.0, 1.0)
        glBindTexture(GL_TEXTURE_2D, tex_id)
    else:
        glColor3f(*color_rgb)
        glBindTexture(GL_TEXTURE_2D, 0)

    gluSphere(quadric, max(0.5, radius), 24, 24)

    glPopMatrix()


def get_behind_position(body, camera, dist=None):
    cx, cy, cz = camera.get_camera_pos()
    bx, by, bz = body.x, body.y, body.z
    dist_cb = math.sqrt((bx - cx) ** 2 + (by - cy) ** 2 + (bz - cz) ** 2)
    if dist is None:
        dist_br = dist_cb * 1
    else:
        dist_br = dist_cb * dist
    t = dist_br / dist_cb
    ring_x = bx + t * (bx - cx)
    ring_y = by + t * (by - cy)
    ring_z = bz + t * (bz - cz)

    return ring_x, ring_y, ring_z


def draw_black_hole(body, camera, ring_t=None):
    # Anillo galactico
    ring_x, ring_y, ring_z = get_behind_position(body, camera, 2.0)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (1.0, 1.0, 1.0, 1.0))
    if ring_t is not None:
        draw_sphere(ring_x, ring_y, ring_z, body.radius * 4.0, (1.0, 1.0, 1.0), ring_t, (camera.yaw + camera.pitch) / 2)
    else:
        draw_sphere(ring_x, ring_y, ring_z, body.radius * 4.0, (1.0, 1.0, 1.0,))

    # Anillo blanco
    ring_x, ring_y, ring_z = get_behind_position(body, camera, 0.8)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (1.0, 1.0, 1.0, 1.0))
    draw_sphere(ring_x, ring_y, ring_z, body.radius * 1.53, (1.0, 1.0, 1.0))

    # Centro negro
    glDisable(GL_LIGHTING)
    draw_sphere(body.x, body.y, body.z, body.radius * 0.8, body.color)
    glEnable(GL_LIGHTING)


def update_lights(sun, camera):
    tx, ty, tz = camera.get_target()
    r = max(5.0, camera.dist)
    rad_yaw   = math.radians(camera.yaw)
    rad_pitch = math.radians(camera.pitch)
    cx = tx + r * math.cos(rad_pitch) * math.cos(rad_yaw)
    cy = ty + r * math.sin(rad_pitch)
    cz = tz + r * math.cos(rad_pitch) * math.sin(rad_yaw)

    light_pos = (sun.x, sun.y, sun.z, 1.0)
    spot_dir  = (cx - sun.x, cy - sun.y, cz - sun.z)

    if sun in planets:
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.0, 0.0, 0.0, 1.0))

        # Light 0: punto en el Sol
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)

        # Light 1: spotlight del Sol hacia la cámara
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT1, GL_SPOT_DIRECTION, spot_dir)

    else:
        glDisable(GL_LIGHT0)
        glDisable(GL_LIGHT1)

        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.3, 0.3, 0.3, 1.0))

        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))


def collide(body1, body2): # Simulado de colisión en objetos
    global bodies, planets
    lst = ['Earth', 'Moon']
    if body1.name is None and body2.name is None or body1.name in lst and body2.name in lst: # Eliminar colisión entre tierra y luna
        return
    loser, winner = (body2, body1) if body1.mass > body2.mass else (body1, body2)
    winner.mass += loser.mass

    winner.calculate_radius(loser.volume)
    heat(winner)

    bodies[:] = [o for o in bodies if o is not loser]
    planets[:] = [o for o in planets if o is not loser]


def heat(body): # Calentar cuerpo para mejor aspecto visual en las colisiones
    global hot_bodies, hot_bodies_time
    if body.black:
        return
    time_elapsed = pygame.time.get_ticks() * 0.001
    if body not in hot_bodies:
        hot_bodies.append(body)
        hot_bodies_time.append(time_elapsed)


def set_title(fps, delta_e, p_mag):
    pygame.display.set_caption(
        f"Simulación Sistema Solar  |  FPS: {fps:5.2f}  |  ΔE%: {delta_e:.6f}  |  |P|: {p_mag:.3e}")


def help():
    print("""
    Tecla               Función
    -----               -------
    Flecha Arriba:      Cambiar a la variable superior a la actual de el cuerpo seleccionado.
    Flecha Abajo:       Cambiar a la variable inferior a la actual de el cuerpo seleccionado.
    Flecha izquierda:   Disminuir variable seleccionada(No aplica a nombre).
    Flecha izquierda:   Aumentar variable seleccionada(No aplica a nombre).
    Q:                  Seleccionar cuerpo anterior.
    E:                  Seleccionar siguiente cuerpo.
    N:                  Crear nuevo cuerpo.
    B:                  Agregar agujero negro base.
    H:                  Listar opciones.\n
    """)


def add_body():
    global planets, bodies
    mass, radius, r, g, b, x, y, z, dynamic, father, name, black = None, None, None, None, None, None, None, None, None, None, None, None

    if input('Presione [e] para cancela r la creación de cuerpo') == 'e':
        return

    while mass is None:
        try:
            mass = float(input("Ingrese la masa del cuerpo planetario: "))
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while radius is None:
        try:
            radius = float(input("Ingrese la radio del cuerpo planetario: "))
            if radius <= 0:
                print('!!! El radio debe ser mayor a 0.')
                radius = None
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while r is None:
        try:
            r = float(input("Ingrese el valor de rojo de 1.0 a 0.0: "))
            if 0.0 > r or r > 1.0:
                r = None
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while g is None:
        try:
            g = float(input("Ingrese el valor de verde de 1.0 a 0.0: "))
            if 0.0 > g or g > 1.0:
                g = None
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while b is None:
        try:
            b = float(input("Ingrese el valor de azul de 1.0 a 0.0: "))
            if 0.0 > b or b > 1.0:
                b = None
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while x is None:
        try:
            x = float(input("Ingrese la posición del cuerpo en eje x: "))
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while y is None:
        try:
            y = float(input("Ingrese la posición del cuerpo en eje y: "))
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while z is None:
        try:
            z = float(input("Ingrese la posición del cuerpo en eje z: "))
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while dynamic is None:
        band = input("El objeto sera dinámico? [y/n] ")
        if band in ['y','Y']:
            dynamic = True
        elif band in ['n','N']:
            dynamic = False
        else:
            print('!!! Valor invalido.')

    while father is None:
        for i, body in enumerate(planets):
            print(f'[{i}] Name: {body.name}.')
        try:
            index = int(input("Ingrese el indice del cuerpo padre (-1 para que no tenga padre): "))
            if 0 <= index < len(planets):
                father = planets[index]
            elif index == -1:
                break
            else:
                print('!!! Valor invalido.')
        except ValueError:
            print("!!! Entrada no numérica. Intente de nuevo.")

    while name is None:
        name = input("Ingrese el nombre del cuerpo: ").strip()

        if name == "":
            name = None
            print("!!! El nombre no puede ser vacío.")

    while black is None:
        band = input("El objeto sera un agujero negro(color se convertirá en negro)? [y/n] ")
        if band in ['y', 'Y']:
            black = True
            r, g, b = 0.0, 0.0, 0.0
        elif band in ['n', 'N']:
            black = False
        else:
            print('!!! Valor invalido.')

    while True:
        band = input("Esta seguro que desea crear el cuerpo? [y/n] ")
        if band in ['y', 'Y']:
            break
        elif band in ['n', 'N']:
            return
        else:
            print('!!! Valor invalido.')

    body = CelestialObject(mass, radius, (r, g, b), x, y, z, dynamic, father, name, black)

    planets.append(body)
    bodies.append(body)


def compute_totals(): # Se revisa la estabilidad de la simulación
    global bodies
    u = 0.0
    k = 0.0
    px = 0.0
    py = 0.0
    pz = 0.0
    for i in range(len(bodies)):
        px += bodies[i].mass * bodies[i].vel_x
        py += bodies[i].mass * bodies[i].vel_y
        pz += bodies[i].mass * bodies[i].vel_z
        k += bodies[i].mass * (bodies[i].vel_x**2 + bodies[i].vel_y**2 + bodies[i].vel_z**2) / 3
        for j in range(i + 1, len(bodies)):
            dx = bodies[i].x - bodies[j].x
            dy = bodies[i].y - bodies[j].y
            dz = bodies[i].z - bodies[j].z
            u += - G * bodies[i].mass * bodies[j].mass / math.sqrt(dx*dx + dy*dy + dz*dz + EPS*EPS)
    e = k + u
    return px, py, pz, k, u, e # px, py, pz: Momento lineal total k: energía cinetica total e = k + u: energía mecánica total


def main():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    clock = pygame.time.Clock()
    gl_init()
    imgui.create_context()
    renderer = PygameRenderer()  # se engancha a la ventana de pygame/OpenGL
    io = imgui.get_io()
    io.display_size = (WIDTH, HEIGHT)

    stars_t, sun_t, mercury_t, venus_t, earth_t, moon_t, mars_t,  asteroid_t, jupiter_t, saturn_t, neptune_t, bh_ring_t = None, None, None, None, None, None, None, None, None, None, None, None
    try:
        stars_t = load_texture('assets/stars.jpg')
        sun_t = load_texture('assets/sun.jpg')
        mercury_t = load_texture('assets/mercury.jpg')
        venus_t = load_texture('assets/venus.jpg')
        earth_t = load_texture('assets/earth.jpg')
        moon_t = load_texture('assets/moon.jpg')
        mars_t = load_texture('assets/mars.jpg')
        jupiter_t = load_texture('assets/jupiter.jpg')
        saturn_t = load_texture('assets/saturn.jpg')
        neptune_t = load_texture('assets/neptune.jpg')
        bh_ring_t = load_texture('assets/bh_ring_max_b.jpg')
    except FileNotFoundError:
        print('!!! Problem loading textures.')


    sun = CelestialObject(10000, 22, (1.0, 0.95, 0.2), 0, 0, 0, True, None, 'Sun', sun_t, False, 0.164)
    bodies.append(sun)

    mercury = CelestialObject(1 / 597, 3, (0.41, 0.41, 0.41), sun.x - 49, 0, 0, True, sun, 'Mercury', mercury_t, False, 0.072, 0.034)
    bodies.append(mercury)

    venus = CelestialObject(2 / 81, 5, (0.93, 0.91, 0.67), sun.x - 72, 0, 0, True, sun, 'Venus', venus_t, False, -0.017, 177.4)
    bodies.append(venus)

    earth = CelestialObject(1 / 33, 5, (0.0, 0.75, 1.0), sun.x - 100, 0, 0, True, sun, 'Earth', earth_t, False, 4.18, 23.44)
    bodies.append(earth)

    moon = CelestialObject(1 / 2673, 2, (0.6, 0.6, 0.6), earth.x + 0.4, earth.y, 0, True, earth, 'Moon', moon_t, False, 0.153, 6.68)
    bodies.append(moon)

    mars = CelestialObject(1.07 / 330, 4, (1.0, 0.27, 0.0), sun.x - 152, 0, 0, True, sun, 'Mars', mars_t, False, 4.06, 25.19)
    bodies.append(mars)

    jupiter = CelestialObject(48 / 5, 11, (0.80, 0.52, 0.25), sun.x - 520, 0, 0, True, sun, 'Jupiter', jupiter_t, False, 10.07, 3.13)
    bodies.append(jupiter)

    asteroids = create_asteroid_belt(sun, 600, 210, 330, asteroid_t)
    bodies.extend(asteroids)

    saturn = CelestialObject(240 / 83, 9.5, (0.82, 0.71, 0.55), sun.x - 958, 0, 0, True, sun, 'Saturn', saturn_t, False, 9.34, 26.73)
    bodies.append(saturn)

    neptune = CelestialObject(10 / 19, 6.5, (0.25, 0.41, 0.88), sun.x - 3005, 0, 0, True, sun, 'Neptune', neptune_t, False, 6.21, 28.32)
    bodies.append(neptune)

    black_hole = CelestialObject(10000, 10, (0.0, 0.0, 0.0), 0, 0, 300, True, None, 'Black Hole', None, True)

    planets.extend([sun, mercury, venus, earth, moon, mars, jupiter, saturn, neptune])


    # Momento inicial de el sol
    px = sum(b.mass * b.vel_x for b in planets if b is not sun)
    py = sum(b.mass * b.vel_y for b in planets if b is not sun)
    sun.vel_x = -px / sun.mass
    sun.vel_y = -py / sun.mass

    # Cuerpo seleccionado
    selection = sun
    selection_id = 0

    # Declarado de camara
    camera = OrbitCamera(lambda: (selection.x, selection.y, selection.z), 800.0, 0.0, 0.0)

    running = True
    accumulator = 0.0
    first_run = True
    e0 = 0.0
    frame_count = 0
    delta_e = 0.0

    dragging = False
    last_mouse = (0, 0)

    # Opciones de modificación
    option = 0
    options = 5
    white = (1.0, 1.0, 1.0, 1.0)
    yellow = (1.00, 0.86, 0.38, 1.0)
    # 0 Nombre, 1 Masa, 2 Volumen, 3 Vel X, 4 Vel Y, 5 Vel Z

    print("Presione [H] para desplegar las opciones.")

    while running:
        frame_seconds = clock.tick(TARGET_FPS) / 1000.0
        accumulator += frame_seconds * SIM_SPEED
        io.delta_time = max(frame_seconds, 1 / 1000.0)

        if selection not in planets:
            selection = planets[0]
            selection_id = 0

        for event in pygame.event.get():
            renderer.process_event(event)
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_b: # Agregar agujero negro de prueba
                    bodies.append(black_hole)
                    planets.append(black_hole)

                if event.key == pygame.K_n: # Añadir nuevo cuerpo
                    add_body()

                if event.key == pygame.K_h: # Mensaje de ayuda en consola
                    help()

                if event.key == pygame.K_UP:
                    if option > 0:
                        option -= 1
                    else:
                        option = options
                if event.key == pygame.K_DOWN:
                    if option < 5:
                        option += 1
                    else:
                        option = 0

                if event.key == pygame.K_RIGHT: # Aumentar
                    if option == 1: # Masa
                        selection.mass += selection.default_mass * 0.10
                    elif option == 2: # Volumen
                        selection.volume += selection.volume * 0.10
                        selection.calculate_radius(selection.volume * 0.10)
                    elif option == 3: # Velocidad X
                        selection.vel_x += 1
                    elif option == 4: # Velocidad Y
                        selection.vel_y += 1
                    elif option == 5: # Velocidad Z
                        selection.vel_z += 1

                if event.key == pygame.K_LEFT: # Disminuir
                    if option == 1: # Masa
                        selection.mass -= selection.default_mass * 0.10
                    elif option == 2: # Volumen
                        selection.volume -= selection.volume * 0.10
                        selection.calculate_radius(-selection.volume * 0.10)
                    elif option == 3: # Velocidad X
                        selection.vel_x -= 1
                    elif option == 4: # Velocidad Y
                        selection.vel_y -= 1
                    elif option == 5: # Velocidad Z
                        selection.vel_z -= 1

                # Selecciones de cuerpos
                if event.key == pygame.K_q:
                    try:
                        if selection_id > 0:
                            selection_id -= 1
                        else:
                            selection_id = (len(planets) - 1)
                        selection = planets[selection_id]
                    except IndexError:
                        selection_id = 0
                        selection = planets[selection_id]
                if event.key == pygame.K_e:
                    if selection_id < (len(planets) - 1):
                        selection_id += 1
                    else:
                        selection_id = 0
                    selection = planets[selection_id]

            # Movimiento de la camara
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    dragging = True
                    last_mouse = event.pos
                elif event.button == 4:  # wheel up
                    camera.dist = max(selection.radius * 2, camera.dist * 0.9)
                elif event.button == 5:  # wheel down
                    camera.dist = min(MAX_DIST, camera.dist / 0.9)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                dx = mx - last_mouse[0]
                dy = my - last_mouse[1]
                camera.yaw -= dx * 0.3
                camera.pitch = max(-89.0, min(89.0, camera.pitch + dy * 0.3))
                last_mouse = (mx, my)

        # Cálculo de físicas
        substeps = 0
        while accumulator >= PHYSICS_DT and substeps < MAX_SUBSTEPS:
            for body in bodies:
                body.calculate_acceleration()
            for body in bodies:
                body.integrate_pos(PHYSICS_DT)
            for body in bodies:
                body.calculate_acceleration()
            for body in bodies:
                body.integrate_vel(PHYSICS_DT)
            accumulator -= PHYSICS_DT
            substeps += 1

        for body in bodies:
            body.spin = (body.spin + body.spin_speed * frame_seconds) % 360.0

        px, py, pz, k, u, e = compute_totals()
        if first_run:
            first_run = False
            e0 = e
        frame_count += 1
        if frame_count == 60:
            delta_e = 100 * (e - e0) / abs(e0)
            frame_count = 0
        set_title(clock.get_fps(), delta_e, magnitude(px, py, pz))

        # Iluminación y trazado de cuerpos en pantalla
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        camera.apply()
        update_lights(sun, camera)

        if stars_t is not None:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (1.0, 1.0, 1.0, 1.0))
            draw_sphere(0, 0, 0, MAX_DIST + 5000.0, (1.0, 1.0, 1.0), stars_t)

        for body in bodies:
            if body is sun:
                glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (1.0, 0.95, 0.4, 1.0))
            elif body in hot_bodies:
                i = hot_bodies.index(body)
                dt = (pygame.time.get_ticks() * 0.001 - hot_bodies_time[i] )
                if 15.0 < dt:
                    hot_bodies.pop(i)
                    hot_bodies_time.pop(i)
                    i -= 1
                elif 5.0 > dt:
                    p = dt * 0.1
                    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION,(p, p * 0.4, p * 0.4, 1.0))
                else:
                    p = (dt - 5.0) * 0.05
                    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.5 - p, 0.2 - p * 0.4, 0.2 - p * 0.4, 1.0))
            else:
                glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
            if body == moon:
                dx, dy = moon.x - earth.x, moon.y - earth.y
                draw_x = earth.x + 20.0 * dx
                draw_y = earth.y + 20.0 * dy

                draw_sphere(draw_x, draw_y, body.z, body.radius, body.color, body.texture, body.tilt, body.spin)
            elif body.black:
                draw_black_hole(body, camera, bh_ring_t)
            else:
                draw_sphere(body.x, body.y, body.z, body.radius, body.color, body.texture, body.tilt, body.spin)

        # Dibujado de interfaz
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        imgui.new_frame()
        imgui.set_next_window_position(10, 10)  # esquina sup. izq.
        imgui.set_next_window_size(180, 340)
        flags = (imgui.WINDOW_NO_TITLE_BAR
                 | imgui.WINDOW_NO_RESIZE
                 | imgui.WINDOW_NO_MOVE
                 | imgui.WINDOW_NO_SAVED_SETTINGS
                 | imgui.WINDOW_NO_FOCUS_ON_APPEARING
                 | imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS)
        imgui.begin("HUD", True, flags)
        # Atributos modificables
        color = yellow if option == 0 else white
        imgui.text_colored(f"Name: {selection.name}", *color)
        color = yellow if option == 1 else white
        imgui.text_colored(f"Mass: {selection.mass}", *color)
        color = yellow if option == 2 else white
        imgui.text_colored(f"Volume: {selection.volume:.1f}", *color)
        color = yellow if option == 3 else white
        imgui.text_colored(f"Vel X: {selection.vel_x:.2f}", *color)
        color = yellow if option == 4 else white
        imgui.text_colored(f"Vel Y: {selection.vel_y:.2f}", *color)
        color = yellow if option == 5 else white
        imgui.text_colored(f"Vel Z: {selection.vel_z:.2f}", *color)
        # Atributos dinámicos
        imgui.text('')
        imgui.text_colored(f"Radius: {selection.radius:.2f}", *white)
        imgui.text('')
        imgui.text_colored(f"Accel X: {selection.accel_x:.2f}", *white)
        imgui.text_colored(f"Accel Y: {selection.accel_y:.2f}", *white)
        imgui.text_colored(f"Accel Z: {selection.accel_z:.2f}", *white)
        imgui.text('')
        imgui.text_colored(f"Tilt Degrees: {selection.tilt:.2f}", *white)
        imgui.text_colored(f"Spin Degrees: {selection.spin:.2f}", *white)
        imgui.text('')
        imgui.text_colored(f"X position: {selection.x:.2f}", *white)
        imgui.text_colored(f"Y position: {selection.y:.2f}", *white)
        imgui.text_colored(f"Z position: {selection.z:.2f}", *white)


        imgui.end()

        imgui.render()
        renderer.render(imgui.get_draw_data())

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
