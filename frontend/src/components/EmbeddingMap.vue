<script setup>

</script>

<script>

import panzoom from 'panzoom';

import { Renderer, Camera, Geometry, Program, Mesh } from 'https://cdn.jsdelivr.net/npm/ogl@0.0.117/+esm';

const vertex = /* glsl */ `\
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
`;

const fragment = /* glsl */ `\
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
`;

export default {
  data() {
    return {
      // external:
      passiveMarginsLRTB: [0, 0, 0, 0],
      point_uids: [],
      currentPositionsX: [],
      currentPositionsY: [],
      targetPositionsX: [],
      targetPositionsY: [],
      colors: [],
      sizes: [],
      clusterIdsPerPoint: [],
      clusterData: [],

      // internal:
      currentVelocityX: [],
      currentVelocityY: [],
      baseScaleX: 1.0,
      baseScaleY: 1.0,
      baseOffsetX: 0.0,
      baseOffsetY: 0.0,
      currentZoom: 1.0,
      targetZoom: 1.0,
      currentPanX: 0.0,
      currentPanY: 0.0,
      targetPanX: 0.0,
      targetPanY: 0.0,
      highlightedPointIdx: -1,

      renderer: null,
      camera: null,
      glContext: null,
    }
  },
  computed: {
    activeAreaWidth() {
      return window.innerWidth - this.passiveMarginsLRTB[0] - this.passiveMarginsLRTB[1]
    },
    activeAreaHeight() {
      return window.innerHeight - this.passiveMarginsLRTB[2] - this.passiveMarginsLRTB[3]
    },
  },
  emits: [
    "show_cluster",
  ],
  mounted() {
    this.setupWebGl()
    this.setupPanZoom();
  },
  methods: {
    screenLeftFromRelative(x) {
      const normalizedPos = (x + this.baseOffsetX) * this.baseScaleX
      const shiftedToActiveAreaPos = normalizedPos * this.activeAreaWidth + this.passiveMarginsLRTB[0]
      const pannedAndZoomed = shiftedToActiveAreaPos * this.currentZoom + this.currentPanX
      return pannedAndZoomed
    },
    screenBottomFromRelative(y) {
      const normalizedPos = (y + this.baseOffsetY) * this.baseScaleY
      const shiftedToActiveAreaPos = normalizedPos * this.activeAreaHeight + this.passiveMarginsLRTB[3]
      const zoomed = ((shiftedToActiveAreaPos - window.innerHeight) * this.currentZoom) + window.innerHeight
      const pannedAndZoomed = zoomed - this.currentPanY
      return pannedAndZoomed
    },
    setupPanZoom() {
      const instance = panzoom(this.$refs.panZoomProxy, {
        zoomSpeed: 0.35, // 35% per mouse wheel event
        minZoom: 0.7,
        bounds: true,
      });

      const that = this

      instance.on('transform', function(e) {
        const transform = e.getTransform()
        that.currentPanX = transform.x
        that.currentPanY = transform.y
        that.currentZoom = transform.scale
        that.updateMap()
      });
    },
    setupWebGl() {
      this.renderer = new Renderer({ depth: false });
      this.glContext = this.renderer.gl;
      this.$refs.webGlArea.appendChild(this.glContext.canvas);
      this.glContext.clearColor(0.93, 0.94, 0.95, 1);

      this.camera = new Camera(this.glContext, { left: 0.00001, right: 1, top: 1, bottom: 0.0001 });
      this.camera.position.z = 1;

      const that = this

      function resize() {
        that.renderer.setSize(window.innerWidth, window.innerHeight);
        //that.camera.perspective({ aspect: that.glContext.canvas.width / that.glContext.canvas.height });
      }
      window.addEventListener('resize', resize, false);
      resize();
      this.updateMap()


      // requestAnimationFrame(update);
      // function update(t) {
      //     requestAnimationFrame(update);

      //     // add some slight overall movement to be more interesting
      //     particles.rotation.x = Math.sin(t * 0.0002) * 0.1;
      //     particles.rotation.y = Math.cos(t * 0.0005) * 0.15;
      //     particles.rotation.z += 0.01;

      //     program.uniforms.uTime.value = t * 0.001;
      //     renderer.render({ scene: particles, camera });
      // }
    },
    updateMap() {
      this.baseOffsetX = -Math.min(...this.currentPositionsX)
      this.baseOffsetY = -Math.min(...this.currentPositionsY)
      this.baseScaleX = 1.0 / (Math.max(...this.currentPositionsX) + this.baseOffsetX)
      this.baseScaleY = 1.0 / (Math.max(...this.currentPositionsY) + this.baseOffsetY)

      const ww = window.innerWidth
      const wh = window.innerHeight

      // FIXME: re-creating the geometry each time the map is moved is not efficient
      // find a way to just update uniforms?
      const geometry = new Geometry(this.glContext, {
          positionX: { size: 1, data: new Float32Array(this.currentPositionsX) },
          positionY: { size: 1, data: new Float32Array(this.currentPositionsY) },
          clusterId: { size: 1, data: new Float32Array(this.clusterIdsPerPoint) },
      });

      const program = new Program(this.glContext, {
          vertex,
          fragment,
          uniforms: {  // types are inferred from shader code
            baseOffsetX: { value: this.baseOffsetX },
            baseOffsetY: { value: this.baseOffsetY },
            baseScaleX: { value: this.baseScaleX },
            baseScaleY: { value: this.baseScaleY },
            activeAreaWidth: { value: this.activeAreaWidth / ww },
            activeAreaHeight: { value: this.activeAreaHeight / wh },
            marginLeft: { value: this.passiveMarginsLRTB[0] / ww },
            marginBottom: { value: this.passiveMarginsLRTB[3] / wh },
            panX: { value: this.currentPanX / ww },
            panY: { value: this.currentPanY / wh },
            zoom: { value: this.currentZoom },
            highlightedPointIdx: { value: this.highlightedPointIdx },
          },
          transparent: true,
          depthTest: false,
      });

      const points = new Mesh(this.glContext, { mode: this.glContext.POINTS, geometry, program });

      this.renderer.render({ scene: points, camera: this.camera });
    },
    updateOnHover(event) {
      if (event.buttons) return;
      const notPannedAndZoomedX = (event.clientX - this.currentPanX) / this.currentZoom
      const notShiftedToActiveAreaX = (notPannedAndZoomedX - this.passiveMarginsLRTB[0]) / this.activeAreaWidth
      const notNormalizedX = notShiftedToActiveAreaX / this.baseScaleX - this.baseOffsetX

      const notPannedY = (window.innerHeight - event.clientY) + this.currentPanY
      const notPannedAndZoomedY = (notPannedY - window.innerHeight) / this.currentZoom + window.innerHeight
      const notShiftedToActiveAreaY = (notPannedAndZoomedY - this.passiveMarginsLRTB[3]) / this.activeAreaHeight
      const notNormalizedY = notShiftedToActiveAreaY / this.baseScaleY - this.baseOffsetY

      let closestIdx = null
      let closestDist = 10000000
      for (const i of Array(this.currentPositionsX.length).keys()) {
        const a = this.currentPositionsX[i] - notNormalizedX
        const b = this.currentPositionsY[i] - notNormalizedY
        const distance = Math.sqrt(a*a + b*b)
        if (distance < closestDist) {
          closestDist = distance
          closestIdx = i
        }
      }
      const threshold = 100  // FIXME: this should be the size of a point in px converted to the embedding scale
      if (closestIdx && closestDist < threshold) {
        this.highlightedPointIdx = closestIdx
      } else {
        this.highlightedPointIdx = -1
      }
      this.updateMap()
    },
  },
}

</script>

<template>
  <div class="fixed w-full h-full" ref="panZoomProxy"></div>

  <div ref="webGlArea" @mousemove="this.updateOnHover" class="fixed w-full h-full"></div>

  <!-- this div shows a gray outline around the "active area" for debugging purposes -->
  <!-- <div class="fixed ring-1 ring-inset ring-gray-300" :style="{'left': passiveMarginsLRTB[0] + 'px', 'right': passiveMarginsLRTB[1] + 'px', 'top': passiveMarginsLRTB[2] + 'px', 'bottom': passiveMarginsLRTB[3] + 'px'}"></div> -->


  <div v-for="cluster_label in clusterData" class="fixed"
  :style="{
    'left': screenLeftFromRelative(cluster_label.center[0]) + 'px',
    'bottom': screenBottomFromRelative(cluster_label.center[1]) + 'px',
    }">
    <button @click="$emit('show_cluster', cluster_label)" class="px-1 bg-white/50 hover:bg-white text-gray-500 rounded">
      {{ cluster_label.title }}
    </button>
  </div>



</template>

<style scoped></style>
