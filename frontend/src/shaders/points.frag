#version 300 es

precision highp float;

in float clusterIdVar;
in float isHighlighted;
in float isSelected;
in float saturationVar;
in vec3 diffuseColor;

uniform float zoom;
uniform float viewportWidth;
uniform float viewportHeight;
uniform float lightPositionX;
uniform float lightPositionY;
uniform float devicePixelRatio;

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
    vec2 viewPortSize = vec2(viewportWidth * devicePixelRatio, viewportHeight * devicePixelRatio);
	vec2 relativeScreenPos = gl_FragCoord.xy / viewPortSize;  // 0-1, from bottom left

    // specular color:
    // (creating a fake-3D appearance by drawing a bright specular highlight)
	vec2 lightPos = vec2(lightPositionX, lightPositionY);
	vec2 specularPosFromCenterOfCircle = (lightPos - relativeScreenPos) * 0.5;
    float specColor = 1.0 - length(posFromCenter - specularPosFromCenterOfCircle);
    specColor = max(0.0, pow(specColor, 2.5));

    // darker edge:
    // (again faking 3D appearance by making the color darker near the edges)
    float edgeDarkness = -0.2 * smoothstep(0.5, 1.0, distFromCenter);

    // noise:
    float noise = 0.1 * rand(floor(posFromCenter * 40.0)/40.0);

    FragColor.rgb = diffuseColor + 0.6 * vec3(specColor) + noise + edgeDarkness;
    FragColor.a = circleArea * 0.7;
}
