#version 300 es

precision highp float;

in float clusterIdVar;
in float isHighlighted;
in float saturationVar;

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
    // diffuse color:
    vec3 pointColor = clusterIdVar < 0.0 ? vec3(isHighlighted > 0.5 ? 0.0 : 0.7) : hsv2rgb(vec3(clusterIdVar / 10.0, 0.1 + saturationVar * 1.0, isHighlighted > 0.5 ? 0.0 : 0.8));

    // basics:
    // note: posFromBottomLeft is similar to UV coordinate, but UV is from top left
    vec2 posFromBottomLeft = vec2(gl_PointCoord.x, 1.0 - gl_PointCoord.y);  // 0 - 1
	vec2 posFromCenter = (posFromBottomLeft - 0.5) * 2.0;
	float distFromCenter = length(posFromCenter);  // 0 - 1.0 within circle
    float pointRadiusPx = (5.0 * zoom * devicePixelRatio) / 2.0;
    float antiAliasingEdgePx = devicePixelRatio > 1.0 ? 0.0 : 1.0;
    float circleArea = 1.0 - smoothstep(1.0 - (antiAliasingEdgePx / pointRadiusPx), 1.0, distFromCenter);

	vec2 viewPortSize = vec2(viewportWidth * devicePixelRatio, viewportHeight * devicePixelRatio);
	vec2 relativeScreenPos = gl_FragCoord.xy / viewPortSize;  // 0-1, from bottom left
	// FragColor = vec4(relativeScreenPos, 1.0, 1.0);

    // specular color:
	vec2 lightPos = vec2(lightPositionX, lightPositionY);
	vec2 specularPosFromCenterOfCircle = (lightPos - relativeScreenPos) * 0.5;
    float specColor = 1.0 - length(posFromCenter - specularPosFromCenterOfCircle);
    specColor = max(0.0, pow(specColor, 2.5));

    // edge highlight:
    float edgeHighlight = 0.2 * smoothstep(0.5, 1.0, distFromCenter);

    // noise:
    float noise = 0.1 * rand(floor(posFromCenter * 40.0)/40.0);

    //gl_FragColor.rgb = 0.5 + 0.2 * sin(posFromBottomLeft.yxx) + vec3(0.1, 0.0, 0.3);
    FragColor.rgb = pointColor + 0.6 * vec3(specColor) + noise - edgeHighlight;
    FragColor.a = circleArea * 0.7;
}
