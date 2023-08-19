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

    isHighlighted = (gl_VertexID == highlightedPointIdx) ? 1.0 : 0.0;

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

    // positions are 0->1, so make -1->1
    // edit: we stay for now in 0-1 space
    vec3 pos = shadowOffsetPos;// * 2.0 - 1.0;

    // Scale towards camera to be more interesting
    // pos.z *= 10.0;

    // modelMatrix is one of the automatically attached uniforms when using the Mesh class
    vec4 mPos = modelMatrix * vec4(pos, 1.0);

    // get the model view position so that we can scale the points off into the distance
    vec4 mvPos = viewMatrix * mPos;
    float zoomAdjustment = (zoom - 1.0) * 0.3 + 1.0;
    gl_PointSize = (5.0 + 15.0 * pointSize) * 1.5 * zoomAdjustment * devicePixelRatio;
    gl_Position = projectionMatrix * mvPos;
}
