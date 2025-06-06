#version 300 es

in vec2 position;
in float positionX;
in float positionY;
in float pointSize;
in float opacity;

uniform mat4 modelMatrix;
uniform mat4 viewMatrix;
uniform mat4 projectionMatrix;

uniform vec2 baseOffset;
uniform vec2 baseScale;
uniform vec2 viewportSize;
uniform vec2 activeAreaSize;
uniform float marginLeft;
uniform float marginBottom;
uniform vec2 pan;
uniform float zoom;
uniform int hoveredPointIdx;
uniform vec3 lightPosition;
uniform float devicePixelRatio;
uniform float pointSizeFactor;

out vec2 vUv;
out float isHighlighted;
out float opacityVar;

void main() {
    // pass data to fragment shader by setting varying variables:
    isHighlighted = (gl_VertexID == hoveredPointIdx) ? 1.0 : 0.0;
    opacityVar = opacity;

    // position calculation:
    vec3 rawPos = vec3(positionX, positionY, -2.0);
    vec3 normalizedPos = (rawPos + vec3(baseOffset, 0.0)) * vec3(baseScale, 1.0);
    vec3 shiftedToActiveAreaPos = normalizedPos * vec3(activeAreaSize, 1.0) + vec3(marginLeft, marginBottom, 0.0);

    // TODO: modify camera for pan and zoom instead of vertex position (to make sure dots stay the same size)

    // zoom origin is at top left (0, 1), so we first need to move the points there, then zoom, and then move back
    vec3 zoomedPos = ((shiftedToActiveAreaPos - vec3(0.0, 1.0, 0.0)) * vec3(zoom, zoom, 1.0)) + vec3(0.0, 1.0, 0.0);
    vec3 pannedAndZoomedPos = zoomedPos + vec3(pan.x, -pan.y, 0);

    // shadow direction:
    vec3 lightPos = vec3(lightPosition.xy, -2.0);
    float shadowOffsetZoomChange = 0.05;
    vec3 relativeShadowOffset = (pannedAndZoomedPos - lightPos) * ((1.0 - shadowOffsetZoomChange) + vec3(zoom * shadowOffsetZoomChange, zoom * shadowOffsetZoomChange, 1.0));
    vec3 shadowOffsetPos = pannedAndZoomedPos + relativeShadowOffset * (1.0 / 200.0);

    // position is now in range 0.0 - 1.0
    vec3 pointPos = shadowOffsetPos;

    // point size:
    // (see points.vert shader for how zoomAdjustment works)
    float zoomAdjustment = (zoom - 1.0) * 0.05 + 1.0;
    float shadowScale = 1.5;
    float pointSize = (12.0 + 10.0 * pointSize) * shadowScale * zoomAdjustment * pointSizeFactor * devicePixelRatio;

    vec2 quadVertexOffset = (position - 0.5) * (vec2(pointSize) / viewportSize);
    vec3 vertexPosition = pointPos + vec3(quadVertexOffset, 0.0) / devicePixelRatio;
    vUv = position;

    // transform position:
    // (modelMatrix is automatically set by the Mesh class)
    vec4 mPos = modelMatrix * vec4(vertexPosition, 1.0);
    vec4 mvPos = viewMatrix * mPos;
    gl_Position = projectionMatrix * mvPos;
}
