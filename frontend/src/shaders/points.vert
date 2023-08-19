#version 300 es

in float positionX;
in float positionY;
in float clusterId;
in float saturation;
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
uniform int selectedPointIdx;
uniform float devicePixelRatio;

out vec3 diffuseColor;
out float clusterIdVar;
out float isHighlighted;
out float isSelected;
out float saturationVar;


vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // pass data to fragment shader by setting varying variables:
    clusterIdVar = clusterId;
    saturationVar = saturation;
    isHighlighted = (gl_VertexID == highlightedPointIdx) ? 1.0 : 0.0;
    isSelected = (gl_VertexID == selectedPointIdx) ? 1.0 : 0.0;

    // diffuse color:
    // (the diffuse color is the same for all fragments of this vertex, so it
    // can be done in the vertex shader where its calculated only once)
    float hue = clusterIdVar / 10.0;
    float sat = 0.1 + saturationVar * 1.0;
    float val = isHighlighted > 0.5 ? 0.0 : 0.8;
    vec3 normalColor = hsv2rgb(vec3(hue, sat, val));
    vec3 highlightedColor = vec3(0.0);
    vec3 selectedColor = vec3(1.0, 0.0, 0.0);
    vec3 unclustered_color = vec3(0.7);
    diffuseColor = isHighlighted > 0.5 ? highlightedColor : (isSelected > 0.5 ? selectedColor : (clusterIdVar < 0.0 ? unclustered_color : normalColor));

    // position calculation:
    vec3 rawPos = vec3(positionX, positionY, (gl_VertexID == highlightedPointIdx) ? -0.9 : -1.0);
    vec3 normalizedPos = (rawPos + vec3(baseOffsetX, baseOffsetY, 0.0)) * vec3(baseScaleX, baseScaleY, 1.0);
    vec3 shiftedToActiveAreaPos = normalizedPos * vec3(activeAreaWidth, activeAreaHeight, 1.0) + vec3(marginLeft, marginBottom, 0.0);

    // TODO: modify camera for pan and zoom instead of vertex position (to make sure dots stay the same size)

    // zoom origin is at top left (0, 1), so we first need to move the points there, then zoom, and then move back
    vec3 zoomedPos = ((shiftedToActiveAreaPos - vec3(0.0, 1.0, 0.0)) * zoom) + vec3(0.0, 1.0, 0.0);
    vec3 pannedAndZoomedPos = zoomedPos + vec3(panX, -panY, 0);

    // position is now in range 0.0 - 1.0
    vec3 pos = pannedAndZoomedPos;

    // transform position:
    // (modelMatrix is automatically set by the Mesh class)
    vec4 mPos = modelMatrix * vec4(pos, 1.0);
    vec4 mvPos = viewMatrix * mPos;
    gl_Position = projectionMatrix * mvPos;

    // point size:
    // (By directly multiplying with zoom, the point size would be as with a real object,
    // the points would get bigger on screen when zooming in. In this case, we want
    // the points to only slightly get bigger, but essentially leaving more room between them
    // to be able to separate closing packet points by zooming in. This is what the
    // zoomAdjustment variable does. The same calculation is used in JS to get the pointSize
    // when checking if a point was clicked.)
    float zoomAdjustment = (zoom - 1.0) * 0.3 + 1.0;
    gl_PointSize = (5.0 + 15.0 * pointSize) * zoomAdjustment * devicePixelRatio;
}
