#version 300 es

precision highp float;

in float clusterIdVar;
in float isHighlighted;

out vec4 FragColor;  // name doesn't matter, if there is just one output, it is the color

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec2 uv = gl_PointCoord.xy;

    float circle = smoothstep(0.5, 0.4, length(uv - 0.5)) * 0.8;

    FragColor.rgb = hsv2rgb(vec3(clusterIdVar / 10.0, 0.7, isHighlighted > 0.5 ? 0.0 : 1.0));
    FragColor.a = circle;
}
