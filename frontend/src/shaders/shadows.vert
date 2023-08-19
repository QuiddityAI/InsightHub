#version 300 es

in float positionX;
in float positionY;
in float pointSize;

uniform mat4 modelMatrix;
uniform mat4 viewMatrix;
uniform mat4 projectionMatrix;

uniform float baseOffsetX;
uniform float baseOffsetY;
uniform float baseScaleX;
uniform float baseScaleY;
uniform float activeAreaWidth;
uniform float activeAreaHeight;
uniform float marginLeft;
uniform float marginBottom;
uniform float panX;
uniform float panY;
uniform float zoom;
uniform int highlightedPointIdx;
uniform float lightPositionX;
uniform float lightPositionY;
uniform float devicePixelRatio;

out float isHighlighted;

void main() {
    // pass data to fragment shader by setting varying variables:
    isHighlighted = (gl_VertexID == highlightedPointIdx) ? 1.0 : 0.0;

    // position calculation:
    vec3 rawPos = vec3(positionX, positionY, -2.0);
    vec3 normalizedPos = (rawPos + vec3(baseOffsetX, baseOffsetY, 0.0)) * vec3(baseScaleX, baseScaleY, 1.0);
    vec3 shiftedToActiveAreaPos = normalizedPos * vec3(activeAreaWidth, activeAreaHeight, 1.0) + vec3(marginLeft, marginBottom, 0.0);

    // TODO: modify camera for pan and zoom instead of vertex position (to make sure dots stay the same size)

    // zoom origin is at top left (0, 1), so we first need to move the points there, then zoom, and then move back
    vec3 zoomedPos = ((shiftedToActiveAreaPos - vec3(0.0, 1.0, 0.0)) * zoom) + vec3(0.0, 1.0, 0.0);
    vec3 pannedAndZoomedPos = zoomedPos + vec3(panX, -panY, 0);

    // shadow direction:
	vec3 lightPos = vec3(lightPositionX, lightPositionY, -2.0);
	vec3 relativeShadowOffset = (pannedAndZoomedPos - lightPos) * zoom;
    vec3 shadowOffsetPos = pannedAndZoomedPos + relativeShadowOffset * (1.0 / 200.0);

    // position is now in range 0.0 - 1.0
    vec3 pos = shadowOffsetPos;

    // transform position:
    // (modelMatrix is automatically set by the Mesh class)
    vec4 mPos = modelMatrix * vec4(pos, 1.0);
    vec4 mvPos = viewMatrix * mPos;
    gl_Position = projectionMatrix * mvPos;

    // point size:
    // (see points.vert shader for how zoomAdjustment works)
    float zoomAdjustment = (zoom - 1.0) * 0.3 + 1.0;
    float shadowScale = 1.5;
    gl_PointSize = (5.0 + 15.0 * pointSize) * shadowScale * zoomAdjustment * devicePixelRatio;
}
