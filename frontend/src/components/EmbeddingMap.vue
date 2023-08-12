<script setup>

</script>

<script>

import panzoom from 'panzoom';

import { Renderer, Camera, Geometry, Program, Mesh } from 'https://cdn.jsdelivr.net/npm/ogl@0.0.117/+esm';
import * as math from 'mathjs'

import vertex from './points.vert?raw'
import fragment from './points.frag?raw'

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
      glProgram: null,
      glMesh: null,
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
    screenToEmbeddingX(screenX) {
      const notPannedAndZoomedX = (screenX - this.currentPanX) / this.currentZoom
      const notShiftedToActiveAreaX = (notPannedAndZoomedX - this.passiveMarginsLRTB[0]) / this.activeAreaWidth
      const notNormalizedX = notShiftedToActiveAreaX / this.baseScaleX - this.baseOffsetX
      return notNormalizedX
    },
    screenToEmbeddingY(screenY) {
      const notPannedY = (window.innerHeight - screenY) + this.currentPanY
      const notPannedAndZoomedY = (notPannedY - window.innerHeight) / this.currentZoom + window.innerHeight
      const notShiftedToActiveAreaY = (notPannedAndZoomedY - this.passiveMarginsLRTB[3]) / this.activeAreaHeight
      const notNormalizedY = notShiftedToActiveAreaY / this.baseScaleY - this.baseOffsetY
      return notNormalizedY
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
        that.updateUniforms()
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

      let lastUpdateTimeInMs = performance.now()

      function getAccelerationOfSpring(currentPos, currentVelocity, targetPosition, stiffness, mass, damping) {
        const displacement = currentPos - targetPosition
        const k = -stiffness  // in kg / s^2
        const d = -damping  // in kg / s
        const Fspring = k * displacement
        const Fdamping = d * currentVelocity
        const acceleration = (Fspring + Fdamping) / mass
        return acceleration
      }

      requestAnimationFrame(update);
      function update(currentTimeInMs) {
        requestAnimationFrame(update);

        const timeSinceLastUpdateInSec = (currentTimeInMs - lastUpdateTimeInMs) / 1000.0
        lastUpdateTimeInMs = currentTimeInMs

        if (that.currentPositionsX.length == 0) return;

        // restDelta means at which distance from the target position the movement stops and they
        // jump to the target (otherwise the motion could go on forever)
        // here we assume that the plot is about 700px wide and if the delta is less than a pixel, it should stop
        const restDelta = (math.max(that.targetPositionsX) - math.min(that.targetPositionsX)) / 700.0
        // to make sure overshoots still work, we don't stop the motion if the speed is still
        // greater than restSpeed, here defined as restDelta per 1/5th second
        const restSpeed = restDelta / 0.2  // in restDelta units per sec

        let somethingChanged = false

        if (that.currentPositionsX.length === that.targetPositionsX.length) {
          for (const i of Array(that.targetPositionsX.length).keys()) {
            const diffX = that.targetPositionsX[i] - that.currentPositionsX[i]
            const diffY = that.targetPositionsY[i] - that.currentPositionsY[i]
            if (diffX === 0.0 && diffY === 0.0) continue;
            somethingChanged = true

            const aX = getAccelerationOfSpring(
              that.currentPositionsX[i], that.currentVelocityX[i], that.targetPositionsX[i],
              /* stiffness */ 10.0, /* mass */ 2.0, /* damping */ 4.0
            )
            that.currentVelocityX[i] += aX * timeSinceLastUpdateInSec
            that.currentPositionsX[i] += that.currentVelocityX[i] * timeSinceLastUpdateInSec
            if (Math.abs(that.currentVelocityX[i]) < restSpeed && Math.abs(diffX) < restDelta) {
              that.currentPositionsX[i] = that.targetPositionsX[i]
            }

            const aY = getAccelerationOfSpring(
              that.currentPositionsY[i], that.currentVelocityY[i], that.targetPositionsY[i],
              /* stiffness */ 10.0, /* mass */ 2.0, /* damping */ 4.0
            )
            that.currentVelocityY[i] += aY * timeSinceLastUpdateInSec
            that.currentPositionsY[i] += that.currentVelocityY[i] * timeSinceLastUpdateInSec
            if (Math.abs(that.currentVelocityY[i]) < restSpeed && Math.abs(diffY) < restDelta) {
              that.currentPositionsY[i] = that.targetPositionsY[i]
            }
          }
        }

        if (somethingChanged) {
          that.updateGeometry()
        }
      }
    },
    updateMap() {
      this.baseOffsetX = -Math.min(...this.targetPositionsX)
      this.baseOffsetY = -Math.min(...this.targetPositionsY)
      this.baseScaleX = 1.0 / (Math.max(...this.targetPositionsX) + this.baseOffsetX)
      this.baseScaleY = 1.0 / (Math.max(...this.targetPositionsY) + this.baseOffsetY)
      this.updateGeometry()
    },
    updateGeometry() {
      const geometry = new Geometry(this.glContext, {
          positionX: { size: 1, data: new Float32Array(this.currentPositionsX) },
          positionY: { size: 1, data: new Float32Array(this.currentPositionsY) },
          clusterId: { size: 1, data: new Float32Array(this.clusterIdsPerPoint) },
      });

      const ww = window.innerWidth
      const wh = window.innerHeight

      this.glProgram = new Program(this.glContext, {
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

      this.glMesh = new Mesh(this.glContext, { mode: this.glContext.POINTS, geometry, program: this.glProgram });

      this.renderer.render({ scene: this.glMesh, camera: this.camera });
    },
    updateUniforms() {

      const ww = window.innerWidth
      const wh = window.innerHeight

      this.glProgram.uniforms = {  // types are inferred from shader code
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
          }
        this.renderer.render({ scene: this.glMesh, camera: this.camera });
    },
    updateOnHover(event) {
      if (event.buttons) return;
      const mousePosInEmbeddingSpaceX = this.screenToEmbeddingX(event.clientX)
      const mousePosInEmbeddingSpaceY = this.screenToEmbeddingX(event.clientY)

      let closestIdx = null
      let closestDist = 10000000
      for (const i of Array(this.currentPositionsX.length).keys()) {
        const a = this.currentPositionsX[i] - mousePosInEmbeddingSpaceX
        const b = this.currentPositionsY[i] - mousePosInEmbeddingSpaceY
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
      this.updateUniforms()
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
