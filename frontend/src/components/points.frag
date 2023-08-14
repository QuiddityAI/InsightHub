#version 300 es

precision highp float;

in float clusterIdVar;
in float isHighlighted;

uniform float viewportWidth;
uniform float viewportHeight;

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
    vec2 uv = gl_PointCoord.xy;

    vec3 pointColor = hsv2rgb(vec3(clusterIdVar / 10.0, 0.8, isHighlighted > 0.5 ? 0.0 : 0.8));

    vec2 posFromUpperLeft = gl_PointCoord.xy;  // 0 - 1

	vec2 posFromCenter = posFromUpperLeft - 0.5;
	float distFromCenter = length(posFromCenter);  // 0 - 0.5

	vec2 viewPortSize = vec2(viewportWidth, viewportHeight);
	vec2 relativeScreenPos = gl_FragCoord.xy / viewPortSize;  // 0-1, from bottom left (?)
	relativeScreenPos.x = 1.0 - relativeScreenPos.x;  // 0-1, from top left (?)
	//gl_FragColor = vec4(relativeScreenPos, 1.0, 1.0);

	vec2 lightPos = vec2(0.3, 0.8);  // FIXME: x coord is inverse
	//vec2 specular = vec2(1.0 - relativeScreenPos.x / 2.0, 1.0 - relativeScreenPos.y / 2.0);
	vec2 specular = relativeScreenPos - lightPos;

    float circleArea = 1.0 - step(0.5, distFromCenter);  // smoothstep(0.5, 0.4, length(uv - 0.5));
    float noise = 0.2 * rand(floor(posFromCenter * 40.0)/40.0);
    float specColor = 1.0 - length(posFromCenter - specular);
    specColor = pow(specColor, 5.0);
    float edgeHighlight = 0.2 * smoothstep(0.25, 0.5, distFromCenter);

    //gl_FragColor.rgb = 0.5 + 0.2 * sin(posFromUpperLeft.yxx) + vec3(0.1, 0.0, 0.3);
    FragColor.rgb = pointColor + 0.6 * vec3(specColor) + noise + edgeHighlight;
    FragColor.a = circleArea;
}
