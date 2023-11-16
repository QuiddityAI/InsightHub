<script setup>

</script>

<script>

import panzoom from 'panzoom';

import { Renderer, Camera, Geometry, Program, Mesh, Transform, Texture, TextureLoader } from 'https://cdn.jsdelivr.net/npm/ogl@0.0.117/+esm';
import * as math from 'mathjs'

import pointsVertexShader from '../shaders/points.vert?raw'
import pointsFragmentShader from '../shaders/points.frag?raw'
import shadowsVertexShader from '../shaders/shadows.vert?raw'
import shadowsFragmentShader from '../shaders/shadows.frag?raw'

import pointTextureBaseColorUrl from '../textures/Brick_Wall_017_basecolor.jpg'
import pointTextureNormalMapUrl from '../textures/Crystal_001_NORM.jpg'

import { ensureLength } from '../utils/utils.js'

export default {
  props: ["appStateStore"],  // for some reason, importing it doesn't work
  emits: [
    "cluster_selected",
    "point_selected",
    "cluster_hovered",
    "cluster_hover_end",
  ],
  data() {
    return {
      // external:
      passiveMarginsLRTB: [0, 0, 0, 0],

      // per point:
      targetPositionsX: [],
      targetPositionsY: [],
      per_point: {
        size: [],
        hue: [],
        sat: [],
        val: [],
        opacity: [],
        secondary_hue: [],
        secondary_sat: [],
        secondary_val: [],
        secondary_opacity: [],
      },
      clusterIdsPerPoint: [],
      itemDetails: [],  // text data per point

      // for all points:
      maxOpacity: 0.7,
      pointSizeFactor: 1.0,
      attribute_fallback: {
        size: 0.5,
        hue: 0.0,
        sat: 0.7,
        val: 0.7,
        opacity: 1.0,
        secondary_hue: 0.0,
        secondary_sat: 1.0,
        secondary_val: 1.0,
        secondary_opacity: 1.0,
      },

      clusterData: [],  // array of cluster description objects
      hover_label_rendering: {},
      textureAtlas: null,
      thumbnailSpriteSize: 64,

      // internal:
      currentPositionsX: [],
      currentPositionsY: [],
      currentVelocityX: [],
      currentVelocityY: [],
      pointVisibility: [],
      visiblePointIndexes: [],

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
      glTextureAtlas: null,
      lightPosition: [0.5, 0.5, -0.5],

      pointTextureBaseColor: null,
      pointTextureNormalMap: null,
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
  mounted() {
    this.setupWebGl()
    this.setupPanZoom();
    setInterval(this.updatePointVisibility, 500);
  },
  watch: {
    "appStateStore.selected_cluster_id" () {
      this.updateUniforms()
    },
    "appStateStore.highlighted_cluster_id" () {
      this.updateUniforms()
    },
    "appStateStore.highlighted_item_id" () {
      if (this.appStateStore.highlighted_item_id === null) {
        this.highlightedPointIdx = -1
        this.$emit('cluster_hover_end')
        return
      }
      for (const i of Array(this.itemDetails.length).keys()) {
        if (this.itemDetails[i]._id == this.appStateStore.highlighted_item_id) {
          this.highlightedPointIdx = i
          // TODO: highlighted_cluster_id should be changed directly, but currently accessing appState breaks this component
          this.$emit('cluster_hovered', this.clusterIdsPerPoint[i])
          this.updateUniforms()
          break
        }
      }
    },
  },
  methods: {
    resetData() {
      this.targetPositionsX = []
      this.targetPositionsY = []
      this.per_point = {
        size: [],
        hue: [],
        sat: [],
        val: [],
        opacity: [],
        secondary_hue: [],
        secondary_sat: [],
        secondary_val: [],
        secondary_opacity: [],
      }
      this.clusterIdsPerPoint = []
      this.itemDetails = []

      this.maxOpacity = 0.7
      this.pointSizeFactor = 1.0
      this.attribute_fallback = {
        size: 0.5,
        hue: 0.0,
        sat: 0.7,
        val: 0.7,
        opacity: 1.0,
        secondary_hue: 0.0,
        secondary_sat: 1.0,
        secondary_val: 1.0,
        secondary_opacity: 1.0,
      }

      this.clusterData = []
      this.textureAtlas = null
      this.thumbnailSpriteSize = 64

      this.selectedPointIdx = -1
      this.highlightedPointIdx = -1

      this.updateGeometry()
    },
    resetPanAndZoom() {
      // smooth reset doesn't seem to be possible because during smooth movement, the transfrom isn't updated?
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
      const that = this
      this.panzoomInstance = panzoom(this.$refs.panZoomProxy, {
        zoomSpeed: 0.35, // 35% per mouse wheel event
        minZoom: 0.7,
        bounds: false,
        zoomDoubleClickSpeed: 1,  // disable zoom on double click
        onTouch: function(e) {
          return e.touches.length > 1;  // don't prevent touch propagation if there is just one touch (but when there are two or more to prevent zooming the page itself instead of this area only)
        },
        onDoubleClick: function(e) {
          that.resetPanAndZoom()
        }
      });

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
          if (math.max(math.abs(diffX)) > restDelta || math.max(math.abs(diffY)) > restDelta) {
            geometryChanged = true

            const aX = getAccelerationOfSpringArr(
              that.currentPositionsX, that.currentVelocityX, that.targetPositionsX,
              /* stiffness */ 20.0, /* mass */ 1.0, /* damping */ 6.0
            )
            that.currentVelocityX = math.add(that.currentVelocityX, math.dotMultiply(aX, timeSinceLastUpdateInSec))
            that.currentPositionsX = math.add(that.currentPositionsX, math.dotMultiply(that.currentVelocityX, timeSinceLastUpdateInSec))
            if (math.max(math.abs(that.currentVelocityX)) < restSpeed && math.max(math.abs(diffX)) < restDelta) {
              that.currentPositionsX = that.targetPositionsX.slice()  // using slice to copy the array
            }

            const aY = getAccelerationOfSpringArr(
              that.currentPositionsY, that.currentVelocityY, that.targetPositionsY,
              /* stiffness */ 20.0, /* mass */ 1.0, /* damping */ 6.0
            )
            that.currentVelocityY = math.add(that.currentVelocityY, math.dotMultiply(aY, timeSinceLastUpdateInSec))
            that.currentPositionsY = math.add(that.currentPositionsY, math.dotMultiply(that.currentVelocityY, timeSinceLastUpdateInSec))
            if (math.max(math.abs(that.currentVelocityY)) < restSpeed && math.max(math.abs(diffY)) < restDelta) {
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
      const newBaseOffsetTarget = [-math.min(this.targetPositionsX), -math.min(this.targetPositionsY)]
      const newBaseScaleTarget = [1.0, 1.0]
      newBaseScaleTarget[0] = 1.0 / (math.max(this.targetPositionsX) + newBaseOffsetTarget[0])
      newBaseScaleTarget[1] = 1.0 / (math.max(this.targetPositionsY) + newBaseOffsetTarget[1])
      const offsetChange = math.max(math.max(newBaseOffsetTarget[0], this.baseOffsetTarget[0]) / math.min(newBaseOffsetTarget[0], this.baseOffsetTarget[0]), math.max(newBaseOffsetTarget[1], this.baseOffsetTarget[1]) / math.min(newBaseOffsetTarget[1], this.baseOffsetTarget[1]))
      const scaleChange = math.max(math.max(newBaseScaleTarget[0], this.baseScaleTarget[0]) / math.min(newBaseScaleTarget[0], this.baseScaleTarget[0]), math.max(newBaseScaleTarget[1], this.baseScaleTarget[1]) / math.min(newBaseScaleTarget[1], this.baseScaleTarget[1]))
      this.baseOffsetTarget = newBaseOffsetTarget
      this.baseScaleTarget = newBaseScaleTarget
      if (offsetChange > 1.5 || scaleChange > 1.5) {
        this.baseOffset = this.baseOffsetTarget.slice()  // using slice to copy the array
        this.baseScale = this.baseScaleTarget.slice()  // using slice to copy the array
        this.baseOffsetVelocity = [0.0, 0.0]
        this.baseScaleVelocity = [0.0, 0.0]
      }
    },
    centerAndFitDataToActiveAreaInstant() {
      this.centerAndFitDataToActiveAreaSmooth()
      this.baseOffset = this.baseOffsetTarget.slice()  // using slice to copy the array
      this.baseScale = this.baseScaleTarget.slice()  // using slice to copy the array
      this.baseOffsetVelocity = [0.0, 0.0]
      this.baseScaleVelocity = [0.0, 0.0]
    },
    regenerateAttributeArraysFromFallbacks() {
      const pointCount = this.targetPositionsX.length
      for (const attr of ["size", "hue", "sat", "val", "opacity", "secondary_hue", "secondary_sat", "secondary_val", "secondary_opacity"]) {
        this.per_point[attr] = []
        this.per_point[attr] = ensureLength(this.per_point[attr], pointCount, this.attribute_fallback[attr])
      }
    },
    updateGeometry() {
      const pointCount = this.targetPositionsX.length
      this.targetPositionsY = ensureLength(this.targetPositionsY, pointCount, 0.0)

      this.currentPositionsX = ensureLength(this.currentPositionsX, pointCount, pointCount > 0 ? math.mean(this.targetPositionsX) : 0.0, true)
      this.currentPositionsY = ensureLength(this.currentPositionsY, pointCount, pointCount > 0 ? math.mean(this.targetPositionsY) : 0.0, true)
      this.currentVelocityX = ensureLength(this.currentVelocityX, pointCount, 0.0, true)
      this.currentVelocityY = ensureLength(this.currentVelocityY, pointCount, 0.0, true)
      this.pointVisibility = ensureLength(this.pointVisibility, pointCount, 0)

      this.clusterIdsPerPoint = ensureLength(this.clusterIdsPerPoint, pointCount, 0)
      for (const attr of ["size", "hue", "sat", "val", "opacity", "secondary_hue", "secondary_sat", "secondary_val", "secondary_opacity"]) {
        this.per_point[attr] = ensureLength(this.per_point[attr], pointCount, this.attribute_fallback[attr])
      }

      this.glTextureAtlas = new Texture(this.glContext, {
        generateMipmaps: false, minFilter: this.glContext.NEAREST, magFilter: this.glContext.LINEAR
      });
      if (this.textureAtlas) {
        this.glTextureAtlas.image = this.textureAtlas;
      }

      this.pointTextureBaseColor = TextureLoader.load(this.glContext, { src: pointTextureBaseColorUrl});
      this.pointTextureNormalMap = TextureLoader.load(this.glContext, { src: pointTextureNormalMapUrl, minFilter: this.glContext.LINEAR });

      this.glScene = new Transform();
      this.updateMeshesQuads();

      this.renderer.render({ scene: this.glScene, camera: this.camera });
    },
    updateMeshesPoints() {
      const shadowGeometry = new Geometry(this.glContext, {
          positionX: { size: 1, data: new Float32Array(this.currentPositionsX) },
          positionY: { size: 1, data: new Float32Array(this.currentPositionsY) },
          pointSize: { size: 1, data: new Float32Array(this.per_point.size) },
          pointVisibility: { size: 1, data: new Float32Array(this.pointVisibility) },
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
          pointSize: { size: 1, data: new Float32Array(this.per_point.size) },
          hue: { size: 1, data: new Float32Array(this.per_point.hue) },
          sat: { size: 1, data: new Float32Array(this.per_point.sat) },
          val: { size: 1, data: new Float32Array(this.per_point.val) },
          opacity: { size: 1, data: new Float32Array(this.per_point.opacity) },
          secondary_hue: { size: 1, data: new Float32Array(this.per_point.secondary_hue) },
          secondary_sat: { size: 1, data: new Float32Array(this.per_point.secondary_sat) },
          secondary_val: { size: 1, data: new Float32Array(this.per_point.secondary_val) },
          secondary_opacity: { size: 1, data: new Float32Array(this.per_point.secondary_opacity) },
          pointVisibility: { size: 1, data: new Float32Array(this.pointVisibility) },
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
    },
    updateMeshesQuads() {
      const pointCount = this.currentPositionsX.length
      const shadowGeometry = new Geometry(this.glContext, {
          position: { size: 2, data: new Float32Array([0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0]) },
          positionX: { instanced: 1, size: 1, data: new Float32Array(this.currentPositionsX) },
          positionY: { instanced: 1, size: 1, data: new Float32Array(this.currentPositionsY) },
          pointSize: { instanced: 1, size: 1, data: new Float32Array(this.per_point.size.slice(0, pointCount)) },
          pointVisibility: { instanced: 1, size: 1, data: new Float32Array(this.pointVisibility.slice(0, pointCount)) },
      });

      this.glProgramShadows = new Program(this.glContext, {
          vertex: shadowsVertexShader,
          fragment: shadowsFragmentShader,
          uniforms: this.getUniforms(),
          transparent: true,
          depthTest: false,
      });

      this.glMeshShadows = new Mesh(this.glContext, { mode: this.glContext.TRIANGLE_STRIP, geometry: shadowGeometry, program: this.glProgramShadows });
      this.glMeshShadows.setParent(this.glScene)

      const pointsGeometry = new Geometry(this.glContext, {
          position: { size: 2, data: new Float32Array([0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0]) },
          positionX: { instanced: 1,  size: 1, data: new Float32Array(this.currentPositionsX) },
          positionY: { instanced: 1,  size: 1, data: new Float32Array(this.currentPositionsY) },
          clusterId: { instanced: 1,  size: 1, data: new Float32Array(this.clusterIdsPerPoint.slice(0, pointCount)) },
          pointSize: { instanced: 1, size: 1, data: new Float32Array(this.per_point.size.slice(0, pointCount)) },
          hue: { instanced: 1, size: 1, data: new Float32Array(this.per_point.hue.slice(0, pointCount)) },
          sat: { instanced: 1, size: 1, data: new Float32Array(this.per_point.sat.slice(0, pointCount)) },
          val: { instanced: 1, size: 1, data: new Float32Array(this.per_point.val.slice(0, pointCount)) },
          opacity: { instanced: 1, size: 1, data: new Float32Array(this.per_point.opacity.slice(0, pointCount)) },
          secondary_hue: { instanced: 1, size: 1, data: new Float32Array(this.per_point.secondary_hue.slice(0, pointCount)) },
          secondary_sat: { instanced: 1, size: 1, data: new Float32Array(this.per_point.secondary_sat.slice(0, pointCount)) },
          secondary_val: { instanced: 1, size: 1, data: new Float32Array(this.per_point.secondary_val.slice(0, pointCount)) },
          secondary_opacity: { instanced: 1, size: 1, data: new Float32Array(this.per_point.secondary_opacity.slice(0, pointCount)) },
          pointVisibility: { instanced: 1, size: 1, data: new Float32Array(this.pointVisibility.slice(0, pointCount)) },
      });

      this.glProgram = new Program(this.glContext, {
          vertex: pointsVertexShader,
          fragment: pointsFragmentShader,
          uniforms: this.getUniforms(),
          transparent: true,
          depthTest: false,
          // depthFunc: this.glContext.NOTEQUAL,
      });

      this.glMesh = new Mesh(this.glContext, { mode: this.glContext.TRIANGLE_STRIP, geometry: pointsGeometry, program: this.glProgram });
      this.glMesh.setParent(this.glScene)
    },
    getUniforms() {
      const ww = window.innerWidth
      const wh = window.innerHeight
      let selectedClusterId = this.appStateStore.selected_cluster_id != null ? this.appStateStore.selected_cluster_id : -1
      if (this.appStateStore.highlighted_cluster_id !== null) {
        selectedClusterId = this.appStateStore.highlighted_cluster_id
      }

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
        textureAtlas: { value: this.glTextureAtlas },
        useTextureAtlas: { value: this.textureAtlas !== null },
        pointTextureBaseColor: { value: this.pointTextureBaseColor },
        pointTextureNormalMap: { value: this.pointTextureNormalMap },
        thumbnailSpriteSize: { value: this.thumbnailSpriteSize },
        selectedClusterId: { value: selectedClusterId },
        maxOpacity: { value: this.maxOpacity },
        pointSizeFactor: { value: this.pointSizeFactor },
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
      const pointSize = this.per_point.size[closestIdx]
      const zoomAdjustment = (this.currentZoom - 1.0) * 0.05 + 1.0;
      const pointSizeScreenPx = (5.0 + 15.0 * pointSize) * zoomAdjustment * this.pointSizeFactor;
      const pointRadiusScreenPx = pointSizeScreenPx / 2
      const pointRadiusEmbedding = this.screenToEmbeddingX(pointRadiusScreenPx) - this.screenToEmbeddingX(0)
      const threshold = pointRadiusEmbedding
      if (closestIdx !== null && closestDist < threshold) {
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
    updatePointVisibility() {
      // point visibility is currently only used if there are thumbnail images:
      if (!this.textureAtlas) return;
      return;
      const margin = -30 * window.devicePixelRatio

      const left = this.screenToEmbeddingX(this.passiveMarginsLRTB[0] + margin)
      const right = this.screenToEmbeddingX(window.innerWidth - this.passiveMarginsLRTB[1] - margin)
      const top = this.screenToEmbeddingY(this.passiveMarginsLRTB[2] + margin)
      const bottom = this.screenToEmbeddingY(window.innerHeight - this.passiveMarginsLRTB[3] - margin)

      const maxItems = 50
      const pointIndexes = []
      const pointVisibility = []
      for (const i of Array(this.currentPositionsX.length).keys()) {
        const x = this.currentPositionsX[i]
        const y = this.currentPositionsY[i]
        const xInView = x >= left && x <= right
        const yInView = y >= bottom && y <= top
        pointVisibility[i] = xInView && yInView ? 1 : 0
        if (xInView && yInView) pointIndexes.push(i);
        if (pointIndexes.length > maxItems) break;
      }
      if (pointIndexes.length <= maxItems) {
        this.visiblePointIndexes = pointIndexes
        this.pointVisibility = pointVisibility
      } else {
        this.visiblePointIndexes = []
        this.pointVisibility = Array(this.currentPositionsX.length).fill(1)
      }
      this.updateGeometry()
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


  <div v-if="textureAtlas" v-for="pointIndex in visiblePointIndexes" :key="pointIndex" class="fixed pointer-events-none"
  :style="{
    'left': screenLeftFromRelative(currentPositionsX[pointIndex]) + 'px',
    'bottom': screenBottomFromRelative(currentPositionsY[pointIndex]) + 'px',
    }" style="transform: translate(-50%, 50%);">
    <div class="px-1 text-gray-500 text-xs">
      <div v-if="itemDetails.length > pointIndex && hover_label_rendering" class="flex flex-col items-center bg-white/50 text-gray-500 text-xs rounded">
        <img v-if="hover_label_rendering.image(itemDetails[pointIndex])" :src="hover_label_rendering.image(itemDetails[pointIndex])" class="h-24">
      </div>
    </div>
  </div>

  <div v-for="cluster_label in clusterData" class="fixed"
  :style="{
    'left': screenLeftFromRelative(cluster_label.center[0]) + 'px',
    'bottom': screenBottomFromRelative(cluster_label.center[1]) + 'px',
    }">
    <button v-if="appStateStore.selected_cluster_id === null || cluster_label.id === appStateStore.selected_cluster_id"
      @click="$emit('cluster_selected', cluster_label)"
      @mouseenter="$emit('cluster_hovered', cluster_label.id)"
      @mouseleave="$emit('cluster_hover_end')"
      class="px-1 bg-white hover:bg-gray-100 text-gray-500 text-xs rounded"
      v-html="cluster_label.title_html"
      >
    </button>
  </div>

  <div v-if="highlightedPointIdx !== -1" class="fixed pointer-events-none"
  :style="{
    'right': screenRightFromRelative(currentPositionsX[highlightedPointIdx]) + 'px',
    'top': screenTopFromRelative(currentPositionsY[highlightedPointIdx]) + 'px',
    'max-width': '200px',
    }">
    <div v-if="itemDetails.length > highlightedPointIdx && hover_label_rendering" class="flex flex-col items-center px-1 bg-white text-gray-500 text-xs rounded">
      <div v-html="hover_label_rendering.title(itemDetails[highlightedPointIdx])"></div>
      <img v-if="hover_label_rendering.image(itemDetails[highlightedPointIdx])" :src="hover_label_rendering.image(itemDetails[highlightedPointIdx])" class="h-24">
    </div>
    <div v-if="itemDetails.length <= highlightedPointIdx || !hover_label_rendering" class="px-1 bg-white text-gray-500 text-xs rounded">
      loading...
    </div>
  </div>
</div>
</template>

<style scoped></style>
