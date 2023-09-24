#version 300 es

precision highp float;

in vec2 vUv;
in float isHighlighted;

uniform float viewportWidth;
uniform float viewportHeight;

out vec4 FragColor;  // name doesn't matter, if there is just one output, it is the color

float rand(vec2 co) {
    return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec3 baseShadowColor = vec3(0.6);

    // position of this fragment within point vertex:
    // note: posFromBottomLeft is similar to UV coordinate, but UV is from top left
    vec2 posFromBottomLeft = vec2(vUv.x, 1.0 - vUv.y);  // 0 - 1
	vec2 posFromCenter = (posFromBottomLeft - 0.5) * 2.0;
	float distFromCenter = length(posFromCenter);  // 0 - 1.0 within circle

    float smoothShadowDarkness = pow(1.0 - smoothstep(0.0, 1.0, distFromCenter), 1.3);

    FragColor.rgb = baseShadowColor;
    FragColor.a = smoothShadowDarkness;
}
