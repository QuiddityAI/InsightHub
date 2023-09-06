#version 300 es

precision highp float;

in float clusterIdVar;
flat in int pointIdxVar;
in float isHighlighted;
in float isSelected;
in float saturationVar;
in vec3 diffuseColor;

uniform sampler2D textureAtlas;
uniform float zoom;
uniform vec2 viewportSize;
uniform vec2 lightPosition;
uniform float devicePixelRatio;
uniform bool useTextureAtlas;

out vec4 FragColor;  // name doesn't matter, if there is just one output, it is the color


vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

float rand(vec2 co) {
    return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    // position of this fragment within point vertex:
    // note: posFromBottomLeft is similar to UV coordinate, but UV is from top left
    vec2 posFromBottomLeft = vec2(gl_PointCoord.x, 1.0 - gl_PointCoord.y);  // 0 - 1
	vec2 posFromCenter = (posFromBottomLeft - 0.5) * 2.0;
	float distFromCenter = length(posFromCenter);  // 0 - 1.0 within circle
    float pointRadiusPx = (5.0 * zoom * devicePixelRatio) / 2.0;
	// FragColor = vec4(relativeScreenPos, 1.0, 1.0);

    // circle area:
    float antiAliasingEdgePx = 1.0;
    float circleArea = 1.0 - smoothstep(1.0 - (antiAliasingEdgePx / pointRadiusPx), 1.0, distFromCenter);

    // position of this fragment on the screen:
	vec2 relativeScreenPos = gl_FragCoord.xy / (viewportSize * devicePixelRatio);  // 0-1, from bottom left

    // specular color:
    // (creating a fake-3D appearance by drawing a bright specular highlight)
	vec2 specularPosFromCenterOfCircle = (lightPosition - relativeScreenPos) * 0.5;
    float specColor = 1.0 - length(posFromCenter - specularPosFromCenterOfCircle);
    specColor = max(0.0, pow(specColor, 2.5));

    // darker edge:
    // (again faking 3D appearance by making the color darker near the edges)
    float edgeDarkness = -0.2 * smoothstep(0.5, 1.0, distFromCenter);

    // noise:
    float noise = 0.1 * rand(floor(posFromCenter * 40.0)/40.0);

    // texture:
    float uvRow = float(int(pointIdxVar) / (2048 / 32) + 1) / 64.0;
    float uvCol = float(int(pointIdxVar) % (2048 / 32)) / 64.0;
    float uvFactor = (2048.0/32.0);
    vec3 tex = texture(textureAtlas, vec2(uvCol, 1.0 - uvRow) + posFromBottomLeft / uvFactor).rgb;

    if (useTextureAtlas) {
        FragColor.rgb = tex;
    } else {
        FragColor.rgb = diffuseColor + 0.6 * vec3(specColor) + noise + edgeDarkness;
    }
    FragColor.a = circleArea * 0.7;
}
