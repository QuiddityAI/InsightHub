#version 300 es

precision highp float;

in vec2 vUv;
in vec3 vertexPositionVar;
in vec3 albedoColorVar;
in float opacityVar;
in float clusterIdVar;
flat in int pointIdxVar;
in float isHighlighted;
in float isSelected;
flat in float flatnessVar;
flat in float pointRadiusPxVar;
flat in float thumbnailAspectRatioVar;

uniform sampler2D textureAtlas;
uniform float zoom;
uniform vec2 viewportSize;
uniform vec3 lightPosition;
uniform float devicePixelRatio;
uniform bool useTextureAtlas;
// uniform sampler2D pointTextureBaseColor;
// uniform sampler2D pointTextureNormalMap;
uniform int thumbnailSpriteSize;
uniform float maxOpacity;

out vec4 FragColor;  // name doesn't matter, if there is just one output, it is the color

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

float roundedBoxSDF(vec2 posFromCenter, vec2 size, float radius, float borderThickness) {
    float distanceToEdge = length(max(abs(posFromCenter) - size + radius, 0.0)) - radius;
    float distanceToBorder = length(max(abs(posFromCenter) - (size - borderThickness) + radius, 0.0)) - radius;
    float edgeSoftness = 0.02;
    float smoothedAlpha = 1.0f - smoothstep(0.0f, edgeSoftness, distanceToEdge);
    //float border = smoothstep(0.0f, edgeSoftness, distanceToBorder);
    float border = step(0.0f, distanceToBorder);
    return smoothedAlpha * border;
}

void main() {
    FragColor = vec4(1.0, 1.0, 1.0, 0.0);

    // position of this fragment within point vertex / quad:
    vec2 posFromBottomLeft = vUv;  // 0 - 1

    bool showThumbnail = useTextureAtlas && thumbnailAspectRatioVar > 0.0;
    if (showThumbnail) {
        int atlasTotalWidth = 4096;
        int spritesPerLine = atlasTotalWidth / thumbnailSpriteSize;
        float uvRow = float(int(pointIdxVar) / spritesPerLine + 1) / float(spritesPerLine);
        float uvCol = float(int(pointIdxVar) % spritesPerLine) / float(spritesPerLine);
        float uvFactor = (float(atlasTotalWidth) / float(thumbnailSpriteSize));
        // making it smaller than the quad by 0.1 by subtracting 0.05 from posFromBottomLeft and multiplying uvFactor by 0.9
        vec4 tex = texture(textureAtlas, vec2(uvCol, 1.0 - uvRow) + (posFromBottomLeft - 0.05) / (uvFactor * 0.9));
        FragColor.rgb = tex.rgb;
        FragColor.a = roundedBoxSDF((posFromBottomLeft - vec2(0.5)) * 2.0, vec2(0.9), 0.4, 1.0);

        // add colored border:
        float isBorder = roundedBoxSDF((posFromBottomLeft - vec2(0.5)) * 2.0, vec2(1.0), 0.4, 0.18);
        FragColor.a = max(FragColor.a, isBorder) * opacityVar * maxOpacity;
        FragColor.rgb = mix(FragColor.rgb, albedoColorVar, isBorder);
    } else {

        vec2 circleCenter = vec2(0.5, 0.5);
        float circleRadius = 0.5;
        vec2 posFromCenter = (posFromBottomLeft - circleCenter) / circleRadius;
        float distFromCenter = length(posFromCenter);  // 0 - 1.0 within circle
        float pointRadiusPx = pointRadiusPxVar;

        // circle area:
        float antiAliasingEdgePx = 1.0;
        float circleArea = 1.0 - smoothstep(1.0 - (antiAliasingEdgePx / pointRadiusPx), 1.0, distFromCenter);
        FragColor.a = max(FragColor.a, circleArea) * opacityVar * maxOpacity;

        vec3 albedoColor = albedoColorVar;

        float borderWidthPx = 1.5;
        float borderRadius = 1.0 - (borderWidthPx / pointRadiusPx);
        float isBorder = smoothstep(borderRadius - (antiAliasingEdgePx / pointRadiusPx), borderRadius, distFromCenter);
        vec3 pointColorAtThisPixel = mix(albedoColor, vec3(1.0), isBorder);

        FragColor.rgb = mix(FragColor.rgb, pointColorAtThisPixel, circleArea);
    }
}
