#version 300 es

in float positionX;
in float positionY;
in float clusterId;

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

out float clusterIdVar;
out float isHighlighted;

void main() {

    clusterIdVar = clusterId;
    isHighlighted = (gl_VertexID == highlightedPointIdx) ? 1.0 : 0.0;

    vec3 rawPos = vec3(positionX, positionY, -1.0);

    vec3 normalizedPos = (rawPos + vec3(baseOffsetX, baseOffsetY, 0.0)) * vec3(baseScaleX, baseScaleY, 1.0);

    vec3 shiftedToActiveAreaPos = normalizedPos * vec3(activeAreaWidth, activeAreaHeight, 1.0) + vec3(marginLeft, marginBottom, 0.0);

    // zoom origin is at top left (0, 1), so we first need to move the points there, then zoom, and then move back
    vec3 zoomedPos = ((shiftedToActiveAreaPos - vec3(0.0, 1.0, 0.0)) * zoom) + vec3(0.0, 1.0, 0.0);
    vec3 pannedAndZoomedPos = zoomedPos + vec3(panX, -panY, 0);

    // positions are 0->1, so make -1->1
    // edit: we stay for now in 0-1 space
    vec3 pos = pannedAndZoomedPos;// * 2.0 - 1.0;

    // Scale towards camera to be more interesting
    // pos.z *= 10.0;

    // modelMatrix is one of the automatically attached uniforms when using the Mesh class
    vec4 mPos = modelMatrix * vec4(pos, 1.0);

    // get the model view position so that we can scale the points off into the distance
    vec4 mvPos = viewMatrix * mPos;
    gl_PointSize = 5.0;
    gl_Position = projectionMatrix * mvPos;
}
