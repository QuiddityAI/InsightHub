<script setup>

</script>

<script>

import panzoom from 'panzoom';

import { Renderer, Camera, Geometry, Program, Mesh, Transform } from 'https://cdn.jsdelivr.net/npm/ogl@0.0.117/+esm';
import * as math from 'mathjs'

import pointsVertexShader from './points.vert?raw'
import pointsFragmentShader from './points.frag?raw'
import shadowsVertexShader from './shadows.vert?raw'
import shadowsFragmentShader from './shadows.frag?raw'

export default {
  data() {
    return {
      // external:
      passiveMarginsLRTB: [0, 0, 0, 0],

      point_uids: [],
      targetPositionsX: [],
      targetPositionsY: [],
      saturation: [],
      colors: [],
      pointSizes: [],
      clusterIdsPerPoint: [],

      clusterData: [],

      // internal:
      currentPositionsX: [],
      currentPositionsY: [],
      currentVelocityX: [],
      currentVelocityY: [],
      baseScaleX: 1.0,
      baseScaleY: 1.0,
      baseOffsetX: 0.0,
      baseOffsetY: 0.0,
      baseScaleTargetX: 1.0,
      baseScaleTargetY: 1.0,
      baseOffsetTargetX: 0.0,
      baseOffsetTargetY: 0.0,
      baseScaleVelocityX: 0.0,
      baseScaleVelocityY: 0.0,
      baseOffsetVelocityX: 0.0,
      baseOffsetVelocityY: 0.0,
      currentZoom: 1.0,
      targetZoom: 1.0,
      currentPanX: 0.0,
      currentPanY: 0.0,
      targetPanX: 0.0,
      targetPanY: 0.0,
      highlightedPointIdx: -1,
      lightPositionX: 0.5,
      lightPositionY: 1.5,

      panzoomInstance: null,

      renderer: null,
      camera: null,
      glContext: null,
      glProgram: null,
      glMesh: null,
      glProgramShadows: null,
      glMeshShadows: null,
      glScene: null,
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
      this.panzoomInstance = panzoom(this.$refs.panZoomProxy, {
        zoomSpeed: 0.35, // 35% per mouse wheel event
        minZoom: 0.7,
        bounds: true,
      });

      const that = this

      this.panzoomInstance.on('transform', function(e) {
        const transform = e.getTransform()
        that.currentPanX = transform.x
        that.currentPanY = transform.y
        that.currentZoom = transform.scale
        that.updateUniforms()
      });
    },
    resetPanAndZoom() {
      this.panzoomInstance.moveTo(0, 0);
      this.panzoomInstance.zoomAbs(0, 0, 1);
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

        const baseOffsetDiffX = that.baseOffsetTargetX - that.baseOffsetX
        const baseOffsetDiffY = that.baseOffsetTargetY - that.baseOffsetY
        if (baseOffsetDiffX !== 0.0 || baseOffsetDiffY !== 0.0) {
          uniformsChanged = true

          const aX = getAccelerationOfSpring(
            that.baseOffsetX, that.baseOffsetVelocityX, that.baseOffsetTargetX,
            /* stiffness */ 15.0, /* mass */ 1.0, /* damping */ 8.0
          )
          that.baseOffsetVelocityX += aX * timeSinceLastUpdateInSec
          that.baseOffsetX += that.baseOffsetVelocityX * timeSinceLastUpdateInSec
          if (Math.abs(that.baseOffsetVelocityX) < restSpeed && Math.abs(baseOffsetDiffX) < restDelta) {
            that.baseOffsetX = that.baseOffsetTargetX
          }

          const aY = getAccelerationOfSpring(
            that.baseOffsetY, that.baseOffsetVelocityY, that.baseOffsetTargetY,
            /* stiffness */ 15.0, /* mass */ 1.0, /* damping */ 8.0
          )
          that.baseOffsetVelocityY += aY * timeSinceLastUpdateInSec
          that.baseOffsetY += that.baseOffsetVelocityY * timeSinceLastUpdateInSec
          if (Math.abs(that.baseOffsetVelocityY) < restSpeed && Math.abs(baseOffsetDiffY) < restDelta) {
            that.baseOffsetY = that.baseOffsetTargetY
          }
        }

        const baseScaleDiffX = that.baseScaleTargetX - that.baseScaleX
        const baseScaleDiffY = that.baseScaleTargetY - that.baseScaleY

        const restSpeedScale = 0.0005
        const restDeltaScale = 0.00005

        if (baseScaleDiffX !== 0.0 || baseScaleDiffY !== 0.0) {
          uniformsChanged = true

          const aX = getAccelerationOfSpring(
            that.baseScaleX, that.baseScaleVelocityX, that.baseScaleTargetX,
            /* stiffness */ 15.0, /* mass */ 1.0, /* damping */ 8.0
          )
          that.baseScaleVelocityX += aX * timeSinceLastUpdateInSec
          that.baseScaleX += that.baseScaleVelocityX * timeSinceLastUpdateInSec
          if (Math.abs(that.baseScaleVelocityX) < restSpeedScale && Math.abs(baseScaleDiffX) < restDeltaScale) {
            that.baseScaleX = that.baseScaleTargetX
          }

          const aY = getAccelerationOfSpring(
            that.baseScaleY, that.baseScaleVelocityY, that.baseScaleTargetY,
            /* stiffness */ 15.0, /* mass */ 1.0, /* damping */ 8.0
          )
          that.baseScaleVelocityY += aY * timeSinceLastUpdateInSec
          that.baseScaleY += that.baseScaleVelocityY * timeSinceLastUpdateInSec
          if (Math.abs(that.baseScaleVelocityY) < restSpeedScale && Math.abs(baseScaleDiffY) < restDeltaScale) {
            that.baseScaleY = that.baseScaleTargetY
          }
        }

        if (that.currentPositionsX.length === that.targetPositionsX.length) {
          for (const i of Array(that.targetPositionsX.length).keys()) {
            const diffX = that.targetPositionsX[i] - that.currentPositionsX[i]
            const diffY = that.targetPositionsY[i] - that.currentPositionsY[i]
            if (diffX === 0.0 && diffY === 0.0) continue;
            geometryChanged = true

            const aX = getAccelerationOfSpring(
              that.currentPositionsX[i], that.currentVelocityX[i], that.targetPositionsX[i],
              /* stiffness */ 20.0, /* mass */ 1.0, /* damping */ 6.0
            )
            that.currentVelocityX[i] += aX * timeSinceLastUpdateInSec
            that.currentPositionsX[i] += that.currentVelocityX[i] * timeSinceLastUpdateInSec
            if (Math.abs(that.currentVelocityX[i]) < restSpeed && Math.abs(diffX) < restDelta) {
              that.currentPositionsX[i] = that.targetPositionsX[i]
            }

            const aY = getAccelerationOfSpring(
              that.currentPositionsY[i], that.currentVelocityY[i], that.targetPositionsY[i],
              /* stiffness */ 20.0, /* mass */ 1.0, /* damping */ 6.0
            )
            that.currentVelocityY[i] += aY * timeSinceLastUpdateInSec
            that.currentPositionsY[i] += that.currentVelocityY[i] * timeSinceLastUpdateInSec
            if (Math.abs(that.currentVelocityY[i]) < restSpeed && Math.abs(diffY) < restDelta) {
              that.currentPositionsY[i] = that.targetPositionsY[i]
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
      this.baseOffsetTargetX = -math.min(this.targetPositionsX)
      this.baseOffsetTargetY = -math.min(this.targetPositionsY)
      this.baseScaleTargetX = 1.0 / (math.max(this.targetPositionsX) + this.baseOffsetTargetX)
      this.baseScaleTargetY = 1.0 / (math.max(this.targetPositionsY) + this.baseOffsetTargetY)
    },
    centerAndFitDataToActiveAreaInstant() {
      this.centerAndFitDataToActiveAreaSmooth()
      this.baseOffsetX = this.baseOffsetTargetX
      this.baseOffsetY = this.baseOffsetTargetY
      this.baseScaleX = this.baseScaleTargetX
      this.baseScaleY = this.baseScaleTargetY
      this.baseOffsetVelocityX = 0.0
      this.baseOffsetVelocityY = 0.0
      this.baseScaleVelocityX = 0.0
      this.baseScaleVelocityY = 0.0
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
        baseOffsetX: { value: this.baseOffsetX },
        baseOffsetY: { value: this.baseOffsetY },
        baseScaleX: { value: this.baseScaleX },
        baseScaleY: { value: this.baseScaleY },
        viewportWidth: { value: ww },
        viewportHeight: { value: wh },
        activeAreaWidth: { value: this.activeAreaWidth / ww },
        activeAreaHeight: { value: this.activeAreaHeight / wh },
        marginLeft: { value: this.passiveMarginsLRTB[0] / ww },
        marginBottom: { value: this.passiveMarginsLRTB[3] / wh },
        panX: { value: this.currentPanX / ww },
        panY: { value: this.currentPanY / wh },
        zoom: { value: this.currentZoom },
        highlightedPointIdx: { value: this.highlightedPointIdx },
        lightPositionX: { value: this.lightPositionX },
        lightPositionY: { value: this.lightPositionY },
        devicePixelRatio: { value: window.devicePixelRatio || 1.0 },
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

      // this.lightPositionX = event.clientX / window.innerWidth
      // this.lightPositionY = 1.0 - event.clientY / window.innerHeight

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
    <button @click="$emit('show_cluster', cluster_label)" class="px-1 backdrop-blur-sm bg-white/50 hover:bg-white text-gray-500 text-xs rounded">
      {{ cluster_label.title }}
    </button>
  </div>



</template>

<style scoped></style>
