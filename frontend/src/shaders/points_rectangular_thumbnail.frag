#version 300 es

precision highp float;

in vec2 vUv;
in vec3 vertexPositionVar;
in vec3 albedoColorVar;
in float clusterIdVar;
flat in int pointIdxVar;
in float isHighlighted;
in float isSelected;
flat in uint pointVisibilityVar;
flat in float flatnessVar;
flat in float pointRadiusPxVar;

uniform sampler2D textureAtlas;
uniform float zoom;
uniform vec2 viewportSize;
uniform vec3 lightPosition;
uniform float devicePixelRatio;
uniform bool useTextureAtlas;
uniform sampler2D pointTextureBaseColor;
uniform sampler2D pointTextureNormalMap;
uniform int thumbnailSpriteSize;
uniform float maxOpacity;

out vec4 FragColor;  // name doesn't matter, if there is just one output, it is the color

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

float rand(vec2 co) {
    return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453);
}

vec3 get_normal_from_position_on_circle(float posX, float posY) {
    // adapted from https://stackoverflow.com/q/53271461
    float x = posX * 2.0 - 1.0;
    float y = posY * 2.0 - 1.0;

    float z = sqrt(1.0 - (pow(x, 2.0) + pow(y, 2.0)));

    vec3 position = vec3(x, y, z);

    // in case really only the circle should be drawn, we can discard all other pixels:
    // float mag = dot(position.xy, position.xy);
    // if(mag > 1.0) discard;

    vec3 normal = normalize(position);
    return normal;
}

void main() {
    if (pointVisibilityVar != 0u) {
        FragColor.a = 0.0;
        return;
    }

    // position of this fragment within point vertex / quad:
    vec2 posFromBottomLeft = vUv;  // 0 - 1

    if (useTextureAtlas) {
        int atlasTotalWidth = 4096;
        int spritesPerLine = atlasTotalWidth / thumbnailSpriteSize;
        float uvRow = float(int(pointIdxVar) / spritesPerLine + 1) / float(spritesPerLine);
        float uvCol = float(int(pointIdxVar) % spritesPerLine) / float(spritesPerLine);
        float uvFactor = (float(atlasTotalWidth) / float(thumbnailSpriteSize));
        vec4 tex = texture(textureAtlas, vec2(uvCol, 1.0 - uvRow) + posFromBottomLeft / uvFactor);
        FragColor = tex;
    }

    vec2 circleCenter = useTextureAtlas ? vec2(0.15, 0.85) : vec2(0.5, 0.5);
    float circleRadius = useTextureAtlas ? 0.15 : 0.5;
    vec2 posFromCenter = (posFromBottomLeft - circleCenter) / circleRadius;
    float distFromCenter = length(posFromCenter);  // 0 - 1.0 within circle
    float pointRadiusPx = pointRadiusPxVar;
    vec2 positionOnCircle = (posFromCenter + 1.0) / 2.0;

    // circle area:
    float antiAliasingEdgePx = 2.0;
    float circleArea = 1.0 - smoothstep(1.0 - (antiAliasingEdgePx / pointRadiusPx), 1.0, distFromCenter);
    FragColor.a = max(FragColor.a, circleArea) * maxOpacity;

    // position of this fragment on the screen:
    vec2 relativeScreenPos = gl_FragCoord.xy / (viewportSize * devicePixelRatio);  // 0-1, from bottom left

    // noise:
    float noise = 0.1 * rand(floor(posFromCenter * 40.0) / 40.0);

    float pi = 3.1415;
    float yFactor = cos(atan(posFromCenter.y, sqrt(1.0 - pow(posFromCenter.y, 2.0))));
    vec2 sphereUv = vec2(((positionOnCircle.x - 0.5) * 2.0 / max(yFactor, 0.001)) / 2.0 + 0.5, positionOnCircle.y);

    vec3 tangentSpaceTextureNormal = texture(pointTextureNormalMap, sphereUv / 3.0).xyz * 2.0 - 1.0;

    vec3 sphereNormal = get_normal_from_position_on_circle(positionOnCircle.x, positionOnCircle.y);  // normal from surface

    // // to apply normal maps, we need a tangent and a bitangent on the sphere in addition to the normal
    // // the tangent is pointing parallel to the surface, but there are any number of possible tangents
    // // the tangent should be in the same direction as used for the normal map
    // // here I tried to make up a formula to find that, it is not correct (reflections are in the wrong direction)
    // // but at least it shows the idea:
    // vec3 tangent = vec3(1.0 - sphereNormal.x, 1.0 - sphereNormal.y, 1.0 - (sphereNormal.z + sphereNormal.x));
    // vec3 bitangent = vec3(1.0 - sphereNormal.x, 1.0 - (sphereNormal.y + sphereNormal.z), 1.0 - sphereNormal.z);

    // // see also https://youtu.be/E4PHFnvMzFc?si=Z1nOGr4p5kJo-8DG&t=5165
    // mat3x3 mtxTangentToWorld = mat3x3(
    //     tangent.x, bitangent.x, sphereNormal.x,
    //     tangent.y, bitangent.y, sphereNormal.y,
    //     tangent.z, bitangent.z, sphereNormal.z
    // );

    // vec3 N = mtxTangentToWorld * tangentSpaceTextureNormal;

    vec3 N = sphereNormal;

    vec3 L = normalize(lightPosition - vertexPositionVar);  // vector to light

    vec3 cameraPosition = vec3(0.5, 0.5, 1.0);
    vec3 V = normalize(-(vertexPositionVar - cameraPosition)); // Vector to viewer

    // Lambert's cosine law
    float lambertian = max(dot(N, L), 0.0);
    float specular = 0.0;
    float shininessVal = 5.0;
    if (lambertian > 0.0) {
        vec3 R = reflect(-L, N);  // Reflected light vector
        // Compute the specular term
        float specAngle = max(dot(R, V), 0.0);
        specular = pow(specAngle, shininessVal);
    }
    float ambientLight = 0.5 + 0.5 * flatnessVar;
    vec3 specularColor = vec3(1.0);
    float specularStrength = 0.7 * (1.0 - flatnessVar);
    // vec3 albedoColor = texture(pointTextureBaseColor, sphereUv).rgb;
    vec3 albedoColor = albedoColorVar;

    vec3 pointColorAtThisPixel = albedoColor * ambientLight +
        lambertian * albedoColor * (1.0 - ambientLight) +
        specularStrength * specular * specularColor + noise;

    FragColor.rgb = mix(FragColor.rgb, pointColorAtThisPixel, circleArea);
}
