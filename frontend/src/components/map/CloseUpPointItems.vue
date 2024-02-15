<script setup>
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
      v-if="mapState.textureAtlas"
      v-for="pointIndex in mapState.visiblePointIndexes"
      :key="pointIndex"
      class="pointer-events-none fixed"
      :style="{
        left: mapState.screenLeftFromRelative(mapState.per_point.x[pointIndex]) + 'px',
        bottom: mapState.screenBottomFromRelative(mapState.per_point.y[pointIndex]) + 'px',
      }"
      style="transform: translate(-50%, 50%)">
      <div class="px-1 text-xs text-gray-500">
        <div
          v-if="appState.get_hover_rendering_by_index(pointIndex)"
          class="flex flex-col items-center rounded bg-white/50 text-xs text-gray-500">
          <img
            v-if="appState.get_hover_rendering_by_index(pointIndex).image(mapState.get_item_by_index(pointIndex))"
            :src="appState.get_hover_rendering_by_index(pointIndex).image(mapState.get_item_by_index(pointIndex))"
            class="h-24" />
        </div>
      </div>
    </div>

    <div
      class="pointer-events-none fixed transition-opacity duration-300"
      :class="{'opacity-0': !mapState.show_html_points, 'opacity-100': mapState.show_html_points}">
      <div
        v-for="pointIndex in mapState.visiblePointIndexes"
        :key="pointIndex"
        class="pointer-events-none fixed"
        :style="{
          left: mapState.screenLeftFromRelative(mapState.per_point.x[pointIndex]) + 'px',
          bottom: mapState.screenBottomFromRelative(mapState.per_point.y[pointIndex]) + 'px',
        }"
        style="transform: translate(-50%, 50%)">
        <div
          v-if="appState.get_hover_rendering_by_index(pointIndex)"
          class="flex max-w-[140px] flex-col items-center rounded bg-white px-1 text-[10px] text-gray-500">
          <div
            v-html="appState.get_hover_rendering_by_index(pointIndex).title(mapState.get_item_by_index(pointIndex))"></div>
          <img
            v-if="appState.get_hover_rendering_by_index(pointIndex).image(mapState.get_item_by_index(pointIndex))"
            :src="appState.get_hover_rendering_by_index(pointIndex).image(mapState.get_item_by_index(pointIndex))"
            class="h-24" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
