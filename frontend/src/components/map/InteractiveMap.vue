<script setup>
import panzoom from "panzoom"

import {
  Renderer,
  Camera,
  Geometry,
  Program,
  Mesh,
  Transform,
  Texture,
  TextureLoader,
} from "https://cdn.jsdelivr.net/npm/ogl@0.0.117/+esm"
import * as math from "mathjs"
import pointInPolygon from "point-in-polygon"

import pointsVertexShader3D from "../../shaders/points.vert?raw"
import pointsFragmentShader3D from "../../shaders/points_rectangular_thumbnail.frag?raw"
import pointsVertexShaderPlotly from "../../shaders/points_plotly_style.vert?raw"
import pointsFragmentShaderPlotly from "../../shaders/points_plotly_style.frag?raw"
import shadowsVertexShader from "../../shaders/shadows.vert?raw"
import shadowsFragmentShader from "../../shaders/shadows.frag?raw"

// import pointTextureBaseColorUrl from "../../textures/Brick_Wall_017_basecolor.jpg"
// import pointTextureNormalMapUrl from "../../textures/Crystal_001_NORM.jpg"

import { ensureLength } from "../../utils/utils.js"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>
export default {
  inject: ["eventBus"],
  emits: ["point_selected"],
  data() {
    return {
      // internal:
      currentPositionsX: [],
      currentPositionsY: [],
      currentVelocityX: [],
      currentVelocityY: [],
      pointVisibility: [],
      actual_opacity: [],

      panzoomInstance: null,

      // mouseover highlight and selection:
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
      // pointTextureBaseColor: null,
      // pointTextureNormalMap: null,
    }
  },
  computed: {
    pointsVertexShader() {
      return this.appStateStore.settings.frontend.rendering.style == "plotly"
        ? pointsVertexShaderPlotly
        : pointsVertexShader3D
    },
    pointsFragmentShader() {
      return this.appStateStore.settings.frontend.rendering.style == "plotly"
        ? pointsFragmentShaderPlotly
        : pointsFragmentShader3D
    },
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    const that = this
    this.setupWebGl()
    this.setupPanZoom()
    setInterval(this.updatePointVisibility, 500)
    this.eventBus.on("reset_map", () => {
      that.resetData()
      that.resetPanAndZoom()
    })
    this.eventBus.on("map_regenerate_attribute_arrays_from_fallbacks", () => {
      that.regenerateAttributeArraysFromFallbacks()
    })
    this.eventBus.on("map_update_geometry", () => {
      that.updateGeometry()
    })
    this.eventBus.on("map_center_and_fit_data_to_active_area_smooth", () => {
      that.centerAndFitDataToActiveAreaSmooth()
    })
    this.eventBus.on("map_center_and_fit_data_to_active_area_instant", () => {
      that.centerAndFitDataToActiveAreaInstant()
    })
    this.eventBus.on("map_reset_pan_and_zoom", () => {
      that.resetPanAndZoom()
    })
    this.eventBus.on("visibility_filters_changed", () => {
      that.update_opacities()
    })
  },
  watch: {
    "mapStateStore.selected_point_indexes"() {
      this.updateGeometry()
    },
    "appStateStore.selected_cluster_id"() {
      this.updateUniforms()
    },
    "appStateStore.highlighted_cluster_id"() {
      this.updateUniforms()
    },
    "appStateStore.highlighted_item_id"() {
      if (this.appStateStore.highlighted_item_id === null) {
        this.mapStateStore.hovered_point_idx = -1
        this.appStateStore.cluster_hover_end()
        return
      }
      this.mapStateStore.hovered_point_idx = this.mapStateStore.per_point.item_id.findIndex(
        (ds_and_item_id) => ds_and_item_id[0] == this.appStateStore.highlighted_item_id[0] && ds_and_item_id[1] == this.appStateStore.highlighted_item_id[1]
      )
      // TODO: highlighted_cluster_id should be changed directly, but currently accessing appState breaks this component
      this.appStateStore.cluster_hovered(this.mapStateStore.per_point.cluster_id[this.mapStateStore.hovered_point_idx])
      this.updateUniforms()
    },
    "appStateStore.settings.frontend.rendering.style"() {
      this.updateGeometry()
    },
    "mapStateStore.per_point.item_id"() {
      this.update_opacities()
    },
    "mapStateStore.per_point.opacity"() {
      this.update_opacities()
    },
  },
  methods: {
    resetData() {
      this.mapStateStore.text_data = {}
      this.mapStateStore.per_point = {
        item_id: [],
        cluster_id: [],
        x: [],
        y: [],
        size: [],
        hue: [],
        sat: [],
        val: [],
        opacity: [],
        secondary_hue: [],
        secondary_sat: [],
        secondary_val: [],
        secondary_opacity: [],
        flatness: [],
        thumbnail_aspect_ratio: [],
      }

      this.mapStateStore.clusterData = []
      this.mapStateStore.textureAtlas = null
      this.mapStateStore.thumbnailSpriteSize = 64

      this.mapStateStore.markedPointIdx = -1
      this.mapStateStore.hovered_point_idx = -1

      this.updateGeometry()
    },
    resetPanAndZoom() {
      // smooth reset doesn't seem to be possible because during smooth movement, the transfrom isn't updated?
      this.panzoomInstance.moveTo(0, 0)
      this.panzoomInstance.zoomAbs(0, 0, 1)
    },
    setupPanZoom() {
      const that = this
      this.panzoomInstance = panzoom(this.$refs.panZoomProxy, {
        zoomSpeed: 0.35, // 35% per mouse wheel event
        minZoom: 0.7,
        bounds: false,
        zoomDoubleClickSpeed: 1, // disable zoom on double click
        onTouch: function (e) {
          return e.touches.length > 1 // don't prevent touch propagation if there is just one touch (but when there are two or more to prevent zooming the page itself instead of this area only)
        },
        onDoubleClick: function (e) {
          that.resetPanAndZoom()
        },
        beforeMouseDown: function (e) {
          var shouldIgnore = that.mapStateStore.selected_map_tool === "lasso"
          return shouldIgnore
        },
      })

      this.panzoomInstance.on("transform", function (e) {
        const transform = e.getTransform()
        that.mapStateStore.currentPan = [transform.x, transform.y]
        that.mapStateStore.currentZoom = transform.scale
        that.updateUniforms()
      })
    },
    setupWebGl() {
      this.renderer = new Renderer({ depth: false, dpr: window.devicePixelRatio || 1.0 })
      this.glContext = this.renderer.gl
      this.$refs.webGlArea.appendChild(this.glContext.canvas)
      this.glContext.clearColor(0.93, 0.94, 0.95, 1)

      this.camera = new Camera(this.glContext, {
        left: 0.00001,
        right: 1,
        top: 1,
        bottom: 0.0001,
      })
      this.camera.position.z = 1

      const that = this

      function resize() {
        that.renderer.setSize(window.innerWidth, window.innerHeight)
        //that.camera.perspective({ aspect: that.glContext.canvas.width / that.glContext.canvas.height });
      }
      window.addEventListener("resize", resize, false)
      resize()
      this.updateGeometry()

      let lastUpdateTimeInMs = performance.now()

      function getAccelerationOfSpringArr(
        currentPos,
        currentVelocity,
        targetPosition,
        stiffness,
        mass,
        damping
      ) {
        // inspired by https://blog.maximeheckel.com/posts/the-physics-behind-spring-animations/
        const displacement = math.subtract(currentPos, targetPosition)
        const k = -stiffness // in kg / s^2
        const d = -damping // in kg / s
        const Fspring = math.dotMultiply(k, displacement)
        const Fdamping = math.dotMultiply(d, currentVelocity)
        const acceleration = math.divide(math.add(Fspring, Fdamping), mass)
        return acceleration
      }

      requestAnimationFrame(update)
      function update(currentTimeInMs) {
        requestAnimationFrame(update)

        const timeSinceLastUpdateInSec = (currentTimeInMs - lastUpdateTimeInMs) / 1000.0
        lastUpdateTimeInMs = currentTimeInMs

        if (
          that.currentPositionsX.length == 0 ||
          that.currentPositionsX.length != that.mapStateStore.per_point.x.length
        )
          return

        // restDelta means at which distance from the target position the movement stops and they
        // jump to the target (otherwise the motion could go on forever)
        // here we assume that the plot is about 700px wide and if the delta is less than a pixel, it should stop
        const restDelta = (math.max(that.mapStateStore.per_point.x) - math.min(that.mapStateStore.per_point.x)) / 700.0
        // to make sure overshoots still work, we don't stop the motion if the speed is still
        // greater than restSpeed, here defined as restDelta per 1/5th second
        const restSpeed = restDelta / 0.2 // in restDelta units per sec

        let geometryChanged = false
        let uniformsChanged = false

        const baseOffsetDiff = math.subtract(that.mapStateStore.baseOffsetTarget, that.mapStateStore.baseOffset)
        if (math.max(math.abs(baseOffsetDiff)) !== 0.0) {
          uniformsChanged = true

          const a = getAccelerationOfSpringArr(
            that.mapStateStore.baseOffset,
            that.mapStateStore.baseOffsetVelocity,
            that.mapStateStore.baseOffsetTarget,
            /* stiffness */ 15.0,
            /* mass */ 1.0,
            /* damping */ 8.0
          )
          that.mapStateStore.baseOffsetVelocity = math.add(
            that.mapStateStore.baseOffsetVelocity,
            math.dotMultiply(a, timeSinceLastUpdateInSec)
          )
          that.mapStateStore.baseOffset = math.add(
            that.mapStateStore.baseOffset,
            math.dotMultiply(that.mapStateStore.baseOffsetVelocity, timeSinceLastUpdateInSec)
          )
          if (
            math.max(math.abs(that.mapStateStore.baseOffsetVelocity)) < restSpeed &&
            math.max(math.abs(baseOffsetDiff)) < restDelta
          ) {
            that.mapStateStore.baseOffset = that.mapStateStore.baseOffsetTarget.slice() // using slice to copy the array
          }
        }

        const restSpeedScale = 0.0005
        const restDeltaScale = 0.00005

        const baseScaleDiff = math.subtract(that.mapStateStore.baseScaleTarget, that.mapStateStore.baseScale)
        if (math.max(math.abs(baseScaleDiff)) !== 0.0) {
          uniformsChanged = true

          const a = getAccelerationOfSpringArr(
            that.mapStateStore.baseScale,
            that.mapStateStore.baseScaleVelocity,
            that.mapStateStore.baseScaleTarget,
            /* stiffness */ 15.0,
            /* mass */ 1.0,
            /* damping */ 8.0
          )
          that.mapStateStore.baseScaleVelocity = math.add(
            that.mapStateStore.baseScaleVelocity,
            math.dotMultiply(a, timeSinceLastUpdateInSec)
          )
          that.mapStateStore.baseScale = math.add(
            that.mapStateStore.baseScale,
            math.dotMultiply(that.mapStateStore.baseScaleVelocity, timeSinceLastUpdateInSec)
          )
          if (
            math.max(math.abs(that.mapStateStore.baseScaleVelocity)) < restSpeedScale &&
            math.max(math.abs(baseScaleDiff)) < restDeltaScale
          ) {
            that.mapStateStore.baseScale = that.mapStateStore.baseScaleTarget.slice() // using slice to copy the array
          }
        }

        if (that.currentPositionsX.length === that.mapStateStore.per_point.x.length) {
          const diffX = math.subtract(that.mapStateStore.per_point.x, that.currentPositionsX)
          const diffY = math.subtract(that.mapStateStore.per_point.y, that.currentPositionsY)
          if (math.max(math.abs(diffX)) > restDelta || math.max(math.abs(diffY)) > restDelta) {
            geometryChanged = true

            const aX = getAccelerationOfSpringArr(
              that.currentPositionsX,
              that.currentVelocityX,
              that.mapStateStore.per_point.x,
              /* stiffness */ 20.0,
              /* mass */ 1.0,
              /* damping */ 6.0
            )
            that.currentVelocityX = math.add(
              that.currentVelocityX,
              math.dotMultiply(aX, timeSinceLastUpdateInSec)
            )
            that.currentPositionsX = math.add(
              that.currentPositionsX,
              math.dotMultiply(that.currentVelocityX, timeSinceLastUpdateInSec)
            )
            if (
              math.max(math.abs(that.currentVelocityX)) < restSpeed &&
              math.max(math.abs(diffX)) < restDelta
            ) {
              that.currentPositionsX = that.mapStateStore.per_point.x.slice() // using slice to copy the array
            }

            const aY = getAccelerationOfSpringArr(
              that.currentPositionsY,
              that.currentVelocityY,
              that.mapStateStore.per_point.y,
              /* stiffness */ 20.0,
              /* mass */ 1.0,
              /* damping */ 6.0
            )
            that.currentVelocityY = math.add(
              that.currentVelocityY,
              math.dotMultiply(aY, timeSinceLastUpdateInSec)
            )
            that.currentPositionsY = math.add(
              that.currentPositionsY,
              math.dotMultiply(that.currentVelocityY, timeSinceLastUpdateInSec)
            )
            if (
              math.max(math.abs(that.currentVelocityY)) < restSpeed &&
              math.max(math.abs(diffY)) < restDelta
            ) {
              that.currentPositionsY = that.mapStateStore.per_point.y.slice() // using slice to copy the array
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
      if (this.mapStateStore.per_point.x.length === 0) return
      const newBaseOffsetTarget = [-math.min(this.mapStateStore.per_point.x), -math.min(this.mapStateStore.per_point.y)]
      const newBaseScaleTarget = [1.0, 1.0]
      newBaseScaleTarget[0] = 1.0 / (math.max(this.mapStateStore.per_point.x) + newBaseOffsetTarget[0])
      newBaseScaleTarget[1] = 1.0 / (math.max(this.mapStateStore.per_point.y) + newBaseOffsetTarget[1])
      const offsetChange = math.max(
        math.max(newBaseOffsetTarget[0], this.mapStateStore.baseOffsetTarget[0]) /
          math.min(newBaseOffsetTarget[0], this.mapStateStore.baseOffsetTarget[0]),
        math.max(newBaseOffsetTarget[1], this.mapStateStore.baseOffsetTarget[1]) /
          math.min(newBaseOffsetTarget[1], this.mapStateStore.baseOffsetTarget[1])
      )
      const scaleChange = math.max(
        math.max(newBaseScaleTarget[0], this.mapStateStore.baseScaleTarget[0]) /
          math.min(newBaseScaleTarget[0], this.mapStateStore.baseScaleTarget[0]),
        math.max(newBaseScaleTarget[1], this.mapStateStore.baseScaleTarget[1]) /
          math.min(newBaseScaleTarget[1], this.mapStateStore.baseScaleTarget[1])
      )
      this.mapStateStore.baseOffsetTarget = newBaseOffsetTarget
      this.mapStateStore.baseScaleTarget = newBaseScaleTarget
      if (offsetChange > 30.5 || scaleChange > 3.5) {
        this.mapStateStore.baseOffset = this.mapStateStore.baseOffsetTarget.slice() // using slice to copy the array
        this.mapStateStore.baseScale = this.mapStateStore.baseScaleTarget.slice() // using slice to copy the array
        this.mapStateStore.baseOffsetVelocity = [0.0, 0.0]
        this.mapStateStore.baseScaleVelocity = [0.0, 0.0]
      }
    },
    centerAndFitDataToActiveAreaInstant() {
      this.centerAndFitDataToActiveAreaSmooth()
      this.mapStateStore.baseOffset = this.mapStateStore.baseOffsetTarget.slice() // using slice to copy the array
      this.mapStateStore.baseScale = this.mapStateStore.baseScaleTarget.slice() // using slice to copy the array
      this.mapStateStore.baseOffsetVelocity = [0.0, 0.0]
      this.mapStateStore.baseScaleVelocity = [0.0, 0.0]
    },
    regenerateAttributeArraysFromFallbacks() {
      const pointCount = this.mapStateStore.per_point.x.length
      for (const attr of [
        "size",
        "hue",
        "sat",
        "val",
        "opacity",
        "secondary_hue",
        "secondary_sat",
        "secondary_val",
        "secondary_opacity",
        "flatness",
        "thumbnail_aspect_ratio",
      ]) {
        this.mapStateStore.per_point[attr] = []
        this.mapStateStore.per_point[attr] = ensureLength(
          this.mapStateStore.per_point[attr],
          pointCount,
          this.appStateStore.settings.frontend.rendering[attr]?.fallback ?? 0.0
        )
      }
    },
    update_opacities() {
      this.actual_opacity = Array(this.mapStateStore.per_point.x.length).fill(1.0)
      try {
        for (const i in this.mapStateStore.per_point.x) {
          const item_ds_and_id = this.mapStateStore.per_point.item_id[i]
          const item = this.mapStateStore.text_data[item_ds_and_id[0]][item_ds_and_id[1]]
          const include = this.mapStateStore.visibility_filters.every(filter_item => filter_item.filter_fn(item))
          this.actual_opacity[i] = include ? this.mapStateStore.per_point.opacity[i] || 1.0 : 0.1
        }
      } catch (e) {
        console.warn(e)
      }
      this.updateGeometry()
    },
    updateGeometry() {
      const pointCount = this.mapStateStore.per_point.x.length
      this.mapStateStore.per_point.y = ensureLength(this.mapStateStore.per_point.y, pointCount, 0.0)

      this.currentPositionsX = ensureLength(
        this.currentPositionsX,
        pointCount,
        pointCount > 0 ? math.mean(this.mapStateStore.per_point.x) : 0.0,
        true
      )
      this.currentPositionsY = ensureLength(
        this.currentPositionsY,
        pointCount,
        pointCount > 0 ? math.mean(this.mapStateStore.per_point.y) : 0.0,
        true
      )
      this.currentVelocityX = ensureLength(this.currentVelocityX, pointCount, 0.0, true)
      this.currentVelocityY = ensureLength(this.currentVelocityY, pointCount, 0.0, true)
      this.actual_opacity = ensureLength(this.actual_opacity, pointCount, 1.0)
      this.pointVisibility = ensureLength(this.pointVisibility, pointCount, 0)

      this.mapStateStore.per_point.cluster_id = ensureLength(this.mapStateStore.per_point.cluster_id, pointCount, 0)
      for (const attr of [
        "size",
        "hue",
        "sat",
        "val",
        "opacity",
        "secondary_hue",
        "secondary_sat",
        "secondary_val",
        "secondary_opacity",
        "flatness",
        "thumbnail_aspect_ratio",
      ]) {
        this.mapStateStore.per_point[attr] = ensureLength(
          this.mapStateStore.per_point[attr],
          pointCount,
          this.appStateStore.settings.frontend.rendering[attr]?.fallback ?? 0.0
        )
      }

      this.glTextureAtlas = new Texture(this.glContext, {
        generateMipmaps: false,
        minFilter: this.glContext.NEAREST,
        magFilter: this.glContext.LINEAR,
      })
      if (this.mapStateStore.textureAtlas) {
        this.glTextureAtlas.image = this.mapStateStore.textureAtlas
      }

      // this.pointTextureBaseColor = TextureLoader.load(this.glContext, {
      //   src: pointTextureBaseColorUrl,
      // })
      // this.pointTextureNormalMap = TextureLoader.load(this.glContext, {
      //   src: pointTextureNormalMapUrl,
      //   minFilter: this.glContext.LINEAR,
      // })

      this.glScene = new Transform()
      this.updateMeshesQuads()

      this.renderer.render({ scene: this.glScene, camera: this.camera })
    },
    updateMeshesPoints() {
      // not used at the moment
      // const shadowGeometry = new Geometry(this.glContext, {
      //     positionX: { size: 1, data: new Float32Array(this.currentPositionsX) },
      //     positionY: { size: 1, data: new Float32Array(this.currentPositionsY) },
      //     pointSize: { size: 1, data: new Float32Array(this.mapStateStore.per_point.size) },
      //     pointVisibility: { size: 1, data: new Float32Array(this.pointVisibility) },
      // });
      // this.glProgramShadows = new Program(this.glContext, {
      //     vertex: shadowsVertexShader,
      //     fragment: shadowsFragmentShader,
      //     uniforms: this.getUniforms(),
      //     transparent: true,
      //     depthTest: false,
      // });
      // this.glMeshShadows = new Mesh(this.glContext, { mode: this.glContext.POINTS, geometry: shadowGeometry, program: this.glProgramShadows });
      // this.glMeshShadows.setParent(this.glScene)
      // const pointsGeometry = new Geometry(this.glContext, {
      //     positionX: { size: 1, data: new Float32Array(this.currentPositionsX) },
      //     positionY: { size: 1, data: new Float32Array(this.currentPositionsY) },
      //     clusterId: { size: 1, data: new Float32Array(this.mapStateStore.per_point.cluster_id) },
      //     pointSize: { size: 1, data: new Float32Array(this.mapStateStore.per_point.size) },
      //     hue: { size: 1, data: new Float32Array(this.mapStateStore.per_point.hue) },
      //     sat: { size: 1, data: new Float32Array(this.mapStateStore.per_point.sat) },
      //     val: { size: 1, data: new Float32Array(this.mapStateStore.per_point.val) },
      //     opacity: { size: 1, data: new Float32Array(this.mapStateStore.per_point.opacity) },
      //     secondary_hue: { size: 1, data: new Float32Array(this.mapStateStore.per_point.secondary_hue) },
      //     secondary_sat: { size: 1, data: new Float32Array(this.mapStateStore.per_point.secondary_sat) },
      //     secondary_val: { size: 1, data: new Float32Array(this.mapStateStore.per_point.secondary_val) },
      //     secondary_opacity: { size: 1, data: new Float32Array(this.mapStateStore.per_point.secondary_opacity) },
      //     pointVisibility: { size: 1, data: new Float32Array(this.pointVisibility) },
      // });
      // this.glProgram = new Program(this.glContext, {
      //     vertex: pointsVertexShader,
      //     fragment: pointsFragmentShader,
      //     uniforms: this.getUniforms(),
      //     transparent: true,
      //     depthTest: false,
      //     // depthFunc: this.glContext.NOTEQUAL,
      // });
      // this.glMesh = new Mesh(this.glContext, { mode: this.glContext.POINTS, geometry: pointsGeometry, program: this.glProgram });
      // this.glMesh.setParent(this.glScene)
    },
    updateMeshesQuads() {
      const pointCount = this.currentPositionsX.length
      const shadowGeometry = new Geometry(this.glContext, {
        position: {
          size: 2,
          data: new Float32Array([0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0]),
        },
        positionX: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.currentPositionsX),
        },
        positionY: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.currentPositionsY),
        },
        pointSize: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.size.slice(0, pointCount)),
        },
        pointVisibility: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.pointVisibility.slice(0, pointCount)),
        },
        opacity: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.actual_opacity.slice(0, pointCount)),
        },
      })

      this.glProgramShadows = new Program(this.glContext, {
        vertex: shadowsVertexShader,
        fragment: shadowsFragmentShader,
        uniforms: this.getUniforms(),
        transparent: true,
        depthTest: false,
      })

      this.glMeshShadows = new Mesh(this.glContext, {
        mode: this.glContext.TRIANGLE_STRIP,
        geometry: shadowGeometry,
        program: this.glProgramShadows,
      })
      this.glMeshShadows.setParent(this.glScene)

      const per_point_hue = [...this.mapStateStore.per_point.hue.slice(0, pointCount)]
      const per_point_sat = [...this.mapStateStore.per_point.sat.slice(0, pointCount)]
      const per_point_val = [...this.mapStateStore.per_point.val.slice(0, pointCount)]
      for (const i of Array(pointCount).keys()) {
        if (this.mapStateStore.per_point.cluster_id[i] === -1) {
          per_point_sat[i] = 0.0
          per_point_val[i] = 0.7
        }
      }
      for (const i of this.mapStateStore.selected_point_indexes) {
        per_point_hue[i] = 0.0
        per_point_sat[i] = 1.0
      }

      const pointsGeometry = new Geometry(this.glContext, {
        position: {
          size: 2,
          data: new Float32Array([0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0]),
        },
        positionX: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.currentPositionsX),
        },
        positionY: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.currentPositionsY),
        },
        clusterId: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.cluster_id.slice(0, pointCount)),
        },
        pointSize: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.size.slice(0, pointCount)),
        },
        hue: { instanced: 1, size: 1, data: new Float32Array(per_point_hue) },
        sat: { instanced: 1, size: 1, data: new Float32Array(per_point_sat) },
        val: { instanced: 1, size: 1, data: new Float32Array(per_point_val), },
        opacity: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.actual_opacity.slice(0, pointCount)),
        },
        secondary_hue: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.secondary_hue.slice(0, pointCount)),
        },
        secondary_sat: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.secondary_sat.slice(0, pointCount)),
        },
        secondary_val: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.secondary_val.slice(0, pointCount)),
        },
        secondary_opacity: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.secondary_opacity.slice(0, pointCount)),
        },
        pointVisibility: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.pointVisibility.slice(0, pointCount)),
        },
        flatness: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.flatness.slice(0, pointCount)),
        },
        thumbnailAspectRatio: {
          instanced: 1,
          size: 1,
          data: new Float32Array(this.mapStateStore.per_point.thumbnail_aspect_ratio.slice(0, pointCount)),
        },
      })

      this.glProgram = new Program(this.glContext, {
        vertex: this.pointsVertexShader,
        fragment: this.pointsFragmentShader,
        uniforms: this.getUniforms(),
        transparent: true,
        depthTest: false,
        // depthFunc: this.glContext.NOTEQUAL,
      })

      this.glMesh = new Mesh(this.glContext, {
        mode: this.glContext.TRIANGLE_STRIP,
        geometry: pointsGeometry,
        program: this.glProgram,
      })
      this.glMesh.setParent(this.glScene)
    },
    getUniforms() {
      const ww = window.innerWidth
      const wh = window.innerHeight
      let selectedClusterId =
        (this.appStateStore.selected_cluster_id !== null && this.appStateStore.selected_cluster_id !== undefined)
          ? this.appStateStore.selected_cluster_id
          : -1
      if (this.appStateStore.highlighted_cluster_id !== null && this.appStateStore.highlighted_cluster_id !== undefined) {
        selectedClusterId = this.appStateStore.highlighted_cluster_id
      }

      return {
        // types are inferred from shader code
        baseOffset: { value: this.mapStateStore.baseOffset },
        baseScale: { value: this.mapStateStore.baseScale },
        viewportSize: { value: [ww, wh] },
        activeAreaSize: {
          value: [this.mapStateStore.activeAreaWidth / ww, this.mapStateStore.activeAreaHeight / wh],
        },
        marginLeft: { value: this.mapStateStore.passiveMarginsLRTB[0] / ww },
        marginBottom: { value: this.mapStateStore.passiveMarginsLRTB[3] / wh },
        pan: { value: math.dotDivide(this.mapStateStore.currentPan, [ww, wh]) },
        zoom: { value: this.mapStateStore.currentZoom },
        hoveredPointIdx: { value: this.mapStateStore.hovered_point_idx },
        lightPosition: { value: this.lightPosition },
        devicePixelRatio: { value: window.devicePixelRatio || 1.0 },
        markedPointIdx: { value: this.mapStateStore.markedPointIdx },
        textureAtlas: { value: this.glTextureAtlas },
        useTextureAtlas: { value: this.mapStateStore.textureAtlas !== null },
        // pointTextureBaseColor: { value: this.pointTextureBaseColor },
        // pointTextureNormalMap: { value: this.pointTextureNormalMap },
        thumbnailSpriteSize: { value: this.mapStateStore.thumbnailSpriteSize },
        selectedClusterId: { value: selectedClusterId },
        maxOpacity: { value: this.appStateStore.settings.frontend.rendering.max_opacity },
        shadowOpacity: { value: this.appStateStore.settings.frontend.rendering.shadow_opacity },
        pointSizeFactor: { value: this.appStateStore.settings.frontend.rendering.point_size_factor },
      }
    },
    updateUniforms() {
      this.glProgram.uniforms = this.getUniforms()
      this.glProgramShadows.uniforms = this.getUniforms()
      this.renderer.render({ scene: this.glScene, camera: this.camera })
    },
    updateOnHover(event) {
      if (event.buttons) {
        if (this.mapStateStore.selected_map_tool === "lasso") {
          const x = this.mapStateStore.screenToEmbeddingX(event.clientX)
          const y = this.mapStateStore.screenToEmbeddingY(event.clientY)
          this.mapStateStore.lasso_points.push([x, y])
          //this.$emit('lasso_points_changed', this.mapStateStore.lasso_points)
        }
        return
      }
      const mousePosInEmbeddingSpaceX = this.mapStateStore.screenToEmbeddingX(event.clientX)
      const mousePosInEmbeddingSpaceY = this.mapStateStore.screenToEmbeddingY(event.clientY)

      // this.lightPosition = [event.clientX / window.innerWidth,  1.0 - event.clientY / window.innerHeight]

      let closestIdx = null
      let closestDist = 10000000
      for (const i of Array(this.currentPositionsX.length).keys()) {
        const a = this.currentPositionsX[i] - mousePosInEmbeddingSpaceX
        const b = this.currentPositionsY[i] - mousePosInEmbeddingSpaceY
        const distance = Math.sqrt(a * a + b * b)
        if (distance < closestDist) {
          closestDist = distance
          closestIdx = i
        }
      }
      const pointSize = this.mapStateStore.per_point.size[closestIdx]
      const zoomAdjustment = (this.mapStateStore.currentZoom - 1.0) * 0.05 + 1.0
      const pointSizeScreenPx =
        (5.0 + 15.0 * pointSize) * zoomAdjustment * this.appStateStore.settings.frontend.rendering.point_size_factor
      const pointRadiusScreenPx = pointSizeScreenPx / 2
      // FIXME: as x and y may have different scale factors, the "closestDist" might be squashed in one direction
      // this should be fixed by unsqueezing it by the scale factor of the respective axis before
      const pointRadiusEmbedding =
        this.mapStateStore.screenToEmbeddingX(pointRadiusScreenPx) - this.mapStateStore.screenToEmbeddingX(0)
      const threshold = pointRadiusEmbedding
      if (closestIdx !== null && closestDist < threshold) {
        this.mapStateStore.hovered_point_idx = closestIdx
      } else {
        this.mapStateStore.hovered_point_idx = -1
      }
      this.updateUniforms()
    },
    onMouseLeave() {
      this.mapStateStore.hovered_point_idx = -1
    },
    onMouseDown(event) {
      if (event.pointerType === "mouse" && event.button != 0) return
      if (this.mapStateStore.selected_map_tool === "lasso") {
        if (event.shiftKey) {
          this.mapStateStore.selection_merging_mode = "add"
        } else if (event.ctrlKey) {
          this.mapStateStore.selection_merging_mode = "remove"
        }
        this.mapStateStore.lasso_points = []
        this.mapStateStore.lasso_points.push([
          this.mapStateStore.screenToEmbeddingX(event.clientX),
          this.mapStateStore.screenToEmbeddingY(event.clientY),
        ])
      }
      this.mouseDownPosition = [event.clientX, event.clientY]
    },
    onMouseUp(event) {
      if (event.pointerType === "mouse" && event.button != 0) return
      if (this.mapStateStore.selected_map_tool === "lasso") {
        this.mapStateStore.lasso_points.push([
          this.mapStateStore.screenToEmbeddingX(event.clientX),
          this.mapStateStore.screenToEmbeddingY(event.clientY),
        ])
        //this.$emit('lasso_points_changed', this.mapStateStore.lasso_points)
        this.executeLassoSelection(this.mapStateStore.selection_merging_mode)
        if (this.mapStateStore.selection_merging_mode === "replace") {
          this.mapStateStore.selected_map_tool = "drag"
        }
      }
      if (this.mapStateStore.hovered_point_idx === -1) return
      const mouseMovementDistance = math.distance(this.mouseDownPosition, [
        event.clientX,
        event.clientY,
      ])
      if (mouseMovementDistance > 5) return
      if (event.shiftKey) {
        if (this.mapStateStore.selected_point_indexes.includes(this.mapStateStore.hovered_point_idx)) {
          this.mapStateStore.selected_point_indexes =
            this.mapStateStore.selected_point_indexes.filter((x) => x !== this.mapStateStore.hovered_point_idx)
        } else {
          this.mapStateStore.selected_point_indexes.push(this.mapStateStore.hovered_point_idx)
          // the array object is still the same, so we need to trigger a change event manually:
          this.updateGeometry()
        }
      } else {
        const dataset_and_item_id = this.mapStateStore.per_point.item_id[this.mapStateStore.hovered_point_idx]
        this.$emit("point_selected", dataset_and_item_id)
      }
    },
    updatePointVisibility() {
      // point visibility is currently only used if there are thumbnail images:
      // if (!this.mapStateStore.textureAtlas) return
      // return
      const margin = -30 * window.devicePixelRatio

      // const left = this.mapStateStore.screenToEmbeddingX(this.mapStateStore.passiveMarginsLRTB[0] + margin)
      // const right = this.mapStateStore.screenToEmbeddingX(
      //   window.innerWidth - this.mapStateStore.passiveMarginsLRTB[1] - margin
      // )
      // const top = this.mapStateStore.screenToEmbeddingY(this.mapStateStore.passiveMarginsLRTB[2] + margin)
      // const bottom = this.mapStateStore.screenToEmbeddingY(
      //   window.innerHeight - this.mapStateStore.passiveMarginsLRTB[3] - margin
      // )

      const left = this.mapStateStore.screenToEmbeddingX(margin)
      const right = this.mapStateStore.screenToEmbeddingX(
        window.innerWidth - margin
      )
      const top = this.mapStateStore.screenToEmbeddingY(margin)
      const bottom = this.mapStateStore.screenToEmbeddingY(
        window.innerHeight - margin
      )

      const maxItems = 10
      const pointIndexes = []
      const pointVisibility = []
      let visibility_change = false
      for (const i of Array(this.currentPositionsX.length).keys()) {
        const x = this.currentPositionsX[i]
        const y = this.currentPositionsY[i]
        const xInView = x >= left && x <= right
        const yInView = y >= bottom && y <= top
        pointVisibility[i] = xInView && yInView ? 1 : 0
        if (xInView && yInView) {
          pointIndexes.push(i)
          if (!visibility_change && this.mapStateStore.visiblePointIndexes[pointIndexes.length - 1] !== i) {
            visibility_change = true
          }
        }
        if (pointIndexes.length > maxItems) break
      }
      if (visibility_change) {
        this.mapStateStore.visiblePointIndexes = pointIndexes
        this.mapStateStore.show_html_points = pointIndexes.length <= maxItems
        // update geometry is not needed as currently only HTML elements use the visibility:
        // this.updateGeometry()
      }
    },
    executeLassoSelection(mode = "replace") {
      const polygonPoints = this.mapStateStore.lasso_points
      const pointPositions = this.mapStateStore.per_point.x.map((x, i) => [x, this.mapStateStore.per_point.y[i]])
      const selectedPointIndexes = []
      for (const i of Array(pointPositions.length).keys()) {
        const point = pointPositions[i]
        if (pointInPolygon(point, polygonPoints)) {
          selectedPointIndexes.push(i)
        }
      }
      if (mode == "replace") {
        this.mapStateStore.selected_point_indexes = selectedPointIndexes
      } else if (mode == "add") {
        this.mapStateStore.selected_point_indexes = [
          ...new Set([...this.mapStateStore.selected_point_indexes, ...selectedPointIndexes]),
        ]
      } else if (mode == "remove") {
        this.mapStateStore.selected_point_indexes =
          this.mapStateStore.selected_point_indexes.filter(
            (x) => !selectedPointIndexes.includes(x)
          )
      }
      this.mapStateStore.lasso_points = []
      this.updateGeometry()
    },
  },
}
</script>

<template>
  <div>
    <div class="fixed h-full w-full" ref="panZoomProxy"></div>

    <div
      ref="webGlArea"
      @mousemove="updateOnHover"
      @touchmove="updateOnHover"
      @mousedown="onMouseDown"
      @mouseup="onMouseUp"
      @touchstart="onMouseDown"
      @touchend="onMouseUp"
      @mouseleave="onMouseLeave"
      class="fixed h-full w-full"
      :class="{
        'cursor-crosshair': mapStateStore.selected_map_tool === 'lasso',
        'cursor-pointer': mapState.hovered_point_idx !== -1,
      }"></div>

    <!-- this div shows a gray outline around the "active area" for debugging purposes -->
    <!-- <div class="fixed ring-1 ring-inset ring-gray-300" :style="{'left': mapState.passiveMarginsLRTB[0] + 'px', 'right': passiveMarginsLRTB[1] + 'px', 'top': passiveMarginsLRTB[2] + 'px', 'bottom': passiveMarginsLRTB[3] + 'px'}"></div> -->
  </div>
</template>

<style scoped></style>
