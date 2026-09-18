
import bpy
import math
import os
import random
from mathutils import Vector

# ------ Render Settings ------ #

FPS = 30
DURATION = 15
FRAME_END = FPS * DURATION

RES_X = 1280
RES_Y = 720

OUTPUT = os.path.abspath("cinematic_physics.mp4")
BG_PATH = os.path.abspath("1789740957857.png")

random.seed(42)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.engine = "BLENDER_EEVEE_NEXT"

scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.resolution_percentage = 100
scene.render.fps = FPS

scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.ffmpeg.fps = FPS
scene.render.filepath = OUTPUT

scene.render.film_transparent = False

# ------ Clear Scene ------ #

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

for datablocks in (
    bpy.data.meshes,
    bpy.data.curves,
    bpy.data.materials,
    bpy.data.cameras,
    bpy.data.lights,
):
    pass

# ------ Color Management ------ #

scene.view_settings.look = "AgX - Medium High Contrast"

# ------ Materials ------ #

def material(
    name,
    color,
    metallic=0.0,
    roughness=0.35,
    emission=None,
    emission_strength=0.0,
):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True

    bsdf = mat.node_tree.nodes.get("Principled BSDF")

    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness

    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    return mat


RED = material("Ruby", (0.8, 0.025, 0.03), 0.15, 0.22)
BLUE = material("Chrome Blue", (0.03, 0.35, 0.95), 0.85, 0.14)
GOLD = material("Gold", (1.0, 0.45, 0.03), 0.75, 0.18)
PURPLE = material("Energy Purple", (0.35, 0.05, 0.9), 0.5, 0.2)
GLASS = material("Glass", (0.8, 0.95, 1.0), 0.0, 0.08)
PLATFORM = material("Platform", (0.12, 0.15, 0.22), 0.35, 0.28)
GROUND = material("Ground", (0.07, 0.09, 0.12), 0.15, 0.5)

# ------ Object Helpers ------ #

def cube(name, location, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(
        location=location
    )

    obj = bpy.context.object
    obj.name = name
    obj.scale = (
        scale[0] / 2,
        scale[1] / 2,
        scale[2] / 2,
    )

    bpy.ops.object.transform_apply(
        location=False,
        rotation=False,
        scale=True,
    )

    if bevel > 0:
        mod = obj.modifiers.new("Edge Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3

    obj.data.materials.append(mat)
    return obj


def sphere(name, location, radius, mat):
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=4,
        radius=radius,
        location=location,
    )

    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)

    bpy.ops.object.shade_smooth()
    return obj


# ------ Ground and Platforms ------ #

ground = cube(
    "Ground",
    (0, -1.05, 2.8),
    (14, 0.5, 14),
    GROUND,
    0.08,
)

platform_data = [
    ((0.0, 0.8, 2.8), (3.5, 0.35, 2.0)),
    ((-2.2, 0.2, 3.0), (1.8, 0.35, 1.5)),
    ((1.5, 0.0, 2.5), (1.6, 0.35, 1.5)),
    ((0.0, -0.2, 5.0), (4.0, 0.35, 2.5)),
]

for i, (location, scale) in enumerate(platform_data):
    cube(
        f"Platform_{i}",
        location,
        scale,
        PLATFORM,
        0.12,
    )

# ------ Dynamic Objects ------ #

objects = [
    (RED, (0.0, 2.5, 2.8), 0.5, (0.25, 0.0, 0.0)),
    (BLUE, (-1.2, 3.0, 3.0), 0.4, (-0.1, 0.0, 0.2)),
    (GLASS, (1.0, 3.5, 2.5), 0.35, (0.0, 0.0, -0.15)),
    (GOLD, (0.5, 3.2, 3.5), 0.3, (0.15, 0.0, 0.0)),
    (PURPLE, (-0.6, 4.0, 4.3), 0.22, (0.3, 0.0, -0.1)),
]

dynamic_objects = []

for i, (mat, pos, radius, velocity) in enumerate(objects):
    obj = sphere(
        f"DynamicSphere_{i}",
        pos,
        radius,
        mat,
    )

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.rigidbody.object_add()
    rb = obj.rigid_body

    rb.type = "ACTIVE"
    rb.mass = max(0.1, radius * 3)
    rb.restitution = 0.72
    rb.friction = 0.45
    rb.linear_damping = 0.05
    rb.angular_damping = 0.12

    rb.kinematic = False
    obj["initial_velocity"] = velocity

    dynamic_objects.append(obj)
    obj.select_set(False)

# ------ Rigid Body World ------ #

if scene.rigidbody_world:
    world = scene.rigidbody_world
else:
    bpy.ops.rigidbody.world_add()
    world = scene.rigidbody_world

world.point_cache.frame_start = 1
world.point_cache.frame_end = FRAME_END
world.substeps_per_frame = 4
world.solver_iterations = 15

world.effector_weights.gravity = 0.35

# ------ Static Collision Objects ------ #

for obj in [ground] + [
    o for o in bpy.context.scene.objects
    if o.name.startswith("Platform_")
]:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    bpy.ops.rigidbody.object_add()
    obj.rigid_body.type = "PASSIVE"
    obj.rigid_body.friction = 0.5
    obj.rigid_body.restitution = 0.72

    obj.select_set(False)

# ------ Initial Velocities ------ #

for obj, (_, _, _, velocity) in zip(dynamic_objects, objects):
    obj.rigid_body.linear_velocity = velocity

# ------ World Background ------ #

world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True

nodes = world.node_tree.nodes
links = world.node_tree.links
nodes.clear()

output = nodes.new("ShaderNodeOutputWorld")
background = nodes.new("ShaderNodeBackground")
background.inputs["Strength"].default_value = 0.35

if os.path.exists(BG_PATH):
    environment = nodes.new("ShaderNodeTexEnvironment")
    environment.image = bpy.data.images.load(BG_PATH, check_existing=True)

    links.new(environment.outputs["Color"], background.inputs["Color"])

links.new(background.outputs["Background"], output.inputs["Surface"])

# ------ Lighting ------ #

def area_light(name, location, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color

    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location

    return obj


key = area_light(
    "Key Light",
    (3.5, 6.5, -1.5),
    1200,
    5.0,
    (1.0, 0.75, 0.55),
)

fill = area_light(
    "Blue Fill",
    (-4.0, 3.0, 1.0),
    850,
    4.0,
    (0.25, 0.45, 1.0),
)

rim = area_light(
    "Rim Light",
    (0.0, 5.0, 6.0),
    1100,
    3.0,
    (1.0, 0.25, 0.08),
)


def point_at(obj, target):
    obj.rotation_euler = (
        Vector(target) - obj.location
    ).to_track_quat("-Z", "Y").to_euler()


point_at(key, (0, 0, 3))
point_at(fill, (0, 1, 3))
point_at(rim, (0, 1, 3))

# ------ Camera ------ #

cam_data = bpy.data.cameras.new("Cinematic Camera")
camera = bpy.data.objects.new("Cinematic Camera", cam_data)
scene.collection.objects.link(camera)
scene.camera = camera

cam_data.lens = 42
cam_data.sensor_width = 36

def animate_camera():
    for frame in range(1, FRAME_END + 1):
        t = (frame - 1) / FPS

        angle = t * 0.20 + math.sin(t * 0.31) * 0.12
        radius = 5.0 + math.sin(t * 0.24) * 0.3

        camera.location = (
            math.sin(angle) * radius,
            1.5 + math.sin(t * 0.45) * 0.2,
            math.cos(angle) * radius + 1.2,
        )

        target = (
            math.sin(t * 0.28) * 0.15,
            1.1 + math.sin(t * 0.35) * 0.15,
            3.0,
        )

        point_at(camera, target)
        camera.keyframe_insert("location", frame=frame)
        camera.keyframe_insert("rotation_euler", frame=frame)

    if camera.animation_data and camera.animation_data.action:
        for fc in camera.animation_data.action.fcurves:
            for keyframe in fc.keyframe_points:
                keyframe.interpolation = "BEZIER"


animate_camera()

# ------ Camera Depth of Field ------ #

cam_data.dof.use_dof = True
cam_data.dof.focus_object = dynamic_objects[0]
cam_data.dof.aperture_fstop = 4.0

# ------ Compositor ------ #

scene.use_nodes = True

tree = scene.node_tree
tree.nodes.clear()

render_layers = tree.nodes.new("CompositorNodeRLayers")
glare = tree.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"
glare.threshold = 1.2
glare.size = 7

composite = tree.nodes.new("CompositorNodeComposite")

tree.links.new(
    render_layers.outputs["Image"],
    glare.inputs["Image"],
)

tree.links.new(
    glare.outputs["Image"],
    composite.inputs["Image"],
)

# ------ Render Quality ------ #

scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.ffmpeg.audio_codec = "NONE"

# Eevee is used for faster animation rendering.
# For a slower, more physically intensive render:
# scene.render.engine = "CYCLES"
# scene.cycles.samples = 64

# ------ Bake Physics ------ #

scene.frame_set(1)

if scene.rigidbody_world:
    bpy.context.scene.rigidbody_world.point_cache.frame_start = 1
    bpy.context.scene.rigidbody_world.point_cache.frame_end = FRAME_END

# ------ Export ------ #

scene.render.filepath = OUTPUT

bpy.ops.wm.save_as_mainfile(
    filepath=os.path.abspath("cinematic_physics.blend")
)

bpy.ops.render.render(animation=True)

print("Render Complete:", OUTPUT)
  
