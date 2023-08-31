<script setup>

</script>

<script>

import panzoom from 'panzoom';

import { Renderer, Camera, Geometry, Program, Mesh, Transform } from 'https://cdn.jsdelivr.net/npm/ogl@0.0.117/+esm';
import * as math from 'mathjs'

import pointsVertexShader from '../shaders/points.vert?raw'
import pointsFragmentShader from '../shaders/points.frag?raw'
import shadowsVertexShader from '../shaders/shadows.vert?raw'
import shadowsFragmentShader from '../shaders/shadows.frag?raw'

export default {
  data() {
    return {
      // external:
      passiveMarginsLRTB: [0, 0, 0, 0],

      targetPositionsX: [],
      targetPositionsY: [],
      saturation: [],
      colors: [],
      pointSizes: [],
      clusterIdsPerPoint: [],

      itemDetails: [],
      clusterData: [],
      rendering: {},

      // internal:
      currentPositionsX: [],
      currentPositionsY: [],
      currentVelocityX: [],
      currentVelocityY: [],

      baseScale: [1.0, 1.0],
      baseOffset: [0.0, 0.0],
      baseScaleTarget: [1.0, 1.0],
      baseOffsetTarget: [0.0, 0.0],
      baseScaleVelocity: [0.0, 0.0],
      baseOffsetVelocity: [0.0, 0.0],

      panzoomInstance: null,
      currentZoom: 1.0,
      currentPan: [0.0, 0.0],

      // mouseover highlight and selection:
      selectedPointIdx: -1,  // set externally
      highlightedPointIdx: -1,  // set internally by mouseover
      mouseDownPosition: [-1, -1],

      // rendering:
      renderer: null,
      camera: null,
      glContext: null,
      glProgram: null,
      glMesh: null,
      glProgramShadows: null,
      glMeshShadows: null,
      glScene: null,
      lightPosition: [0.5, 1.5],
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
    "cluster_selected",
    "point_selected",
  ],
  mounted() {
    this.setupWebGl()
    this.setupPanZoom();
  },
  methods: {
    resetData() {
      this.targetPositionsX = []
      this.targetPositionsY = []
      this.saturation = [],
      this.colors = [],
      this.pointSizes = [],
      this.clusterIdsPerPoint = [],

      this.itemDetails = []
      this.clusterData = []

      this.selectedPointIdx = -1
      this.highlightedPointIdx = -1

      this.updateGeometry()
    },
    resetPanAndZoom() {
      this.panzoomInstance.moveTo(0, 0);
      this.panzoomInstance.zoomAbs(0, 0, 1);
    },
    screenLeftFromRelative(x) {
      const normalizedPos = (x + this.baseOffset[0]) * this.baseScale[0]
      const shiftedToActiveAreaPos = normalizedPos * this.activeAreaWidth + this.passiveMarginsLRTB[0]
      const pannedAndZoomed = shiftedToActiveAreaPos * this.currentZoom + this.currentPan[0]
      return pannedAndZoomed
    },
    screenBottomFromRelative(y) {
      const normalizedPos = (y + this.baseOffset[1]) * this.baseScale[1]
      const shiftedToActiveAreaPos = normalizedPos * this.activeAreaHeight + this.passiveMarginsLRTB[3]
      const zoomed = ((shiftedToActiveAreaPos - window.innerHeight) * this.currentZoom) + window.innerHeight
      const pannedAndZoomed = zoomed - this.currentPan[1]
      return pannedAndZoomed
    },
    screenRightFromRelative(x) {
      const normalizedPos = (x + this.baseOffset[0]) * this.baseScale[0]
      const shiftedToActiveAreaPos = normalizedPos * this.activeAreaWidth + this.passiveMarginsLRTB[0]
      const pannedAndZoomed = shiftedToActiveAreaPos * this.currentZoom + this.currentPan[0]
      return window.innerWidth - pannedAndZoomed
    },
    screenTopFromRelative(y) {
      const normalizedPos = (y + this.baseOffset[1]) * this.baseScale[1]
      const shiftedToActiveAreaPos = normalizedPos * this.activeAreaHeight + this.passiveMarginsLRTB[3]
      const zoomed = ((shiftedToActiveAreaPos - window.innerHeight) * this.currentZoom) + window.innerHeight
      const pannedAndZoomed = zoomed - this.currentPan[1]
      return window.innerHeight - pannedAndZoomed
    },
    screenToEmbeddingX(screenX) {
      const notPannedAndZoomedX = (screenX - this.currentPan[0]) / this.currentZoom
      const notShiftedToActiveAreaX = (notPannedAndZoomedX - this.passiveMarginsLRTB[0]) / this.activeAreaWidth
      const notNormalizedX = notShiftedToActiveAreaX / this.baseScale[0] - this.baseOffset[0]
      return notNormalizedX
    },
    screenToEmbeddingY(screenY) {
      const notPannedY = (window.innerHeight - screenY) + this.currentPan[1]
      const notPannedAndZoomedY = (notPannedY - window.innerHeight) / this.currentZoom + window.innerHeight
      const notShiftedToActiveAreaY = (notPannedAndZoomedY - this.passiveMarginsLRTB[3]) / this.activeAreaHeight
      const notNormalizedY = notShiftedToActiveAreaY / this.baseScale[1] - this.baseOffset[1]
      return notNormalizedY
    },
    setupPanZoom() {
      this.panzoomInstance = panzoom(this.$refs.panZoomProxy, {
        zoomSpeed: 0.35, // 35% per mouse wheel event
        minZoom: 0.7,
        bounds: true,
        onTouch: function(e) {
          return e.touches.length > 1;  // don't prevent touch propagation if there is just one touch (but when there are two or more to prevent zooming the page itself instead of this area only)
        }
      });

      const that = this

      this.panzoomInstance.on('transform', function(e) {
        const transform = e.getTransform()
        that.currentPan = [transform.x, transform.y]
        that.currentZoom = transform.scale
        that.updateUniforms()
      });
    },
    setupWebGl() {
      this.renderer = new Renderer({ depth: false, dpr: window.devicePixelRatio || 1.0 });
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
      this.updateGeometry()

      let lastUpdateTimeInMs = performance.now()

      function getAccelerationOfSpringArr(currentPos, currentVelocity, targetPosition, stiffness, mass, damping) {
        // inspired by https://blog.maximeheckel.com/posts/the-physics-behind-spring-animations/
        const displacement = math.subtract(currentPos, targetPosition)
        const k = -stiffness  // in kg / s^2
        const d = -damping  // in kg / s
        const Fspring = math.dotMultiply(k, displacement)
        const Fdamping = math.dotMultiply(d, currentVelocity)
        const acceleration = math.divide(math.add(Fspring, Fdamping), mass)
        return acceleration
      }

      requestAnimationFrame(update);
      function update(currentTimeInMs) {
        requestAnimationFrame(update);

        const timeSinceLastUpdateInSec = (currentTimeInMs - lastUpdateTimeInMs) / 1000.0
        lastUpdateTimeInMs = currentTimeInMs

        if (that.currentPositionsX.length == 0 || that.currentPositionsX.length != that.targetPositionsX.length) return;

        // restDelta means at which distance from the target position the movement stops and they
        // jump to the target (otherwise the motion could go on forever)
        // here we assume that the plot is about 700px wide and if the delta is less than a pixel, it should stop
        const restDelta = (math.max(that.targetPositionsX) - math.min(that.targetPositionsX)) / 700.0
        // to make sure overshoots still work, we don't stop the motion if the speed is still
        // greater than restSpeed, here defined as restDelta per 1/5th second
        const restSpeed = restDelta / 0.2  // in restDelta units per sec

        let geometryChanged = false
        let uniformsChanged = false

        const baseOffsetDiff = math.subtract(that.baseOffsetTarget, that.baseOffset)
        if (math.max(math.abs(baseOffsetDiff)) !== 0.0) {
          uniformsChanged = true

          const a = getAccelerationOfSpringArr(
            that.baseOffset, that.baseOffsetVelocity, that.baseOffsetTarget,
            /* stiffness */ 15.0, /* mass */ 1.0, /* damping */ 8.0
          )
          that.baseOffsetVelocity = math.add(that.baseOffsetVelocity, math.dotMultiply(a, timeSinceLastUpdateInSec))
          that.baseOffset = math.add(that.baseOffset, math.dotMultiply(that.baseOffsetVelocity, timeSinceLastUpdateInSec))
          if (math.max(math.abs(that.baseOffsetVelocity)) < restSpeed && math.max(math.abs(baseOffsetDiff)) < restDelta) {
            that.baseOffset = that.baseOffsetTarget.slice()  // using slice to copy the array
          }
        }

        const restSpeedScale = 0.0005
        const restDeltaScale = 0.00005

        const baseScaleDiff = math.subtract(that.baseScaleTarget, that.baseScale)
        if (math.max(math.abs(baseScaleDiff)) !== 0.0) {
          uniformsChanged = true

          const a = getAccelerationOfSpringArr(
            that.baseScale, that.baseScaleVelocity, that.baseScaleTarget,
            /* stiffness */ 15.0, /* mass */ 1.0, /* damping */ 8.0
          )
          that.baseScaleVelocity = math.add(that.baseScaleVelocity, math.dotMultiply(a, timeSinceLastUpdateInSec))
          that.baseScale = math.add(that.baseScale, math.dotMultiply(that.baseScaleVelocity, timeSinceLastUpdateInSec))
          if (math.max(math.abs(that.baseScaleVelocity)) < restSpeedScale && math.max(math.abs(baseScaleDiff)) < restDeltaScale) {
            that.baseScale = that.baseScaleTarget.slice()  // using slice to copy the array
          }
        }

        if (that.currentPositionsX.length === that.targetPositionsX.length) {
          const diffX = math.subtract(that.targetPositionsX, that.currentPositionsX)
          const diffY = math.subtract(that.targetPositionsY, that.currentPositionsY)
          if (math.max(math.abs(diffX)) !== 0.0 || math.max(math.abs(diffY)) !== 0.0) {
            geometryChanged = true

            const aX = getAccelerationOfSpringArr(
              that.currentPositionsX, that.currentVelocityX, that.targetPositionsX,
              /* stiffness */ 20.0, /* mass */ 1.0, /* damping */ 6.0
            )
            that.currentVelocityX = math.add(that.currentVelocityX, math.dotMultiply(aX, timeSinceLastUpdateInSec))
            that.currentPositionsX = math.add(that.currentPositionsX, math.dotMultiply(that.currentVelocityX, timeSinceLastUpdateInSec))
            if (math.max(math.abs(that.currentVelocityX)) < restSpeed && math.max(math.abs(diffX) < restDelta)) {
              that.currentPositionsX = that.targetPositionsX.slice()  // using slice to copy the array
            }

            const aY = getAccelerationOfSpringArr(
              that.currentPositionsY, that.currentVelocityY, that.targetPositionsY,
              /* stiffness */ 20.0, /* mass */ 1.0, /* damping */ 6.0
            )
            that.currentVelocityY = math.add(that.currentVelocityY, math.dotMultiply(aY, timeSinceLastUpdateInSec))
            that.currentPositionsY = math.add(that.currentPositionsY, math.dotMultiply(that.currentVelocityY, timeSinceLastUpdateInSec))
            if (math.max(math.abs(that.currentVelocityY)) < restSpeed && math.max(math.abs(diffY) < restDelta)) {
              that.currentPositionsY = that.targetPositionsY.slice()  // using slice to copy the array
            }

          }
        }

        if (geometryChanged) {
          that.updateGeometry()
        } else if (uniformsChanged) {
          that.updateUniforms()
        }
      }
    },
    centerAndFitDataToActiveAreaSmooth() {
      if (this.targetPositionsX.length === 0) return;
      this.baseOffsetTarget = [-math.min(this.targetPositionsX), -math.min(this.targetPositionsY)]
      this.baseScaleTarget[0] = 1.0 / (math.max(this.targetPositionsX) + this.baseOffsetTarget[0])
      this.baseScaleTarget[1] = 1.0 / (math.max(this.targetPositionsY) + this.baseOffsetTarget[1])
    },
    centerAndFitDataToActiveAreaInstant() {
      this.centerAndFitDataToActiveAreaSmooth()
      this.baseOffset = this.baseOffsetTarget.slice()  // using slice to copy the array
      this.baseScale = this.baseScaleTarget.slice()  // using slice to copy the array
      this.baseOffsetVelocity = [0.0, 0.0]
      this.baseScaleVelocity = [0.0, 0.0]
    },
    updateGeometry() {
      function ensureLength(x, size, fillValue) {
        if (x.length != size) {
          return Array(size).fill(fillValue)
        }
        return x
      }

      const pointCount = this.targetPositionsX.length
      this.targetPositionsY = ensureLength(this.targetPositionsY, pointCount, 0.0)

      this.currentPositionsX = ensureLength(this.currentPositionsX, pointCount, pointCount > 0 ? math.mean(this.targetPositionsX) : 0.0)
      this.currentPositionsY = ensureLength(this.currentPositionsY, pointCount, pointCount > 0 ? math.mean(this.targetPositionsY) : 0.0)
      this.currentVelocityX = ensureLength(this.currentVelocityX, pointCount, 0.0)
      this.currentVelocityY = ensureLength(this.currentVelocityY, pointCount, 0.0)

      this.clusterIdsPerPoint = ensureLength(this.clusterIdsPerPoint, pointCount, 0)
      this.saturation = ensureLength(this.saturation, pointCount, 1.0)
      this.pointSizes = ensureLength(this.pointSizes, pointCount, 0.5)

      this.glScene = new Transform();

      const shadowGeometry = new Geometry(this.glContext, {
          positionX: { size: 1, data: new Float32Array(this.currentPositionsX) },
          positionY: { size: 1, data: new Float32Array(this.currentPositionsY) },
          pointSize: { size: 1, data: new Float32Array(this.pointSizes) },
      });

      this.glProgramShadows = new Program(this.glContext, {
          vertex: shadowsVertexShader,
          fragment: shadowsFragmentShader,
          uniforms: this.getUniforms(),
          transparent: true,
          depthTest: false,
      });

      this.glMeshShadows = new Mesh(this.glContext, { mode: this.glContext.POINTS, geometry: shadowGeometry, program: this.glProgramShadows });
      this.glMeshShadows.setParent(this.glScene)

      const pointsGeometry = new Geometry(this.glContext, {
          positionX: { size: 1, data: new Float32Array(this.currentPositionsX) },
          positionY: { size: 1, data: new Float32Array(this.currentPositionsY) },
          clusterId: { size: 1, data: new Float32Array(this.clusterIdsPerPoint) },
          saturation: { size: 1, data: new Float32Array(this.saturation) },
          pointSize: { size: 1, data: new Float32Array(this.pointSizes) },
      });

      this.glProgram = new Program(this.glContext, {
          vertex: pointsVertexShader,
          fragment: pointsFragmentShader,
          uniforms: this.getUniforms(),
          transparent: true,
          depthTest: false,
          // depthFunc: this.glContext.NOTEQUAL,
      });

      this.glMesh = new Mesh(this.glContext, { mode: this.glContext.POINTS, geometry: pointsGeometry, program: this.glProgram });
      this.glMesh.setParent(this.glScene)

      this.renderer.render({ scene: this.glScene, camera: this.camera });
    },
    getUniforms() {
      const ww = window.innerWidth
      const wh = window.innerHeight
      return {  // types are inferred from shader code
        baseOffset: { value: this.baseOffset },
        baseScale: { value: this.baseScale },
        viewportSize: { value: [ww, wh] },
        activeAreaSize: { value: [this.activeAreaWidth / ww, this.activeAreaHeight / wh] },
        marginLeft: { value: this.passiveMarginsLRTB[0] / ww },
        marginBottom: { value: this.passiveMarginsLRTB[3] / wh },
        pan: { value: math.dotDivide(this.currentPan, [ww, wh]) },
        zoom: { value: this.currentZoom },
        highlightedPointIdx: { value: this.highlightedPointIdx },
        lightPosition: { value: this.lightPosition },
        devicePixelRatio: { value: window.devicePixelRatio || 1.0 },
        selectedPointIdx: { value: this.selectedPointIdx },
      }
    },
    updateUniforms() {
      this.glProgram.uniforms = this.getUniforms()
      this.glProgramShadows.uniforms = this.getUniforms()
      this.renderer.render({ scene: this.glScene, camera: this.camera });
    },
    updateOnHover(event) {
      if (event.buttons) return;
      const mousePosInEmbeddingSpaceX = this.screenToEmbeddingX(event.clientX)
      const mousePosInEmbeddingSpaceY = this.screenToEmbeddingY(event.clientY)

      // this.lightPosition = [event.clientX / window.innerWidth,  1.0 - event.clientY / window.innerHeight]

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
      const pointSize = this.pointSizes[closestIdx]
      const zoomAdjustment = (this.currentZoom - 1.0) * 0.3 + 1.0;
      const pointSizeScreenPx = (5.0 + 15.0 * pointSize) * zoomAdjustment * window.devicePixelRatio;
      const pointSizeEmbedding = this.screenToEmbeddingX(pointSizeScreenPx) - this.screenToEmbeddingX(0)
      const threshold = pointSizeEmbedding
      if (closestIdx && closestDist < threshold) {
        this.highlightedPointIdx = closestIdx
      } else {
        this.highlightedPointIdx = -1
      }
      this.updateUniforms()
    },
    onMouseLeave() {
      this.highlightedPointIdx = -1
    },
    onMouseDown(event) {
      if (event.pointerType === "mouse" && event.button != 0) return;
      this.mouseDownPosition = [event.clientX, event.clientY]
    },
    onMouseUp(event) {
      if (event.pointerType === "mouse" && event.button != 0) return;
      if (this.highlightedPointIdx === -1) return;
      const mouseMovementDistance = math.distance(this.mouseDownPosition, [event.clientX, event.clientY])
      if (mouseMovementDistance > 5) return;
      this.$emit('point_selected', this.highlightedPointIdx)
    },
  },
}

</script>

<template>
<div>
  <div class="fixed w-full h-full" ref="panZoomProxy"></div>

  <div ref="webGlArea" @mousemove="this.updateOnHover" @mousedown="onMouseDown" @mouseup="onMouseUp" @touchstart="onMouseDown" @touchend="onMouseUp" @mouseleave="onMouseLeave" class="fixed w-full h-full"></div>

  <!-- this div shows a gray outline around the "active area" for debugging purposes -->
  <!-- <div class="fixed ring-1 ring-inset ring-gray-300" :style="{'left': passiveMarginsLRTB[0] + 'px', 'right': passiveMarginsLRTB[1] + 'px', 'top': passiveMarginsLRTB[2] + 'px', 'bottom': passiveMarginsLRTB[3] + 'px'}"></div> -->


  <div v-for="cluster_label in clusterData" class="fixed"
  :style="{
    'left': screenLeftFromRelative(cluster_label.center[0]) + 'px',
    'bottom': screenBottomFromRelative(cluster_label.center[1]) + 'px',
    }">
    <button @click="$emit('cluster_selected', cluster_label)" class="px-1 backdrop-blur-sm bg-white/50 hover:bg-white text-gray-500 text-xs rounded">
      {{ cluster_label.title }}
    </button>
  </div>

  <div v-if="highlightedPointIdx !== -1" class="fixed pointer-events-none"
  :style="{
    'right': screenRightFromRelative(currentPositionsX[highlightedPointIdx]) + 'px',
    'top': screenTopFromRelative(currentPositionsY[highlightedPointIdx]) + 'px',
    'max-width': '200px',
    }">
    <div v-html="itemDetails.length > highlightedPointIdx ? rendering.hover_label(itemDetails[highlightedPointIdx]) : 'loading...'" class="px-1 backdrop-blur-sm bg-white/50 text-gray-500 text-xs rounded">
    </div>
  </div>
</div>
</template>

<style scoped></style>
