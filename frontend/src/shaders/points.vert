#version 300 es

// a maximum of 16 vertex attributes is allowed:
in vec2 position;
in float positionX;
in float positionY;
in float clusterId;
in float pointSize;
in float hue;
in float sat;
in float val;
in float opacity;
in float secondary_hue;
in float secondary_sat;
in float secondary_val;
in float secondary_opacity;
in float flatness;
in float thumbnailAspectRatio;

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
uniform int markedPointIdx;
uniform float devicePixelRatio;
uniform int selectedClusterId;
uniform float pointSizeFactor;

out vec2 vUv;
out vec3 vertexPositionVar;
out vec3 albedoColorVar;
out vec4 secondaryColorVar;
out float clusterIdVar;
flat out int pointIdxVar;
out float isHighlighted;
out float isSelected;
flat out float flatnessVar;
flat out float thumbnailAspectRatioVar;
flat out float pointRadiusPxVar;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    // pass data to fragment shader by setting varying variables:
    clusterIdVar = clusterId;
    pointIdxVar = gl_InstanceID;
    isHighlighted = (gl_InstanceID == hoveredPointIdx) ? 1.0 : 0.0;
    isSelected = (gl_InstanceID == markedPointIdx) ? 1.0 : 0.0;
    flatnessVar = flatness;
    thumbnailAspectRatioVar = thumbnailAspectRatio;

    // albedo color:
    // (the albedo color is the same for all fragments of this vertex, so it
    // can be done in the vertex shader where its calculated only once)
    float newVal = isHighlighted > 0.5 ? 0.0 : val;
    vec3 normalColor = hsv2rgb(vec3(hue, sat, newVal));
    vec3 highlightedColor = vec3(0.0);
    vec3 selectedColor = vec3(1.0, 0.0, 0.0);
    vec3 unclustered_color = vec3(0.7);
    albedoColorVar = isHighlighted > 0.5 ? highlightedColor : (isSelected > 0.5 ? selectedColor : (selectedClusterId != -1 && selectedClusterId != int(clusterId) ? unclustered_color : normalColor));

    secondaryColorVar = vec4(hsv2rgb(vec3(secondary_hue, secondary_sat, secondary_val)), secondary_opacity);

    // position calculation:
    vec3 rawPos = vec3(positionX, positionY, (gl_InstanceID == hoveredPointIdx) ? -0.9 : -1.0);
    vec3 normalizedPos = (rawPos + vec3(baseOffset, 0.0)) * vec3(baseScale, 1.0);
    vec3 shiftedToActiveAreaPos = normalizedPos * vec3(activeAreaSize, 1.0) + vec3(marginLeft, marginBottom, 0.0);

    // TODO: modify camera for pan and zoom instead of vertex position (to make sure dots stay the same size)

    // zoom origin is at top left (0, 1), so we first need to move the points there, then zoom, and then move back
    vec3 zoomedPos = ((shiftedToActiveAreaPos - vec3(0.0, 1.0, 0.0)) * vec3(zoom, zoom, 1.0)) + vec3(0.0, 1.0, 0.0);
    vec3 pannedAndZoomedPos = zoomedPos + vec3(pan.x, -pan.y, 0);

    // position is now in range 0.0 - 1.0
    vec3 pointPos = pannedAndZoomedPos;

    // point size:
    // (By directly multiplying with zoom, the point size would be as with a real object,
    // the points would get bigger on screen when zooming in. In this case, we want
    // the points to only slightly get bigger, but essentially leaving more room between them
    // to be able to separate closing packet points by zooming in. This is what the
    // zoomAdjustment variable does. The same calculation is used in JS to get the pointSize
    // when checking if a point was clicked.)
    float zoomAdjustment = (zoom - 1.0) * 0.05 + 1.0;
    float pointSize = (5.0 + 15.0 * pointSize) * zoomAdjustment * pointSizeFactor * devicePixelRatio;
    pointRadiusPxVar = pointSize / 2.0;

    vec2 quadVertexOffset = (position - 0.5) * (vec2(pointSize) / viewportSize);
    vec3 vertexPosition = pointPos + vec3(quadVertexOffset, 0.0) / devicePixelRatio;
    vUv = position;
    vertexPositionVar = vertexPosition;

    // transform position:
    // (modelMatrix is automatically set by the Mesh class)
    vec4 mPos = modelMatrix * vec4(vertexPosition, 1.0);
    vec4 mvPos = viewMatrix * mPos;
    gl_Position = projectionMatrix * mvPos;
}
