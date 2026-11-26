"""IA POR DENTRO · EP03 · abertura — cena física + tokenização em Blender/Cycles.

Uso (Python 3.13 com o pacote `bpy` 5.x):
  python3 blender/cena.py --start 0 --end 335 --samples 48 --out out/frames
  python3 blender/cena.py --frames 0,120,240 --samples 16 --scale 50 --out out/teste

Tudo é procedural (materiais, iluminação, modelos), sem assets externos.
O texto da tela e os fragmentos usam as fontes do projeto (blender/fonts, OFL).
Os tempos vêm de data/timeline.json, data/typing.json e data/tokens.json — os mesmos
arquivos usados pelo Remotion para legendas e som, então imagem e voz não se desencontram.

Camadas de significado (fidelidade científica):
  tela (texto)  →  fragmentos (tokens, caixas com borda ciano)  →  IDs (números do vocabulário o200k_base)
A cena NÃO representa embeddings nem o "interior físico" do computador; a passagem pela
estrutura de subpixels é uma metáfora visual de aproximação, sinalizada como ilustração no rótulo.
"""
import argparse, json, math, os, sys
import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "data/timeline.json")))
TY = json.load(open(os.path.join(ROOT, "data/typing.json")))
TOK = json.load(open(os.path.join(ROOT, "data/tokens.json")))
FPS = TL["fps"]
NFRAMES = round(TL["durationSec"] * FPS)
FONT_TEXT = os.path.join(ROOT, "blender/fonts/Figtree-Medium.ttf")
FONT_ID = os.path.join(ROOT, "blender/fonts/JetBrainsMono-Medium.ttf")

# ---------------------------------------------------------------------------
# Tempos-chave (s) — derivados da narração
# ---------------------------------------------------------------------------
V = TL["voice"]
T_RACK0, T_RACK1 = 1.2, 2.7          # rack focus: teclado → tela
T_RISE0, T_RISE1 = 0.0, 5.9          # grua/dolly do teclado até o enquadramento da tela
T_HOLD1 = 7.08                       # quadro segurado na pausa de "nem letras"
T_PUSH0, T_PUSH1 = 7.08, 8.15        # "Eles leem tokens": aproximação macro
T_SCREEN_OFF0, T_SCREEN_OFF1 = 7.62, 8.05
T_TOK0, T_TOK_STAG = V["tokensWord"], 0.085
T_GAP0, T_GAP1 = 7.92, 8.55
T_ID0, T_ID_STAG = 8.42, 0.075       # IDs entram na pausa antes de "Mas"
T_SETTLE1 = 10.6                     # câmera desacelera até parar antes do fim da pergunta

def smooth(x):  # smootherstep
    x = min(1.0, max(0.0, x)); return x * x * x * (x * (6 * x - 15) + 10)

def ease_out(x):
    x = min(1.0, max(0.0, x)); return 1 - (1 - x) ** 3

def ramp(t, a, b, f=smooth):
    return f((t - a) / (b - a)) if b > a else float(t >= a)

def lerp(a, b, k):
    return a + (b - a) * k

def lerpv(a, b, k):
    return Vector(a).lerp(Vector(b), k)

# ---------------------------------------------------------------------------
# Métricas da fonte (fontTools) — posições exatas, sem depender do layout do Blender
# ---------------------------------------------------------------------------
from fontTools.ttLib import TTFont
_ft = TTFont(FONT_TEXT); _cmap = _ft.getBestCmap(); _upm = _ft["head"].unitsPerEm
def adv(s):
    return sum(_ft["hmtx"][_cmap[ord(c)]][0] for c in s) / _upm  # em

E = 0.012                 # corpo do texto na tela (m por em)
PITCH = 2.15 * E          # entrelinha no modo fragmentos (linha + ID)
LINES = ["paciente em", "ventilação", "mecânica"]
LINE_START = [0, 12, 23]
WRAP = [11, 22]
TEXT = TOK["text"]
assert " ".join(LINES) == TEXT
SPACE = adv(" ") * E
GAP = 0.20 * E
PAD = 0.07 * E
EDITOR_PITCH = 1.32 * E   # entrelinha do campo de texto (antes da tokenização)

# runs: (token, linha, texto visível, índice inicial, x no editor, largura, ordem na linha, espaço pendurado)
RUNS = []
pos = 0
for k, p in enumerate(TOK["pieces"]):
    t0, t1 = pos, pos + len(p["text"]); pos = t1
    for li in range(3):
        ls, le = LINE_START[li], LINE_START[li] + len(LINES[li])
        a, b = max(t0, ls), min(t1, le)
        if a >= b: continue
        hanging = t0 in WRAP and a == ls and t0 == ls - 1
        txt = TEXT[a:b]
        RUNS.append(dict(token=k, line=li, text=txt, start=a, x=adv(LINES[li][: a - ls]) * E,
                         w=adv(txt) * E, hanging=hanging, idx=0, id=p["id"]))
for li in range(3):
    for i, r in enumerate([r for r in RUNS if r["line"] == li]): r["idx"] = i
rebuilt = [""] * len(TEXT)
for r in RUNS:
    for i, c in enumerate(r["text"]): rebuilt[r["start"] + i] = c
for i in WRAP: rebuilt[i] = " "
assert "".join(rebuilt) == TEXT, "runs não reconstroem a frase"

# extensão horizontal do bloco tokenizado (para centralizar)
BLOCK_L = min(r["x"] + r["idx"] * GAP - PAD - (SPACE if r["hanging"] else 0) for r in RUNS)
BLOCK_R = max(r["x"] + r["idx"] * GAP + r["w"] + PAD for r in RUNS)

# ---------------------------------------------------------------------------
# Geometria do set (metros; mesa em z=0; tela no plano y=0, olhando para −y)
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 0.60, 0.34
SCREEN_C = Vector((0.0, 0.0, 0.43))
# origem do bloco de texto na tela: linha de base da 1ª linha, margem esquerda
TEXT_ORIGIN = Vector((-0.055, -0.0004, 0.468))

def content_to_world(x, y, z=0.0):
    """coordenadas locais do conteúdo (x direita, y cima, z para a câmera) → mundo"""
    return TEXT_ORIGIN + Vector((x, -z, y))

# ---------------------------------------------------------------------------
# Utilidades de cena
# ---------------------------------------------------------------------------
def new_obj(name, data, coll=None, parent=None):
    o = bpy.data.objects.new(name, data)
    (coll or bpy.context.scene.collection).objects.link(o)
    if parent: o.parent = parent
    return o

def rounded_box(name, sx, sy, sz, bevel, segments=6, mats=(), parent=None, bevel_mat_index=None):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    o = new_obj(name, me, parent=parent)
    o.scale = (sx, sy, sz)
    for m in mats: me.materials.append(m)
    mod = o.modifiers.new("bevel", "BEVEL")
    mod.width = bevel; mod.segments = segments; mod.limit_method = "NONE"
    mod.harden_normals = False
    if bevel_mat_index is not None: mod.material = bevel_mat_index
    # escala aplicada na malha para o bevel ficar uniforme
    me.transform(__import__("mathutils").Matrix.Diagonal((sx, sy, sz, 1.0))); o.scale = (1, 1, 1)
    for p in me.polygons: p.use_smooth = True
    return o

def text_obj(name, body, font, size, extrude=0.0, bevel=0.0, mat=None, parent=None):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body; cu.font = font; cu.size = size
    cu.extrude = extrude; cu.bevel_depth = bevel; cu.bevel_resolution = 2
    cu.align_x = "LEFT"; cu.align_y = "BOTTOM_BASELINE" if hasattr(cu, "align_y") else cu.align_y
    cu.resolution_u = 6
    o = new_obj(name, cu, parent=parent)
    if mat: cu.materials.append(mat)
    return o

def nodes(mat):
    mat.use_nodes = True; nt = mat.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    return nt

def kelvin(K):
    # aproximação de Tanner Helland para cor de corpo negro (sRGB → linear)
    t = K / 100.0
    r = 255 if t <= 66 else 329.698727446 * ((t - 60) ** -0.1332047592)
    g = 99.4708025861 * math.log(t) - 161.1195681661 if t <= 66 else 288.1221695283 * ((t - 60) ** -0.0755148492)
    b = 255 if t >= 66 else (0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307)
    lin = lambda c: ((min(255, max(0, c)) / 255) ** 2.2)
    return (lin(r), lin(g), lin(b))

# ---------------------------------------------------------------------------
# Materiais
# ---------------------------------------------------------------------------
def mat_principled(name, base, rough, metal=0.0, coat=0.0, coat_rough=0.05, spec=0.5, bump_scale=0.0, bump_strength=0.0, noise_var=0.0):
    m = bpy.data.materials.new(name); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (*base, 1)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    bs.inputs["Coat Weight"].default_value = coat
    bs.inputs["Coat Roughness"].default_value = coat_rough
    bs.inputs["Specular IOR Level"].default_value = spec
    if bump_scale > 0 or noise_var > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = bump_scale or 200
        nz.inputs["Detail"].default_value = 8
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        if bump_strength > 0:
            bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = bump_strength
            bp.inputs["Distance"].default_value = 0.0004
            nt.links.new(nz.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], bs.inputs["Normal"])
        if noise_var > 0:
            mr = nt.nodes.new("ShaderNodeMapRange")
            mr.inputs["To Min"].default_value = rough * (1 - noise_var); mr.inputs["To Max"].default_value = rough * (1 + noise_var)
            nt.links.new(nz.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], bs.inputs["Roughness"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_wood():
    m = bpy.data.materials.new("mesa_madeira"); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 14.0, 1.0)
    wave = nt.nodes.new("ShaderNodeTexWave"); wave.wave_type = "BANDS"; wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 9.0; wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 6.0; wave.inputs["Detail Roughness"].default_value = 0.65
    ramp_ = nt.nodes.new("ShaderNodeValToRGB")
    ramp_.color_ramp.elements[0].color = (0.020, 0.014, 0.010, 1)
    ramp_.color_ramp.elements[1].color = (0.055, 0.038, 0.026, 1)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 900; nz.inputs["Detail"].default_value = 4
    rr = nt.nodes.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.28; rr.inputs["To Max"].default_value = 0.52
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.08; bp.inputs["Distance"].default_value = 0.0003
    L = nt.links
    L.new(tc.outputs["Object"], mp.inputs["Vector"]); L.new(mp.outputs["Vector"], wave.inputs["Vector"])
    L.new(wave.outputs["Fac"], ramp_.inputs["Fac"]); L.new(ramp_.outputs["Color"], bs.inputs["Base Color"])
    L.new(tc.outputs["Object"], nz.inputs["Vector"]); L.new(nz.outputs["Fac"], rr.inputs["Value"])
    L.new(rr.outputs["Result"], bs.inputs["Roughness"]); L.new(wave.outputs["Fac"], bp.inputs["Height"])
    L.new(bp.outputs["Normal"], bs.inputs["Normal"])
    bs.inputs["Coat Weight"].default_value = 0.35; bs.inputs["Coat Roughness"].default_value = 0.18
    L.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_emit(name, color, strength):
    m = bpy.data.materials.new(name); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1); em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m

def subpixel_mask(nt, screen_obj, pitch):
    """Máscara RGB de subpixels (listras verticais R|G|B + fenda entre linhas),
    em coordenadas do objeto-tela (metros). Retorna o socket de cor (média ≈ 1)."""
    tc = nt.nodes.new("ShaderNodeTexCoord"); tc.object = screen_obj
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    def mathn(op, a, b=None, val=None):
        n = nt.nodes.new("ShaderNodeMath"); n.operation = op
        if isinstance(a, float): n.inputs[0].default_value = a
        else: nt.links.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, float): n.inputs[1].default_value = b
            else: nt.links.new(b, n.inputs[1])
        return n.outputs[0]
    fx = mathn("FRACT", mathn("DIVIDE", sep.outputs["X"], pitch))
    fz = mathn("FRACT", mathn("DIVIDE", sep.outputs["Z"], pitch))
    # bordas suaves para cada listra (evita serrilhado quando visto de longe)
    def band(lo, hi):
        a = mathn("SMOOTH_MIN", mathn("SUBTRACT", fx, lo), mathn("SUBTRACT", hi, fx))
        n = nt.nodes.new("ShaderNodeMath"); n.operation = "SMOOTH_MIN"
        return mathn("GREATER_THAN", mathn("MINIMUM", mathn("SUBTRACT", fx, lo), mathn("SUBTRACT", hi, fx)), 0.04)
    r = band(0.0, 1 / 3); g = band(1 / 3, 2 / 3); b = band(2 / 3, 1.0)
    row = mathn("GREATER_THAN", mathn("MINIMUM", fz, mathn("SUBTRACT", 1.0, fz)), 0.07)
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mathn("MULTIPLY", r, row), comb.inputs[0])
    nt.links.new(mathn("MULTIPLY", g, row), comb.inputs[1])
    nt.links.new(mathn("MULTIPLY", b, row), comb.inputs[2])
    scale = nt.nodes.new("ShaderNodeVectorMath"); scale.operation = "SCALE"
    scale.inputs["Scale"].default_value = 3.6  # compensa a área apagada (média ≈ 1)
    nt.links.new(comb.outputs[0], scale.inputs[0])
    return scale.outputs[0]

def mat_screen_emit(name, color, strength, screen_obj, pitch, glossy=False):
    """Emissão de tela com máscara de subpixels controlada por 'pattern' (0 = cor lisa, 1 = subpixels)."""
    m = bpy.data.materials.new(name); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mask = subpixel_mask(nt, screen_obj, pitch)
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.label = "pattern"
    mix.inputs["Factor"].default_value = 0.0
    mix.inputs["A"].default_value = (1, 1, 1, 1)
    nt.links.new(mask, mix.inputs["B"])
    tint = nt.nodes.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0; tint.inputs["A"].default_value = (*color, 1)
    nt.links.new(mix.outputs["Result"], tint.inputs["B"])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1)
    bs.inputs["Roughness"].default_value = 0.16 if glossy else 0.5
    bs.inputs["Specular IOR Level"].default_value = 0.5 if glossy else 0.15
    bs.inputs["Emission Strength"].default_value = strength
    nt.links.new(tint.outputs["Result"], bs.inputs["Emission Color"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    m["pattern_node"] = mix.name
    return m

def mat_letter(name, screen_obj, pitch):
    """Letra: começa como pixels acesos na tela; termina como objeto físico (cetim claro)."""
    m = bpy.data.materials.new(name); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mask = subpixel_mask(nt, screen_obj, pitch)
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.name = "pattern"
    mix.inputs["Factor"].default_value = 0.0; mix.inputs["A"].default_value = (1, 1, 1, 1)
    nt.links.new(mask, mix.inputs["B"])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.name = "bsdf"
    bs.inputs["Base Color"].default_value = (0.80, 0.82, 0.84, 1)
    bs.inputs["Roughness"].default_value = 0.45
    bs.inputs["Coat Weight"].default_value = 0.4; bs.inputs["Coat Roughness"].default_value = 0.12
    tint = nt.nodes.new("ShaderNodeMix"); tint.data_type = "RGBA"; tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0; tint.inputs["A"].default_value = (0.86, 0.89, 0.92, 1)
    nt.links.new(mix.outputs["Result"], tint.inputs["B"]); nt.links.new(tint.outputs["Result"], bs.inputs["Emission Color"])
    bs.inputs["Emission Strength"].default_value = 1.0
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_tile(name):
    m = bpy.data.materials.new(name); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.name = "bsdf"
    bs.inputs["Base Color"].default_value = (0.004, 0.0052, 0.0068, 1)
    bs.inputs["Roughness"].default_value = 0.55
    bs.inputs["Coat Weight"].default_value = 0.8; bs.inputs["Coat Roughness"].default_value = 0.04
    bs.inputs["Alpha"].default_value = 0.0
    # leve translucidez fosca (vidro fumê) na face frontal
    bs.inputs["Transmission Weight"].default_value = 0.0
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    m.blend_method = "HASHED" if hasattr(m, "blend_method") else None
    return m

CYAN = (0.04, 0.62, 0.78)   # ciano linear (≈ #3DD3E6 em sRGB)
BLUE = (0.10, 0.22, 0.62)

def mat_rim(name):
    m = bpy.data.materials.new(name); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.name = "bsdf"
    bs.inputs["Base Color"].default_value = (0.004, 0.012, 0.016, 1)
    bs.inputs["Roughness"].default_value = 0.3
    bs.inputs["Emission Color"].default_value = (*CYAN, 1)
    bs.inputs["Emission Strength"].default_value = 0.0
    bs.inputs["Alpha"].default_value = 0.0
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def mat_id(name):
    m = bpy.data.materials.new(name); nt = nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled"); bs.name = "bsdf"
    bs.inputs["Base Color"].default_value = (0.6, 0.85, 0.92, 1)
    bs.inputs["Roughness"].default_value = 0.3
    bs.inputs["Emission Color"].default_value = (0.55, 0.88, 0.96, 1)
    bs.inputs["Emission Strength"].default_value = 0.0
    bs.inputs["Alpha"].default_value = 0.0
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m

def key(obj_or_socket, path, value, frame):
    setattr(obj_or_socket, path, value) if not hasattr(obj_or_socket, "default_value") or path != "default_value" else None
    if hasattr(obj_or_socket, "default_value") and path == "default_value":
        obj_or_socket.default_value = value
    obj_or_socket.keyframe_insert(path, frame=frame)

# ---------------------------------------------------------------------------
# Construção
# ---------------------------------------------------------------------------
def build(args):
    sc = bpy.context.scene
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"; cy.samples = args.samples; cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02; cy.use_denoising = True
    try: cy.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    cy.max_bounces = 6; cy.diffuse_bounces = 3; cy.glossy_bounces = 3
    cy.transmission_bounces = 4; cy.transparent_max_bounces = 8
    cy.sample_clamp_indirect = 4.0; cy.blur_glossy = 0.6
    cy.caustics_reflective = False; cy.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
    sc.render.resolution_percentage = args.scale
    sc.render.fps = FPS
    sc.render.film_transparent = False
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception: pass
    sc.view_settings.exposure = 0.0
    sc.frame_start, sc.frame_end = 0, NFRAMES - 1

    world = bpy.data.worlds.new("mundo"); sc.world = world; wn = nodes(world)
    bg = wn.nodes.new("ShaderNodeBackground"); bg.inputs["Color"].default_value = (0.0015, 0.0018, 0.0026, 1)
    bg.inputs["Strength"].default_value = 1.0
    wo = wn.nodes.new("ShaderNodeOutputWorld"); wn.links.new(bg.outputs[0], wo.inputs[0])

    font_t = bpy.data.fonts.load(FONT_TEXT); font_i = bpy.data.fonts.load(FONT_ID)

    # --- mesa, parede, luzes práticas ao fundo (bokeh do corredor) ---
    me = bpy.data.meshes.new("mesa"); me.from_pydata([(-2, -1.5, 0), (2, -1.5, 0), (2, 1.0, 0), (-2, 1.0, 0)], [], [(0, 1, 2, 3)])
    desk = new_obj("mesa", me); desk.data.materials.append(mat_wood())
    wall_m = mat_principled("parede", (0.010, 0.011, 0.013), 0.8)
    mw = bpy.data.meshes.new("parede"); mw.from_pydata([(-6, 3.2, -1), (6, 3.2, -1), (6, 3.2, 4), (-6, 3.2, 4)], [], [(0, 1, 2, 3)])
    new_obj("parede", mw).data.materials.append(wall_m)
    import random; rnd = random.Random(7)
    for i in range(14):
        warm = i % 4 != 0
        col = kelvin(2900 if warm else 6200)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rnd.uniform(0.025, 0.05), location=(rnd.uniform(-1.6, 1.8), rnd.uniform(1.6, 3.0), rnd.uniform(0.7, 2.2)))
        s = bpy.context.active_object; s.name = f"bokeh_{i}"
        s.data.materials.append(mat_emit(f"bokeh_{i}", col, rnd.uniform(6, 22) * (1.0 if warm else 0.6)))
    # faixa de luz de corredor ao fundo (porta entreaberta)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-1.1, 3.15, 1.0), rotation=(math.pi / 2, 0, 0))
    door = bpy.context.active_object; door.scale = (0.06, 1.9, 1); door.name = "porta_luz"
    door.data.materials.append(mat_emit("porta_luz", kelvin(4300), 3.0))

    # --- monitor ---
    screen_mesh = bpy.data.meshes.new("tela"); hw, hh = SCREEN_W / 2, SCREEN_H / 2
    screen_mesh.from_pydata([(-hw, 0, -hh), (hw, 0, -hh), (hw, 0, hh), (-hw, 0, hh)], [], [(0, 1, 2, 3)])
    screen = new_obj("tela", screen_mesh); screen.location = SCREEN_C
    pitch = 0.0010  # passo de pixel exagerado (ilustração) para a estrutura aparecer no macro
    screen_mat = mat_screen_emit("tela_fundo", (0.020, 0.023, 0.028), 1.0, screen, pitch, glossy=True)
    screen.data.materials.append(screen_mat)
    bez_m = mat_principled("moldura", (0.006, 0.006, 0.007), 0.28, coat=0.3)
    body_m = mat_principled("carcaca", (0.03, 0.031, 0.034), 0.45, metal=0.6, noise_var=0.2, bump_scale=600, bump_strength=0.05)
    # moldura: caixa arredondada atrás do plano da tela, maior 9 mm de cada lado
    bez = rounded_box("moldura", SCREEN_W + 0.018, 0.022, SCREEN_H + 0.018, 0.004, 4, [bez_m])
    bez.location = SCREEN_C + Vector((0, 0.0112, 0))
    back = rounded_box("carcaca", SCREEN_W - 0.02, 0.03, SCREEN_H - 0.04, 0.012, 6, [body_m])
    back.location = SCREEN_C + Vector((0, 0.035, -0.01))
    neck = rounded_box("haste", 0.05, 0.02, 0.26, 0.006, 4, [body_m]); neck.location = (0, 0.07, 0.15)
    base = rounded_box("base", 0.24, 0.17, 0.008, 0.004, 4, [body_m]); base.location = (0, 0.05, 0.004)

    # luz emitida pelo monitor sobre o teclado e a mesa (área invisível à câmera)
    ld = bpy.data.lights.new("luz_monitor", "AREA"); ld.shape = "RECTANGLE"; ld.size = SCREEN_W; ld.size_y = SCREEN_H
    ld.color = kelvin(7200); ld.energy = 6.0
    lmon = new_obj("luz_monitor", ld); lmon.location = SCREEN_C + Vector((0, -0.003, 0)); lmon.rotation_euler = (-math.pi / 2, 0, 0)
    lmon.visible_camera = False
    # prática quente do plantão (luminária alta à esquerda)
    lw = bpy.data.lights.new("pratica", "AREA"); lw.size = 0.5; lw.color = kelvin(3100); lw.energy = 9.0
    lp = new_obj("pratica", lw); lp.location = (-0.9, -0.4, 1.3); lp.rotation_euler = (math.radians(50), 0, math.radians(-60))
    lp.visible_camera = False

    # --- teclado ---
    kb_m = mat_principled("teclado_aluminio", (0.075, 0.078, 0.085), 0.38, metal=1.0, noise_var=0.25, bump_scale=1800, bump_strength=0.04)
    cap_m = mat_principled("tecla_pbt", (0.018, 0.019, 0.021), 0.62, bump_scale=2500, bump_strength=0.12, noise_var=0.1)
    kb_y = -0.255
    kb = rounded_box("teclado", 0.29, 0.112, 0.010, 0.004, 4, [kb_m]); kb.location = (0.0, kb_y, 0.005)
    rows = ["1234567890-=", "qwertyuiop´[", "asdfghjklç~]", "zxcvbnm,.;/", " "]
    KP = 0.0185; keys = {}
    for ri, row in enumerate(rows):
        y = kb_y + 0.038 - ri * KP
        if row == " ":
            k = rounded_box("tecla_espaco", KP * 6 - 0.0025, KP - 0.0025, 0.0065, 0.0016, 3, [cap_m])
            k.location = (0.005, y, 0.0135); keys[" "] = k; continue
        x0 = -0.118 + ri * 0.006
        for ci, ch in enumerate(row):
            k = rounded_box(f"tecla_{ri}_{ci}", KP - 0.0025, KP - 0.0025, 0.0065, 0.0016, 3, [cap_m])
            k.location = (x0 + ci * KP, y, 0.0135); keys[ch] = k
    keys["^"] = keys["~"]; keys["â"] = keys["a"]; keys["ã"] = keys["a"]

    # estetoscópio sobre a mesa (curva com bevel) + caneca
    tube_m = mat_principled("borracha", (0.012, 0.013, 0.015), 0.55, coat=0.2)
    steel_m = mat_principled("aco", (0.62, 0.63, 0.65), 0.18, metal=1.0)
    cd = bpy.data.curves.new("estetoscopio", "CURVE"); cd.dimensions = "3D"; cd.bevel_depth = 0.0042; cd.bevel_resolution = 4
    sp = cd.splines.new("BEZIER"); pts = [(0.22, -0.34, 0.004), (0.27, -0.24, 0.004), (0.20, -0.14, 0.004), (0.29, -0.08, 0.004), (0.34, -0.19, 0.004)]
    sp.bezier_points.add(len(pts) - 1)
    for bp_, p in zip(sp.bezier_points, pts):
        bp_.co = p; bp_.handle_left_type = bp_.handle_right_type = "AUTO"
    st = new_obj("estetoscopio", cd); cd.materials.append(tube_m)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.021, depth=0.009, location=(0.225, -0.365, 0.0045)); bpy.context.active_object.data.materials.append(steel_m)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(radius=0.040, depth=0.10, location=(-0.30, -0.08, 0.05), vertices=64)
    mug = bpy.context.active_object; mug.name = "caneca"; mug.data.materials.append(mat_principled("ceramica", (0.06, 0.065, 0.07), 0.22, coat=0.6))
    bpy.ops.object.shade_smooth()

    # --- conteúdo da tela: UI genérica, texto, cursor ---
    content = new_obj("conteudo", None); content.location = TEXT_ORIGIN; content.rotation_euler = (math.pi / 2, 0, 0)
    ui_m = mat_screen_emit("ui_campo", (0.040, 0.045, 0.052), 1.0, screen, pitch)
    ui_bar = mat_screen_emit("ui_esqueleto", (0.085, 0.092, 0.10), 1.0, screen, pitch)
    field_w = adv("paciente em") * E + 0.024
    def flat_rect(name, x0, y0, w, h, r, mat):
        import bmesh
        mme = bpy.data.meshes.new(name)
        mme.from_pydata([(x0, y0, 0), (x0 + w, y0, 0), (x0 + w, y0 + h, 0), (x0, y0 + h, 0)], [], [(0, 1, 2, 3)])
        o = new_obj(name, mme, parent=content); mme.materials.append(mat)
        b = o.modifiers.new("canto", "BEVEL"); b.affect = "VERTICES"; b.width = r; b.segments = 8
        return o
    field = flat_rect("campo", -0.014, -2 * EDITOR_PITCH - 0.020, field_w + 0.010, 2 * EDITOR_PITCH + 0.040, 0.008, ui_m)
    field.location.z = 0.00005
    bars = []
    for i, (w, yy) in enumerate([(0.12, 0.060), (0.085, 0.048), (0.10, 0.036)]):
        b = flat_rect(f"esqueleto_{i}", -0.014, yy, w, 0.0035, 0.0017, ui_bar); b.location.z = 0.00005; bars.append(b)
    letter_mats, runs_objs = [], []
    for r in RUNS:
        lm = mat_letter(f"letra_{r['token']}_{r['line']}", screen, pitch); letter_mats.append(lm)
        o = text_obj(f"run_{r['token']}_{r['line']}", r["text"], font_t, 1.0, mat=lm, parent=content)
        runs_objs.append(o)
    caret_m = mat_screen_emit("cursor", (0.86, 0.89, 0.92), 1.0, screen, pitch)
    caret = rounded_box("cursor", 0.0007, 0.0118, 0.0001, 0.00005, 1, [caret_m], parent=content)

    # escala da fonte: calibra o tamanho do Blender para 1 em = E
    calib = text_obj("calib", "H", font_t, 1.0); bpy.context.view_layer.update()
    gH = _ft["glyf"][_cmap[ord("H")]]; ink_em = (gH.xMax - gH.xMin) / _upm
    size = E / (calib.dimensions.x / ink_em); bpy.data.objects.remove(calib)
    for o in runs_objs: o.data.size = size

    # --- fragmentos: placas, bordas, marcas de espaço, IDs ---
    tiles, rims, marks, ids, links = [], [], [], [], []
    yMax = max(_ft["glyf"][_cmap[ord(c)]].yMax for c in TEXT if c != " ") / _upm
    yMin = min(_ft["glyf"][_cmap[ord(c)]].yMin for c in TEXT if c != " ") / _upm
    TILE_TOP, TILE_BOT, DEPTH = (yMax + 0.13) * E, (yMin - 0.13) * E, 0.28 * E
    tile_mats, rim_mats, id_mats = [], [], []
    for r in RUNS:
        w = r["w"] + 2 * PAD + (SPACE if r["hanging"] else 0)
        tm = mat_tile(f"placa_{r['token']}"); rm = mat_rim(f"borda_{r['token']}")
        t = rounded_box(f"placa_{r['token']}", w, TILE_TOP - TILE_BOT, DEPTH, 0.032 * E, 3, [tm, rm], parent=content, bevel_mat_index=1)
        tiles.append(t); tile_mats.append(tm); rim_mats.append(rm)
        idm = mat_id(f"id_{r['token']}"); id_mats.append(idm)
        io = text_obj(f"id_{r['token']}", str(r["id"]), font_i, size * 0.42, extrude=0.02 * E, mat=idm, parent=content)
        ids.append(io)
        # filete ciano placa → ID (consulta no vocabulário)
        ln = rounded_box(f"elo_{r['token']}", 0.012 * E, 1.0, 0.012 * E, 0.0, 1, [rm], parent=content); links.append(ln)
        if r["hanging"] or r["text"].startswith(" "):
            mk = rounded_box(f"espaco_{r['token']}", SPACE * 0.62, 0.018 * E, 0.03 * E, 0.0, 1, [rm], parent=content)
            marks.append((r, mk))
    bpy.context.view_layer.update()
    id_w = {i: ids[i].dimensions.x for i in range(len(ids))}

    # câmera
    cam_d = bpy.data.cameras.new("camera"); cam_d.lens = 35; cam_d.sensor_fit = "AUTO"; cam_d.sensor_width = 36
    cam_d.clip_start = 0.005; cam_d.dof.use_dof = True; cam_d.dof.aperture_blades = 9; cam_d.dof.aperture_rotation = 0.2
    cam = new_obj("camera", cam_d); sc.camera = cam
    target = new_obj("alvo", None)
    tr = cam.constraints.new("TRACK_TO"); tr.target = target; tr.track_axis = "TRACK_NEGATIVE_Z"; tr.up_axis = "UP_Y"

    # luzes da fase "dentro da tela"
    lk = bpy.data.lights.new("chave", "AREA"); lk.shape = "DISK"; lk.size = 0.08; lk.color = kelvin(5200); lk.energy = 0.0
    key_l = new_obj("chave", lk)
    lr = bpy.data.lights.new("recorte", "AREA"); lr.shape = "RECTANGLE"; lr.size = 0.12; lr.size_y = 0.02; lr.color = BLUE; lr.energy = 0.0
    rim_l = new_obj("recorte", lr)
    lf = bpy.data.lights.new("preenchimento", "AREA"); lf.size = 0.2; lf.color = kelvin(7000); lf.energy = 0.0
    fill_l = new_obj("preenchimento", lf)

    frag = bpy.data.collections.new("fragmentos")
    for o in [*runs_objs, *tiles, *ids, *links, *[m for _, m in marks]]: frag.objects.link(o)
    for L_ in (key_l, rim_l, fill_l): L_.light_linking.receiver_collection = frag
    fill_l.visible_glossy = False; rim_l.visible_diffuse = False

    return dict(sc=sc, cam=cam, target=target, content=content, screen=screen, screen_mat=screen_mat, ui=[ui_m, ui_bar], caret=caret,
                caret_m=caret_m, runs=runs_objs, letter_mats=letter_mats, tiles=tiles, tile_mats=tile_mats, rim_mats=rim_mats, ids=ids,
                id_mats=id_mats, id_w=id_w, links=links, marks=marks, keys=keys, lmon=lmon, lp=lp, key_l=key_l, rim_l=rim_l, fill_l=fill_l,
                size=size, TILE_TOP=TILE_TOP, TILE_BOT=TILE_BOT, DEPTH=DEPTH, field=field, bars=bars)

# ---------------------------------------------------------------------------
# Animação (calculada em Python e gravada como keyframes por quadro → motion blur correto)
# ---------------------------------------------------------------------------
def typed_count(frame):
    n = TY["pretyped"]
    for k in TY["keys"]:
        if k["kind"] != "dead" and math.ceil(k["t"] * FPS - 1e-6) <= frame: n += 1
    return n

def editor_xy(r):           # posição do run no campo de texto (antes da tokenização)
    return r["x"], -r["line"] * EDITOR_PITCH

def token_xy(r, gp):        # posição no arranjo de fragmentos (vãos abertos por gp)
    cx = (BLOCK_L + BLOCK_R) / 2
    x = r["x"] + r["idx"] * GAP * gp
    return x, -r["line"] * PITCH

# enquadramentos (posição da câmera, alvo, distância de foco, f-stop)
BLOCK_CX = (BLOCK_L + BLOCK_R) / 2
def cam_state(t):
    # alvo final: centro do bloco tokenizado com a linha dos IDs
    fin_target = content_to_world(BLOCK_CX, -1.0 * PITCH - 1.9 * E, 0.0)
    fin_dist = 0.186
    near_target = content_to_world(BLOCK_CX - 0.002, -1.0 * EDITOR_PITCH, 0.0)
    A_pos, A_tgt = Vector((0.07, -0.47, 0.11)), Vector((0.0, -0.16, 0.055))   # baixo, teclado em primeiro plano
    B_pos = near_target + Vector((0.052, -0.275, -0.034))                        # tela em ângulo leve
    B2_pos = near_target + Vector((0.052, -0.275, -0.034))                       # leve deriva na pausa
    C_pos = fin_target + Vector((0.0, -fin_dist, 0.0))                           # frontal, macro
    D_pos = fin_target + Vector((0.0, -fin_dist * 0.955, 0.0))                   # desaceleração final
    k1 = ramp(t, T_RISE0, T_RISE1)
    pos = lerpv(A_pos, B_pos, k1); tgt = lerpv(A_tgt, near_target, smooth(min(1, k1 * 1.15)))
    pos = lerpv(pos, B2_pos, ramp(t, T_RISE1, T_HOLD1, ease_out))
    kp = ramp(t, T_PUSH0, T_PUSH1)
    pos = lerpv(pos, C_pos, kp); tgt = lerpv(tgt, fin_target, kp)
    pos = lerpv(pos, D_pos, ramp(t, T_PUSH1, T_SETTLE1, ease_out))
    # foco
    d_kb = (Vector((0.0, -0.255, 0.02)) - pos).length
    d_txt = (tgt - pos).length
    rack = ramp(t, T_RACK0, T_RACK1)
    focus = lerp(d_kb, d_txt, rack)
    if t >= T_PUSH0: focus = d_txt - ramp(t, T_TOK0, T_TOK0 + 0.6) * 0.30 * E  # foco na face frontal das placas
    fstop = lerp(1.8, 2.8, rack); fstop = lerp(fstop, 5.6, ramp(t, T_PUSH0, T_PUSH1))
    return pos, tgt, focus, fstop

def animate(S):
    cam, tgt = S["cam"], S["target"]
    for f in range(NFRAMES):
        t = f / FPS
        pos, look, focus, fstop = cam_state(t)
        cam.location = pos; cam.keyframe_insert("location", frame=f)
        tgt.location = look; tgt.keyframe_insert("location", frame=f)
        cam.data.dof.focus_distance = focus; cam.data.dof.keyframe_insert("focus_distance", frame=f)
        cam.data.dof.aperture_fstop = fstop; cam.data.dof.keyframe_insert("aperture_fstop", frame=f)

        # padrão de subpixels: aparece só de perto, some quando a tela "apaga"
        dist = (look - pos).length
        # só mostra subpixels quando cada pixel da tela ocupa ≥ 9 pixels do vídeo (sem moiré)
        px_per_lcd = 1920 * 0.0010 / (1.028 * dist)
        pat = ramp(px_per_lcd, 9.0, 13.0) * (1 - ramp(t, T_SCREEN_OFF1 - 0.04, T_SCREEN_OFF1 + 0.20))
        screen_on = 1 - ramp(t, T_SCREEN_OFF0, T_SCREEN_OFF1)
        for m in [S["screen_mat"], *S["ui"], S["caret_m"]]:
            nt = m.node_tree
            mix = [n for n in nt.nodes if n.type == "MIX" and n.label == "pattern"][0]
            mix.inputs["Factor"].default_value = pat; mix.inputs["Factor"].keyframe_insert("default_value", frame=f)
            bs = [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"][0]
            base_strength = 1.0 if m is not S["caret_m"] else 1.0
            bs.inputs["Emission Strength"].default_value = base_strength * lerp(0.02, 1.0, screen_on)
            bs.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
        S["lmon"].data.energy = 6.0 * screen_on; S["lmon"].data.keyframe_insert("energy", frame=f)
        S["lp"].data.energy = 9.0 * lerp(0.25, 1.0, screen_on); S["lp"].data.keyframe_insert("energy", frame=f)

        # luzes de dentro: chave suave à esquerda-alto, recorte azul atrás-alto, preenchimento baixo
        inside = ramp(t, T_SCREEN_OFF0, T_PUSH1 + 0.2)
        c = content_to_world(BLOCK_CX, -PITCH, 0.0)
        S["key_l"].location = c + Vector((-0.17, -0.035, 0.07)); S["key_l"].rotation_euler = (math.radians(70), 0, math.radians(-75))
        S["key_l"].data.energy = 4.0 * inside; S["key_l"].data.keyframe_insert("energy", frame=f)
        S["rim_l"].location = c + Vector((0.05, 0.01, 0.10)); S["rim_l"].rotation_euler = (math.radians(-8), math.radians(25), 0)
        S["rim_l"].data.energy = 1.4 * inside; S["rim_l"].data.keyframe_insert("energy", frame=f)
        S["fill_l"].location = c + Vector((0.06, -0.16, -0.09)); S["fill_l"].rotation_euler = (math.radians(120), 0, math.radians(20))
        S["fill_l"].data.energy = 0.5 * inside; S["fill_l"].data.keyframe_insert("energy", frame=f)
        for o in (S["key_l"], S["rim_l"], S["fill_l"]):
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)

        # campo de texto e barras de UI: apagam com a tela e saem da renderização depois
        for o in [S["field"], *S["bars"]]:
            o.hide_render = t > T_SCREEN_OFF1 + 0.1; o.keyframe_insert("hide_render", frame=f)
        # teclas: afundam 1,6 mm quando pressionadas (≈ 70 ms)
        for ch, k in S["keys"].items():
            pass
        # cursor
        gp = ramp(t, T_GAP0, T_GAP1)
        n = typed_count(f)
        last = n - 1
        if last in WRAP:
            li = WRAP.index(last); cx = adv(LINES[li] + " ") * E
        else:
            li = max(i for i in range(3) if last >= LINE_START[i]); cx = adv(LINES[li][: last - LINE_START[li] + 1]) * E
        S["caret"].location = (cx + 0.0008, -li * EDITOR_PITCH + 0.0042, 0.0001)
        vis = 1.0
        if V["nem"] - 0.0 <= t: vis = 0.0 if TL["caret"]["lastKeyHoldUntil"] <= t < TL["caret"]["offUntil"] else 1.0
        vis *= 1 - ramp(t, TL["caret"]["fadeOutStart"], TL["caret"]["fadeOutEnd"])
        S["caret"].scale = (1, max(vis, 1e-4), 1); S["caret"].keyframe_insert("scale", frame=f); S["caret"].keyframe_insert("location", frame=f)

        # runs (letras) e fragmentos
        for i, r in enumerate(RUNS):
            o = S["runs"][i]
            k_line = ramp(t, T_PUSH0 + 0.25, T_PUSH1)            # entrelinha: editor → fragmentos
            ex, ey = editor_xy(r); tx, ty = token_xy(r, gp)
            x = tx; y = lerp(ey, ty, k_line)
            ta = T_TOK0 + r["token"] * T_TOK_STAG                # entrada deste fragmento
            a = ramp(t, ta, ta + 0.32)
            lift = ease_out((t - ta) / 0.45) * 0.30 * E if t > ta else 0.0
            o.location = (x, y, 0.00012 + lift + 0.004 * E); o.keyframe_insert("location", frame=f)
            o.data.extrude = 0.028 * E * a; o.data.keyframe_insert("extrude", frame=f)
            o.data.bevel_depth = 0.0035 * E * a; o.data.keyframe_insert("bevel_depth", frame=f)
            lm = S["letter_mats"][i].node_tree
            lm.nodes["pattern"].inputs["Factor"].default_value = pat * (1 - a)
            lm.nodes["pattern"].inputs["Factor"].keyframe_insert("default_value", frame=f)
            bs = lm.nodes["bsdf"]
            bs.inputs["Emission Strength"].default_value = lerp(1.0, 0.09, a)
            bs.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
            bs.inputs["Base Color"].default_value = (*(lerp(0.0, 0.70, a),) * 3, 1)
            bs.inputs["Base Color"].keyframe_insert("default_value", frame=f)

            # placa
            tile = S["tiles"][i]
            w = r["w"] + 2 * PAD + (SPACE if r["hanging"] else 0)
            left = x - PAD - (SPACE if r["hanging"] else 0)
            ymid = y + (S["TILE_TOP"] + S["TILE_BOT"]) / 2
            back_z = -S["DEPTH"] * 1.2
            tz = lerp(back_z, lift - S["DEPTH"] / 2, ease_out(a))
            tile.location = (left + w / 2, ymid, tz); tile.keyframe_insert("location", frame=f)
            tm = S["tile_mats"][i].node_tree.nodes["bsdf"]
            tm.inputs["Alpha"].default_value = a; tm.inputs["Alpha"].keyframe_insert("default_value", frame=f)
            rmn = S["rim_mats"][i].node_tree.nodes["bsdf"]
            rmn.inputs["Alpha"].default_value = a; rmn.inputs["Alpha"].keyframe_insert("default_value", frame=f)
            flash = math.exp(-max(0.0, t - ta - 0.12) / 0.25) if t > ta else 0.0
            rmn.inputs["Emission Strength"].default_value = a * (1.6 + 3.0 * flash)
            rmn.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)

            # ID: desce da placa e acende; filete liga placa → ID
            ti = T_ID0 + r["token"] * T_ID_STAG
            b = ramp(t, ti, ti + 0.35, ease_out)
            io = S["ids"][i]
            id_y = y + S["TILE_BOT"] - 0.62 * E
            io.location = (left + w / 2 - S["id_w"][i] / 2, lerp(id_y + 0.25 * E, id_y, b), lift * 0.6)
            io.keyframe_insert("location", frame=f)
            im = S["id_mats"][i].node_tree.nodes["bsdf"]
            im.inputs["Alpha"].default_value = b; im.inputs["Alpha"].keyframe_insert("default_value", frame=f)
            im.inputs["Emission Strength"].default_value = 1.1 * b; im.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
            ln = S["links"][i]
            top_y = y + S["TILE_BOT"]; bot_y = id_y + 0.42 * E * 0.75
            L = max(1e-5, (top_y - bot_y) * b * 0.82)
            ln.scale = (1, L, 1); ln.location = (left + w / 2, top_y - L / 2, lift * 0.6)
            ln.keyframe_insert("scale", frame=f); ln.keyframe_insert("location", frame=f)
        for r, mk in S["marks"]:
            i = RUNS.index(r)
            x, _ = token_xy(r, gp); y = lerp(-r["line"] * EDITOR_PITCH, -r["line"] * PITCH, ramp(t, T_PUSH0 + 0.25, T_PUSH1))
            sx = x - SPACE if r["hanging"] else x
            ta = T_TOK0 + r["token"] * T_TOK_STAG
            lift = ease_out((t - ta) / 0.45) * 0.30 * E if t > ta else 0.0
            mk.location = (sx + SPACE / 2, y + 0.03 * E, lift + 0.02 * E if t > ta else -0.01)
            mk.keyframe_insert("location", frame=f)

    # teclas: keyframes só nos eventos (pressão/soltura)
    for k in S["keys"].values():
        k.keyframe_insert("location", frame=0)
    for ev in TY["keys"]:
        ch = ev["key"] if ev["kind"] != "space" else " "
        kobj = S["keys"].get(ch) or S["keys"].get(ch.lower())
        if not kobj: continue
        z0 = 0.0135; f0 = ev["t"] * FPS
        for df, dz in [(-0.6, 0.0), (0.0, -0.0016), (1.6, -0.0016), (2.6, 0.0)]:
            kobj.location.z = z0 + dz; kobj.keyframe_insert("location", index=2, frame=f0 + df)
        kobj.location.z = z0

    # interpolação: linear entre keyframes por quadro; teclas com Bézier
    for o in bpy.data.objects:
        ad = o.animation_data
        if ad and ad.action and not o.name.startswith("tecla"):
            for fc in _fcurves(ad.action):
                for kp in fc.keyframe_points: kp.interpolation = "LINEAR"

def _fcurves(action):
    if hasattr(action, "fcurves") and len(action.fcurves):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out

def set_bodies(S, frame):
    n = typed_count(int(frame))
    for i, r in enumerate(RUNS):
        vis = max(0, min(len(r["text"]), n - r["start"]))
        body = r["text"][:vis]
        if S["runs"][i].data.body != body: S["runs"][i].data.body = body if body else " "

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=NFRAMES - 1)
    ap.add_argument("--frames", type=str, default=""); ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--scale", type=int, default=100); ap.add_argument("--out", default=os.path.join(ROOT, "out/frames"))
    ap.add_argument("--save-blend", default="")
    args = ap.parse_args(argv)
    S = build(args); animate(S)
    if args.save_blend: bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.save_blend))
    frames = [int(x) for x in args.frames.split(",")] if args.frames else list(range(args.start, args.end + 1))
    os.makedirs(args.out, exist_ok=True)
    import time
    # quadros sem nenhuma mudança: copia em vez de renderizar (mesma imagem, bit a bit)
    import shutil
    COPY = {f: 186 for f in list(range(187, 199)) + list(range(210, 212))}
    COPY.update({f: 199 for f in range(200, 210)})
    COPY.update({f: 318 for f in range(319, NFRAMES)})
    todo = [f for f in frames if f not in COPY] + [f for f in frames if f in COPY]
    for f in todo:
        t0 = time.time()
        if f in COPY:
            src = os.path.join(os.path.abspath(args.out), f"f{COPY[f]:04d}.png")
            if os.path.exists(src):
                shutil.copy(src, os.path.join(os.path.abspath(args.out), f"f{f:04d}.png")); print(f"quadro {f} = cópia de {COPY[f]}", flush=True); continue
        S["sc"].frame_set(f); set_bodies(S, f)
        S["sc"].render.filepath = os.path.join(os.path.abspath(args.out), f"f{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"quadro {f} em {time.time() - t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()
