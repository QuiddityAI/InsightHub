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
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="pointer-events-none">
    <div
      v-for="cluster_label in mapState.clusterData"
      class="pointer-events-auto fixed"
      :style="{
        left: mapState.screenLeftFromRelative(cluster_label.center[0]) + 'px',
        bottom: mapState.screenBottomFromRelative(cluster_label.center[1]) + 'px',
      }">
      <button
        v-if="
          appState.selected_cluster_id === null ||
          cluster_label.id === appState.selected_cluster_id
        "
        @click="appState.cluster_selected(cluster_label)"
        @mouseenter="appState.cluster_hovered(cluster_label.id)"
        @mouseleave="appState.cluster_hover_end()"
        class="rounded bg-white px-1 text-xs text-gray-500 hover:bg-gray-100"
        v-html="cluster_label.title_html"></button>
    </div>
  </div>
</template>

<style scoped></style>
