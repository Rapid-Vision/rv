from enum import Enum


class RenderPass(Enum):
    """
    Enum representing the supported render passes available for export. To enable them, use `Scene.set_passes` method.

    For full documentation view [blender docs](https://docs.blender.org/manual/en/latest/render/layers/passes.html)
    """

    Z = "Z"
    VECTOR = "Vector"
    MIST = "Mist"
    POSITION = "Position"
    NORMAL = "Normal"
    UV = "UV"
    OBJECT_INDEX = "ObjectIndex"
    MATERIAL_INDEX = "MaterialIndex"
    SHADOW = "Shadow"
    AO = "AO"
    EMISSION = "Emission"
    ENVIRONMENT = "Environment"
    SHADOW_CATCHER = "ShadowCatcher"
    DIFFUSE_COLOR = "DiffuseColor"
    DIFFUSE_DIRECT = "DiffuseDirect"
    DIFFUSE_INDIRECT = "DiffuseIndirect"
    GLOSSY_COLOR = "GlossyColor"
    GLOSSY_DIRECT = "GlossyDirect"
    GLOSSY_INDIRECT = "GlossyIndirect"
    TRANSMISSION_COLOR = "TransmissionColor"
    TRANSMISSION_DIRECT = "TransmissionDirect"
    TRANSMISSION_INDIRECT = "TransmissionIndirect"
    CRYPTO_OBJECT = "CryptoObject"
    CRYPTO_MATERIAL = "CryptoMaterial"
    CRYPTO_ASSET = "CryptoAsset"


PASS_MAP = {
    RenderPass.Z: "use_pass_z",
    RenderPass.VECTOR: "use_pass_vector",
    RenderPass.MIST: "use_pass_mist",
    RenderPass.POSITION: "use_pass_position",
    RenderPass.NORMAL: "use_pass_normal",
    RenderPass.UV: "use_pass_uv",
    RenderPass.OBJECT_INDEX: "use_pass_object_index",
    RenderPass.MATERIAL_INDEX: "use_pass_material_index",
    RenderPass.SHADOW: "use_pass_shadow",
    RenderPass.AO: "use_pass_ambient_occlusion",
    RenderPass.EMISSION: "use_pass_emit",
    RenderPass.ENVIRONMENT: "use_pass_environment",
    RenderPass.SHADOW_CATCHER: "use_pass_shadow_catcher",
    RenderPass.DIFFUSE_COLOR: "use_pass_diffuse_color",
    RenderPass.DIFFUSE_DIRECT: "use_pass_diffuse_direct",
    RenderPass.DIFFUSE_INDIRECT: "use_pass_diffuse_indirect",
    RenderPass.GLOSSY_COLOR: "use_pass_glossy_color",
    RenderPass.GLOSSY_DIRECT: "use_pass_glossy_direct",
    RenderPass.GLOSSY_INDIRECT: "use_pass_glossy_indirect",
    RenderPass.TRANSMISSION_COLOR: "use_pass_transmission_color",
    RenderPass.TRANSMISSION_DIRECT: "use_pass_transmission_direct",
    RenderPass.TRANSMISSION_INDIRECT: "use_pass_transmission_indirect",
    RenderPass.CRYPTO_OBJECT: "use_pass_cryptomatte_object",
    RenderPass.CRYPTO_MATERIAL: "use_pass_cryptomatte_material",
    RenderPass.CRYPTO_ASSET: "use_pass_cryptomatte_asset",
}
